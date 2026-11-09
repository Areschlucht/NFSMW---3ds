#include "streamed_world.h"
#include "streamed_world_texture.h"
#include "world_streaming.h"
#include "world_streaming_scene.h"
#include "world_visibility.h"
#include "mw_lod_select.h"
#include "mw_gekko_math.h"
#include <errno.h>
#include <limits.h>
#include <malloc.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SECTION_LIMIT 147u
#define PATH_LIMIT 512u
#define NORMAL_ALIGN 16u
typedef struct ArenaBlock { size_t bytes;struct ArenaBlock *next;bool free; } ArenaBlock;
typedef struct { uint8_t *base;size_t bytes;uint32_t allocations; } Arena;
static size_t padded(size_t n,size_t a){return (n+a-1)&~(a-1);}
static size_t block_header(void){return padded(sizeof(ArenaBlock),NORMAL_ALIGN);}
static void *arena_alloc(Arena *a,size_t bytes){
    size_t n=padded(bytes?bytes:1,NORMAL_ALIGN),h=block_header();
    for(ArenaBlock *b=(ArenaBlock *)a->base;b;b=b->next){
        if(!b->free||b->bytes<n)continue;
        if(b->bytes>=n+h+NORMAL_ALIGN){
            ArenaBlock *tail=(ArenaBlock *)((uint8_t *)b+h+n);
            *tail=(ArenaBlock){b->bytes-n-h,b->next,true};b->next=tail;b->bytes=n;
        }
        b->free=false;a->allocations++;void *result=(uint8_t *)b+h;memset(result,0,b->bytes);return result;
    }
    return NULL;
}
static void arena_free(Arena *a,void *p){
    if(!p)return;
    size_t h=block_header();((ArenaBlock *)((uint8_t *)p-h))->free=true;
    for(ArenaBlock *b=(ArenaBlock *)a->base;b&&b->next;){
        if(b->free&&b->next->free){b->bytes+=h+b->next->bytes;b->next=b->next->next;}else b=b->next;
    }
}
static size_t arena_charge(const void *p){return p?((const ArenaBlock *)((const uint8_t *)p-block_header()))->bytes+block_header():0;}
static size_t arena_used(const Arena *a){size_t n=0;for(const ArenaBlock *b=(const ArenaBlock *)a->base;b;b=b->next)if(!b->free)n+=b->bytes+block_header();return n;}
static uint32_t word(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const uint8_t *p){uint32_t bits=word(p);float x;memcpy(&x,&bits,4);return x;}
static int16_t signed_half(const uint8_t *p){uint16_t bits=(uint16_t)(p[0]|(uint16_t)p[1]<<8);int16_t x;memcpy(&x,&bits,2);return x;}
typedef struct { uint32_t hash;uint8_t identity[32];int32_t cache_slot,base_slot; } Provider;
typedef struct { uint16_t id;uint32_t owners;void *bytes;WorldStreamingSceneSection view; } Section;
typedef struct { uint32_t first,count,texture_hash; } ModelBatch;
typedef struct {
    void *bytes,*gpu;uint16_t *indices;WorldStreamingSceneModel view;
    ModelBatch *batches;uint32_t batch_count;
    C3D_BufInfo buffer;float origin[3];
} Model;
typedef struct { C3D_Tex texture;uint32_t alpha_test,blend;bool initialized; } Texture;
typedef struct { uint16_t section,model;uint32_t instance; } Object;
typedef struct { uint32_t first,count;uint16_t object,texture; } Run;
typedef struct {
    uint32_t hash;uint8_t identity[32];int16_t triangles;float metric;bool mesh,valid;
} BaseInfo;
typedef struct {
    Section *sections[SECTION_LIMIT];uint32_t section_count;
    Provider *models,*textures;uint32_t model_count,texture_count;
    Object *objects;Run *runs;uint32_t object_count,run_count,triangles;
    uint8_t *references;uint16_t *reference_slots;uint32_t reference_count;
    uint32_t region;StreamedWorldView view;bool borrowed_providers;uint32_t fallback_bindings;
} Frame;
struct StreamedWorld {
    Arena arena;StreamedWorldConfig config;char asset_root[PATH_LIMIT];
    void *scratch,*metadata;WorldStreamingDatabase database;WorldStreamingSelector selector;
    WorldStreamingSceneCache cache;BaseInfo *base_info;uint32_t base_next;
    Frame frames[2];unsigned active;C3D_AttrInfo attributes;StreamedWorldStats stats;
};

static StreamedWorldResult error(StreamedWorld *w,StreamedWorldResult result,const char *what,uint32_t id){
    w->stats.result=result;snprintf(w->stats.detail,sizeof(w->stats.detail),"%s %08lx",what,(unsigned long)id);return result;
}
static StreamedWorldResult directory_read(StreamedWorld *w,StreamedWorldAssetKind kind,uint32_t id,const uint8_t identity[32],void *destination,size_t capacity,size_t *bytes){
    char path[PATH_LIMIT+100];int n;
    if(kind==STREAMED_WORLD_MODEL)n=snprintf(path,sizeof(path),"%s/models/%08lx.wsm",w->asset_root,(unsigned long)id);
    else if(kind==STREAMED_WORLD_SECTION)n=snprintf(path,sizeof(path),"%s/sections/%lu.wsi",w->asset_root,(unsigned long)id);
    else if(kind==STREAMED_WORLD_TEXTURE&&identity){
        char digest[65];for(unsigned i=0;i<32;i++)snprintf(digest+i*2,3,"%02x",identity[i]);
        n=snprintf(path,sizeof(path),"%s/textures/%08lx-%s.wtx",w->asset_root,(unsigned long)id,digest);
    }else return STREAMED_WORLD_INVALID;
    if(n<0||(size_t)n>=sizeof(path))return STREAMED_WORLD_INVALID;
    FILE *f=fopen(path,"rb");if(!f)return errno==ENOENT?STREAMED_WORLD_MISSING:STREAMED_WORLD_IO;
    if(fseek(f,0,SEEK_END)){fclose(f);return STREAMED_WORLD_IO;}long length=ftell(f);
    if(length<=0){fclose(f);return STREAMED_WORLD_FORMAT;}*bytes=(size_t)length;
    if(!destination){fclose(f);return capacity?STREAMED_WORLD_INVALID:STREAMED_WORLD_OK;}
    if(capacity<*bytes){fclose(f);return STREAMED_WORLD_CAPACITY;}
    rewind(f);bool ok=fread(destination,1,*bytes,f)==*bytes;fclose(f);return ok?STREAMED_WORLD_OK:STREAMED_WORLD_IO;
}
static StreamedWorldResult read_asset(StreamedWorld *w,StreamedWorldAssetKind kind,uint32_t id,const uint8_t identity[32],void *destination,size_t capacity,size_t *bytes){
    if(destination)w->stats.asset_reads++;else w->stats.asset_queries++;
    return w->config.read_asset?w->config.read_asset(w->config.read_context,kind,id,identity,destination,capacity,bytes):directory_read(w,kind,id,identity,destination,capacity,bytes);
}
static StreamedWorldResult scratch_asset(StreamedWorld *w,StreamedWorldAssetKind kind,uint32_t id,const uint8_t identity[32],size_t *bytes){
    StreamedWorldResult result=read_asset(w,kind,id,identity,NULL,0,bytes);
    if(result!=STREAMED_WORLD_OK)return error(w,result,"Cannot find asset",id);
    if(!*bytes||*bytes>w->config.scratch_bytes)return error(w,STREAMED_WORLD_BUDGET,"Scratch asset budget",id);
    size_t expected=*bytes;result=read_asset(w,kind,id,identity,w->scratch,w->config.scratch_bytes,bytes);
    if(result!=STREAMED_WORLD_OK||*bytes!=expected)return error(w,result==STREAMED_WORLD_OK?STREAMED_WORLD_FORMAT:result,"Cannot read asset",id);
    return STREAMED_WORLD_OK;
}
static int compare_provider(const void *left,const void *right){
    const Provider *a=left,*b=right;if(a->hash<b->hash)return -1;if(a->hash>b->hash)return 1;return memcmp(a->identity,b->identity,32);
}
static Provider *provider(Provider *p,uint32_t count,uint32_t hash){
    uint32_t low=0,high=count;while(low<high){uint32_t mid=low+(high-low)/2;if(p[mid].hash<hash)low=mid+1;else high=mid;}
    return low<count&&p[low].hash==hash?p+low:NULL;
}
static StreamedWorldResult provider_table(StreamedWorld *w,Frame *f,bool textures){
    uint32_t total=0;
    for(uint32_t i=0;i<f->section_count;i++){
        uint32_t n=textures?f->sections[i]->view.texture_count:f->sections[i]->view.model_count;
        if(n>65535-total)return error(w,STREAMED_WORLD_CAPACITY,"Provider table limit",0);
        total+=n;
    }
    Provider *table=total?arena_alloc(&w->arena,(size_t)total*sizeof(*table)):NULL;
    if(total&&!table)return error(w,STREAMED_WORLD_BUDGET,"Normal provider budget",0);
    uint32_t used=0;
    for(uint32_t i=0;i<f->section_count;i++){
        WorldStreamingSceneSection *s=&f->sections[i]->view;uint32_t count=textures?s->texture_count:s->model_count;
        for(uint32_t j=0;j<count;j++){
            WorldStreamingSceneBinding binding;
            bool ok=textures?world_streaming_scene_texture_binding(s,j,&binding):world_streaming_scene_model_binding(s,j,&binding);
            if(!ok){arena_free(&w->arena,table);return error(w,STREAMED_WORLD_FORMAT,"Invalid provider record",s->id);}
            table[used].hash=binding.hash;memcpy(table[used].identity,binding.identity,32);table[used].cache_slot=-1;table[used].base_slot=-1;used++;
        }
    }
    if(total)qsort(table,total,sizeof(*table),compare_provider);
    used=0;
    for(uint32_t i=0;i<total;i++){
        if(used&&table[i].hash==table[used-1].hash){
            if(memcmp(table[i].identity,table[used-1].identity,32)){uint32_t hash=table[i].hash;arena_free(&w->arena,table);return error(w,STREAMED_WORLD_AMBIGUOUS,"Conflicting active providers",hash);}
            continue;
        }
        table[used++]=table[i];
    }
    if(textures){f->textures=table;f->texture_count=used;}else{f->models=table;f->model_count=used;}
    return STREAMED_WORLD_OK;
}
static void collect_unused(StreamedWorld *w){
    for(size_t i=0;i<w->cache.capacity;i++){
        WorldStreamingSceneCacheEntry *entry=w->cache.entries+i;
        if(!entry->state||entry->references||entry->pins)continue;
        unsigned kind=entry->kind;void *resource=NULL;
        if(world_streaming_scene_cache_evict(&w->cache,i,&resource)!=WORLD_SCENE_OK||!resource)continue;
        if(kind==WORLD_SCENE_MODEL){Model *m=resource;if(m->gpu)linearFree(m->gpu);arena_free(&w->arena,m->batches);arena_free(&w->arena,m->bytes);arena_free(&w->arena,m);}
        else {Texture *t=resource;if(t->initialized)C3D_TexDelete(&t->texture);arena_free(&w->arena,t);}
    }
}
static void release_frame(StreamedWorld *w,Frame *f){
    for(uint32_t i=0;i<f->reference_count;i++)world_streaming_scene_cache_release(&w->cache,f->reference_slots[i]);
    memset(f->references,0,w->config.cache_entries);f->reference_count=0;
    for(uint32_t i=0;i<f->section_count;i++){
        Section *s=f->sections[i];if(--s->owners==0){arena_free(&w->arena,s->bytes);arena_free(&w->arena,s);}
    }
    f->section_count=0;if(!f->borrowed_providers){arena_free(&w->arena,f->models);arena_free(&w->arena,f->textures);}f->models=NULL;f->textures=NULL;f->borrowed_providers=false;
    f->model_count=f->texture_count=f->object_count=f->run_count=f->triangles=f->region=f->fallback_bindings=0;
}
static void own_reference(StreamedWorld *w,Frame *f,size_t slot){
    if(f->references[slot]){world_streaming_scene_cache_release(&w->cache,slot);return;}
    f->references[slot]=1;f->reference_slots[f->reference_count++]=(uint16_t)slot;
}
static int cache_exact(StreamedWorld *w,WorldStreamingSceneKind kind,Provider *p){
    if(p->cache_slot>=0&&(size_t)p->cache_slot<w->cache.capacity){
        const WorldStreamingSceneCacheEntry *e=w->cache.entries+p->cache_slot;
        if(e->state==2&&e->kind==kind&&e->hash==p->hash&&!memcmp(e->identity,p->identity,32))return p->cache_slot;
    }
    for(size_t i=0;i<w->cache.capacity;i++){
        const WorldStreamingSceneCacheEntry *e=w->cache.entries+i;
        if(e->state==2&&e->kind==kind&&e->hash==p->hash&&!memcmp(e->identity,p->identity,32)){p->cache_slot=(int32_t)i;return (int)i;}
    }
    return -1;
}
static StreamedWorldResult acquire_existing(StreamedWorld *w,Frame *f,WorldStreamingSceneKind kind,const Provider *p,size_t *slot){
    (void)kind;*slot=(size_t)p->cache_slot;
    if(f->references[*slot])return STREAMED_WORLD_OK;
    uint32_t generation=w->cache.entries[*slot].generation;
    if(world_streaming_scene_cache_retain(&w->cache,*slot,generation)!=WORLD_SCENE_OK)return error(w,STREAMED_WORLD_FORMAT,"Invalid cache reference",p->hash);
    own_reference(w,f,*slot);return STREAMED_WORLD_OK;
}
static StreamedWorldResult model_resource(StreamedWorld *w,Frame *f,uint32_t hash,size_t *slot){
    Provider *p=provider(f->models,f->model_count,hash);
    if(!p)return error(w,STREAMED_WORLD_MISSING,"No active model provider",hash);
    if(cache_exact(w,WORLD_SCENE_MODEL,p)>=0)return acquire_existing(w,f,WORLD_SCENE_MODEL,p,slot);
    size_t bytes;StreamedWorldResult result=scratch_asset(w,STREAMED_WORLD_MODEL,hash,p->identity,&bytes);if(result)return result;
    WorldStreamingSceneModel source;
    if(world_streaming_scene_model_open(w->scratch,bytes,&source)!=WORLD_SCENE_OK||source.hash!=hash||memcmp((uint8_t *)w->scratch+184,p->identity,32))return error(w,STREAMED_WORLD_FORMAT,"Invalid model identity/geometry",hash);
    Model *m=arena_alloc(&w->arena,sizeof(*m));void *payload=arena_alloc(&w->arena,bytes);
    if(!m||!payload){arena_free(&w->arena,m);arena_free(&w->arena,payload);return error(w,STREAMED_WORLD_BUDGET,"Normal model budget",hash);}
    memcpy(payload,w->scratch,bytes);m->bytes=payload;m->view=source;m->view.data=payload;
    /* Immutable source batch spans need decoding only once. Coalesce only
       adjacent identical texture hashes; original descriptors stay in payload.
       Stage-time GPU-state merging still handles effective fallback aliases. */
    ModelBatch previous={0};uint32_t spans=0;bool merge_batches=true;
#ifdef STREAMED_WORLD_DISABLE_RUN_MERGE
    merge_batches=false;
#endif
    for(uint32_t i=0;i<source.batch_count;i++){
        WorldStreamingSceneBatch b;
        if(!world_streaming_scene_model_batch(&m->view,i,&b)){
            arena_free(&w->arena,payload);arena_free(&w->arena,m);return error(w,STREAMED_WORLD_FORMAT,"Invalid immutable batch",hash);
        }
        if(!b.index_count)continue;
        if(merge_batches&&spans&&previous.texture_hash==b.texture_hash&&previous.first+previous.count==b.first_index)previous.count+=b.index_count;
        else {previous=(ModelBatch){b.first_index,b.index_count,b.texture_hash};spans++;}
    }
    if(spans){
        m->batches=arena_alloc(&w->arena,(size_t)spans*sizeof(*m->batches));
        if(!m->batches){arena_free(&w->arena,payload);arena_free(&w->arena,m);return error(w,STREAMED_WORLD_BUDGET,"Normal batch budget",hash);}
        for(uint32_t i=0;i<source.batch_count;i++){
            WorldStreamingSceneBatch b;world_streaming_scene_model_batch(&m->view,i,&b);if(!b.index_count)continue;
            ModelBatch *last=m->batch_count?m->batches+m->batch_count-1:NULL;
            if(merge_batches&&last&&last->texture_hash==b.texture_hash&&last->first+last->count==b.first_index)last->count+=b.index_count;
            else m->batches[m->batch_count++]=(ModelBatch){b.first_index,b.index_count,b.texture_hash};
        }
    }
    for(unsigned a=0;a<3;a++)m->origin[a]=(float)(((double)source.bounds[a]+source.bounds[a+3])*.5);
    size_t index_offset=padded((size_t)source.vertex_count*sizeof(WorldVertex),128);
    size_t linear_bytes=padded(index_offset+(size_t)source.index_count*2,128);
    size_t normal_bytes=arena_charge(m)+arena_charge(payload)+arena_charge(m->batches);uint32_t generation;
    WorldStreamingSceneResult acquired=world_streaming_scene_cache_acquire(&w->cache,WORLD_SCENE_MODEL,hash,p->identity,(uint32_t)normal_bytes,(uint32_t)linear_bytes,slot,&generation);
    if(acquired!=WORLD_SCENE_OK){arena_free(&w->arena,m->batches);arena_free(&w->arena,payload);arena_free(&w->arena,m);return error(w,acquired==WORLD_SCENE_CAPACITY?STREAMED_WORLD_CAPACITY:STREAMED_WORLD_BUDGET,"Model cache budget",hash);}
    if(!source.index_count){
        if(world_streaming_scene_cache_ready(&w->cache,*slot,generation,m)!=WORLD_SCENE_OK){result=error(w,STREAMED_WORLD_FORMAT,"Empty model ready transition",hash);goto failed;}
        own_reference(w,f,*slot);return STREAMED_WORLD_OK;
    }
    m->gpu=linearMemAlign(linear_bytes,128);
    if(!m->gpu){result=error(w,STREAMED_WORLD_BUDGET,"Linear model allocation",hash);goto failed;}
    memset(m->gpu,0,linear_bytes);m->indices=(uint16_t *)((uint8_t *)m->gpu+index_offset);
    if(world_streaming_scene_model_expand_rebased(&m->view,m->origin,w->config.render_scale,m->gpu,source.vertex_count,m->indices,source.index_count)!=WORLD_SCENE_OK){result=error(w,STREAMED_WORLD_FORMAT,"Model expansion",hash);goto failed;}
    GSPGPU_FlushDataCache(m->gpu,(u32)linear_bytes);BufInfo_Init(&m->buffer);
    if(BufInfo_Add(&m->buffer,m->gpu,sizeof(WorldVertex),3,0x210)<0){result=error(w,STREAMED_WORLD_FORMAT,"Model GPU buffer",hash);goto failed;}
    if(world_streaming_scene_cache_ready(&w->cache,*slot,generation,m)!=WORLD_SCENE_OK){result=error(w,STREAMED_WORLD_FORMAT,"Model ready transition",hash);goto failed;}
    w->stats.model_uploads++;
    own_reference(w,f,*slot);return STREAMED_WORLD_OK;
failed:
    if(m->gpu)linearFree(m->gpu);
    arena_free(&w->arena,m->batches);arena_free(&w->arena,payload);arena_free(&w->arena,m);
    world_streaming_scene_cache_release(&w->cache,*slot);void *unused=NULL;world_streaming_scene_cache_evict(&w->cache,*slot,&unused);return result;
}
static StreamedWorldResult texture_resource(StreamedWorld *w,Frame *f,uint32_t hash,size_t *slot){
    Provider *p=provider(f->textures,f->texture_count,hash);
    if(!p&&w->config.original_missing_texture_hash){
        /* Original generic model fixup requests bTextureLookup(hash,1,0).
           Final lookup miss returns the actual registered DEFAULTALPHA. A
           declared provider with broken bytes must NEVER enter this branch. */
        p=provider(f->textures,f->texture_count,w->config.original_missing_texture_hash);
        if(!p)return error(w,STREAMED_WORLD_MISSING,"Original default provider absent",hash);
        f->fallback_bindings++;hash=p->hash;
    }
    if(!p)return error(w,STREAMED_WORLD_MISSING,"No active texture provider",hash);
    if(cache_exact(w,WORLD_SCENE_TEXTURE,p)>=0)return acquire_existing(w,f,WORLD_SCENE_TEXTURE,p,slot);
    size_t bytes;StreamedWorldResult result=scratch_asset(w,STREAMED_WORLD_TEXTURE,hash,p->identity,&bytes);if(result)return result;
    WorldStreamingSceneTexture source;
    if(world_streaming_scene_texture_open(w->scratch,bytes,&source)!=WORLD_SCENE_OK||source.hash!=hash||memcmp(source.identity,p->identity,32)||source.width<8||source.height<8||source.width>1024||source.height>1024||source.blend>2)return error(w,STREAMED_WORLD_FORMAT,"Invalid/unsupported texture",hash);
    Texture *t=arena_alloc(&w->arena,sizeof(*t));if(!t)return error(w,STREAMED_WORLD_BUDGET,"Normal texture budget",hash);
    uint32_t generation;WorldStreamingSceneResult acquired=world_streaming_scene_cache_acquire(&w->cache,WORLD_SCENE_TEXTURE,hash,p->identity,(uint32_t)arena_charge(t),source.rgba_bytes,slot,&generation);
    if(acquired!=WORLD_SCENE_OK){arena_free(&w->arena,t);return error(w,acquired==WORLD_SCENE_CAPACITY?STREAMED_WORLD_CAPACITY:STREAMED_WORLD_BUDGET,"Texture cache budget",hash);}
    if(!C3D_TexInit(&t->texture,(u16)source.width,(u16)source.height,GPU_RGBA8)){result=error(w,STREAMED_WORLD_BUDGET,"Linear texture allocation",hash);goto failed;}
    t->initialized=true;t->alpha_test=source.alpha_test;t->blend=source.blend;
    if(t->texture.size!=source.rgba_bytes||!streamed_world_texture_rgba8(t->texture.data,t->texture.size,source.rgba,source.width,source.height,source.alpha_test,source.blend,w->config.comparison_zero_transparent_rgb)){result=error(w,STREAMED_WORLD_FORMAT,"Texture GPU upload",hash);goto failed;}
    C3D_TexFlush(&t->texture);C3D_TexSetFilter(&t->texture,GPU_LINEAR,GPU_NEAREST);C3D_TexSetWrap(&t->texture,GPU_REPEAT,GPU_REPEAT);
    if(world_streaming_scene_cache_ready(&w->cache,*slot,generation,t)!=WORLD_SCENE_OK){result=error(w,STREAMED_WORLD_FORMAT,"Texture ready transition",hash);goto failed;}
    w->stats.texture_uploads++;
    own_reference(w,f,*slot);return STREAMED_WORLD_OK;
failed:
    if(t->initialized)C3D_TexDelete(&t->texture);
    arena_free(&w->arena,t);
    world_streaming_scene_cache_release(&w->cache,*slot);void *unused=NULL;world_streaming_scene_cache_evict(&w->cache,*slot,&unused);return result;
}
static StreamedWorldResult base_info(StreamedWorld *w,Frame *f,uint32_t hash,BaseInfo *out){
    memset(out,0,sizeof(*out));Provider *p=provider(f->models,f->model_count,hash);if(!p)return STREAMED_WORLD_OK;
    if(p->base_slot>=0&&(uint32_t)p->base_slot<w->config.cache_entries){
        BaseInfo *b=w->base_info+p->base_slot;
        if(b->valid&&b->hash==hash&&!memcmp(b->identity,p->identity,32)){*out=*b;return STREAMED_WORLD_OK;}
    }
    for(uint32_t i=0;i<w->config.cache_entries;i++)if(w->base_info[i].valid&&w->base_info[i].hash==hash&&!memcmp(w->base_info[i].identity,p->identity,32)){p->base_slot=(int32_t)i;*out=w->base_info[i];return STREAMED_WORLD_OK;}
    size_t bytes;StreamedWorldResult result=scratch_asset(w,STREAMED_WORLD_MODEL,hash,p->identity,&bytes);if(result)return result;
    WorldStreamingSceneModel m;
    if(world_streaming_scene_model_open(w->scratch,bytes,&m)!=WORLD_SCENE_OK||m.hash!=hash||memcmp((uint8_t *)w->scratch+184,p->identity,32))return error(w,STREAMED_WORLD_FORMAT,"Invalid base LOD model",hash);
    out->hash=hash;memcpy(out->identity,p->identity,32);out->triangles=signed_half(m.data+m.source_header+20);out->metric=real(m.data+m.source_header+156);out->mesh=m.index_count!=0;out->valid=true;
    if(!isfinite(out->metric))return error(w,STREAMED_WORLD_FORMAT,"Invalid source LOD metric",hash);
    p->base_slot=(int32_t)(w->base_next++%w->config.cache_entries);w->base_info[p->base_slot]=*out;return STREAMED_WORLD_OK;
}
static float lod_sqrt(float squared,void *context){(void)context;return mw_gekko_sqrt_newton2(squared);}
static bool visible_bounds(const float bounds[6],const StreamedWorldView *view,const WorldFrustum *frustum){
    WorldBounds b;unsigned source_axis[3]={0,2,1};
    for(unsigned a=0;a<3;a++){
        unsigned s=source_axis[a];double center=((double)bounds[s]+bounds[s+3])*.5;
        if(a==2)center=-center;
        b.center[a]=(float)(center-view->camera_viewer[a]);b.extent[a]=(bounds[s+3]-bounds[s])*.5f;
    }
    return world_visible(frustum,&b);
}
static StreamedWorldResult stage_sections(StreamedWorld *w,Frame *f,uint16_t dependency_index){
    uint16_t ids[SECTION_LIMIT];size_t count=0;
    if(world_streaming_plan(&w->database,&dependency_index,1,ids,SECTION_LIMIT,&count)!=WORLD_STREAMING_OK)return error(w,STREAMED_WORLD_CAPACITY,"Section request limit",0);
    if(w->config.boot_global_provider_bank){
        if(count>=SECTION_LIMIT)return error(w,STREAMED_WORLD_CAPACITY,"Boot provider bank limit",0);
        ids[count++]=0; /* Export-only global namespace: do not query WST for0. */
    }
    Frame *old=&w->frames[w->active];
    bool same=count==old->section_count;
    for(size_t i=0;same&&i<count;i++)if(old->sections[i]->id!=ids[i])same=false;
    if(same){
        for(size_t i=0;i<count;i++){old->sections[i]->owners++;f->sections[f->section_count++]=old->sections[i];}
        f->models=old->models;f->model_count=old->model_count;f->textures=old->textures;f->texture_count=old->texture_count;f->borrowed_providers=true;
        return STREAMED_WORLD_OK;
    }
    for(size_t i=0;i<count;i++){
        Section *s=NULL;for(uint32_t j=0;j<old->section_count;j++)if(old->sections[j]->id==ids[i]){s=old->sections[j];break;}
        if(s){s->owners++;f->sections[f->section_count++]=s;continue;}
        size_t bytes=0;StreamedWorldResult result=read_asset(w,STREAMED_WORLD_SECTION,ids[i],NULL,NULL,0,&bytes);
        if(result!=STREAMED_WORLD_OK)return error(w,result,"Cannot find section",ids[i]);
        if(!bytes||bytes>16*1024*1024)return error(w,STREAMED_WORLD_FORMAT,"Invalid section size",ids[i]);
        s=arena_alloc(&w->arena,sizeof(*s));void *payload=arena_alloc(&w->arena,bytes);
        if(!s||!payload){arena_free(&w->arena,s);arena_free(&w->arena,payload);return error(w,STREAMED_WORLD_BUDGET,"Normal section budget",ids[i]);}
        size_t actual=bytes;result=read_asset(w,STREAMED_WORLD_SECTION,ids[i],NULL,payload,bytes,&actual);
        if(result!=STREAMED_WORLD_OK||actual!=bytes||world_streaming_scene_section_open(payload,bytes,&s->view)!=WORLD_SCENE_OK||s->view.id!=ids[i]){
            arena_free(&w->arena,payload);arena_free(&w->arena,s);return error(w,result==STREAMED_WORLD_OK?STREAMED_WORLD_FORMAT:result,"Invalid section payload",ids[i]);
        }
        s->bytes=payload;s->id=ids[i];s->owners=1;f->sections[f->section_count++]=s;
    }
    StreamedWorldResult result=provider_table(w,f,false);return result?result:provider_table(w,f,true);
}
static StreamedWorldResult stage_draws(StreamedWorld *w,Frame *f){
    float zero[3]={0,0,0};WorldFrustum frustum;
    if(!world_frustum(&frustum,zero,f->view.forward_viewer,f->view.vertical_fov_radians,f->view.aspect,f->view.near_world,f->view.far_world))return error(w,STREAMED_WORLD_INVALID,"Invalid camera frustum",0);
    float camera[3]={(float)f->view.camera_viewer[0],(float)-f->view.camera_viewer[2],(float)f->view.camera_viewer[1]};
    float forward[3]={f->view.forward_viewer[0],-f->view.forward_viewer[2],f->view.forward_viewer[1]};
    float projection=mw_lod_projection_raw(f->view.original_fov_turn);
    bool standard_up=fabsf(f->view.up_viewer[0])<1e-6f&&fabsf(f->view.up_viewer[2])<1e-6f&&f->view.up_viewer[1]>0;
    for(uint32_t s=0;s<f->section_count;s++)for(uint32_t i=0;i<f->sections[s]->view.instance_count;i++){
        const uint8_t *source_instance=f->sections[s]->view.data+
            f->sections[s]->view.instances+i*144+8;
        uint32_t effective_flags=word(source_instance+24);
        if(w->config.instance_state&&!w->config.instance_state(w->config.instance_state_context,
            word(source_instance-8),effective_flags,&effective_flags))
            return error(w,STREAMED_WORLD_FORMAT,"Source activation flags differ",word(source_instance-8));
        if(!mw_lod_instance_visible(effective_flags,f->view.original_context_flags))continue;
        /* Section open has validated these immutable records. Reject by the
           exact same bounds before decoding nine matrix elements/four LODs. */
        if(standard_up){
            const WorldStreamingSceneSection *section=&f->sections[s]->view;
            const uint8_t *record=section->data+section->instances+i*144+8;
            float bounds[6];for(unsigned a=0;a<6;a++)bounds[a]=real(record+a*4);
            if(!visible_bounds(bounds,&f->view,&frustum))continue;
        }
        WorldStreamingSceneInstance instance;
        if(!world_streaming_scene_instance(&f->sections[s]->view,i,&instance))return error(w,STREAMED_WORLD_FORMAT,"Invalid instance",f->sections[s]->id);
        int slot=0;
        if(w->config.lod_mode==STREAMED_WORLD_SOURCE_LOD_COMPONENTS){
            MwLodSelectInput input={0};input.instance_flags=effective_flags;input.context_flags=f->view.original_context_flags;input.original_view_state=f->view.original_view_state;
            for(unsigned k=0;k<4;k++)if(instance.bound_slots[k])input.bound_slot_mask|=1u<<k;
            if(!mw_lod_projected_score(instance.translation,camera,forward,real(instance.original_object+56),projection,lod_sqrt,NULL,&input.projected_score))return error(w,STREAMED_WORLD_FORMAT,"Invalid original LOD operands",instance.source_instance_offset);
            if(input.projected_score<=1)continue;
            BaseInfo base;StreamedWorldResult result=base_info(w,f,instance.bound_slots[0],&base);if(result)return result;
            input.slot0_has_mesh=base.mesh;input.slot0_header_triangle_statistic=base.triangles;input.slot0_header_metric_9c=base.metric;slot=mw_lod_select(&input);
        }
        if(slot<0||!instance.bound_slots[slot])continue;
        size_t model_slot;StreamedWorldResult result=model_resource(w,f,instance.bound_slots[slot],&model_slot);if(result)return result;
        Model *m=w->cache.entries[model_slot].resource;if(!m->view.index_count)continue;
        if(f->object_count>=w->config.object_capacity)return error(w,STREAMED_WORLD_CAPACITY,"Visible instance limit",0);
        uint32_t object=f->object_count++;
        f->objects[object]=(Object){(uint16_t)s,(uint16_t)model_slot,i};
        for(uint32_t b=0;b<m->batch_count;b++){
            const ModelBatch *batch=m->batches+b;
            size_t texture_slot;result=texture_resource(w,f,batch->texture_hash,&texture_slot);if(result)return result;
            /* WSM retains every original descriptor/material record. The current
               shader consumes no per-descriptor state beyond the resolved WTX;
               merge only this adjacent identical GPU state, preserving indices.
               Add any future consumed material state to this equality first. */
            Run *previous=f->run_count?f->runs+f->run_count-1:NULL;
            bool merge_allowed=true;
#ifdef STREAMED_WORLD_DISABLE_RUN_MERGE
            merge_allowed=false; /* Offline ordered-state reference only. */
#endif
            if(merge_allowed&&previous&&previous->object==object&&previous->texture==texture_slot&&previous->first+previous->count==batch->first)previous->count+=batch->count;
            else {
                if(f->run_count>=w->config.run_capacity)return error(w,STREAMED_WORLD_CAPACITY,"Draw run limit",0);
                f->runs[f->run_count++]=(Run){batch->first,batch->count,(uint16_t)object,(uint16_t)texture_slot};
            }
            f->triangles+=batch->count/3;
        }
    }
    return STREAMED_WORLD_OK;
}
static void update_stats(StreamedWorld *w){
    Frame *f=&w->frames[w->active];w->stats.region=f->region;w->stats.boot_provider_banks=w->config.boot_global_provider_bank&&f->section_count?1:0;
    w->stats.source_sections=f->section_count-w->stats.boot_provider_banks;w->stats.visible_instances=f->object_count;w->stats.draw_runs=f->run_count;w->stats.triangles=f->triangles;
    w->stats.texture_fallback_bindings=f->fallback_bindings;
    w->stats.normal_used=(uint32_t)arena_used(&w->arena);w->stats.normal_budget=w->config.normal_bytes;w->stats.linear_used=w->cache.linear_used;w->stats.linear_budget=w->config.linear_bytes;w->stats.scratch_bytes=w->config.scratch_bytes;
    w->stats.arena_allocations=w->arena.allocations;
    w->stats.resident_models=w->stats.resident_textures=0;
    for(size_t i=0;i<w->cache.capacity;i++)if(w->cache.entries[i].state==2){if(w->cache.entries[i].kind==WORLD_SCENE_MODEL)w->stats.resident_models++;else w->stats.resident_textures++;}
}
StreamedWorldResult streamed_world_create(const StreamedWorldConfig *config,StreamedWorld **out){
    if(!out)return STREAMED_WORLD_INVALID;
    *out=NULL;
    if(!config||!config->metadata_path||(!config->asset_root&&!config->read_asset)||config->normal_bytes<1024*1024||config->normal_bytes>128*1024*1024||!config->linear_bytes||config->scratch_bytes<256||config->scratch_bytes>32*1024*1024||
       !config->cache_entries||config->cache_entries>65535||!config->object_capacity||config->object_capacity>65535||!config->run_capacity||config->run_capacity>1000000||
       !isfinite(config->render_scale)||config->render_scale<=0||(config->lod_mode!=STREAMED_WORLD_REFERENCE_SLOT0&&config->lod_mode!=STREAMED_WORLD_SOURCE_LOD_COMPONENTS)||
       (config->original_missing_texture_hash&&config->original_missing_texture_hash!=0x66994f4au))return STREAMED_WORLD_INVALID;
    void *memory=memalign(NORMAL_ALIGN,config->normal_bytes);if(!memory)return STREAMED_WORLD_BUDGET;
    Arena arena={memory,config->normal_bytes,0};*(ArenaBlock *)memory=(ArenaBlock){config->normal_bytes-block_header(),NULL,true};
    StreamedWorld *w=arena_alloc(&arena,sizeof(*w));if(!w){free(memory);return STREAMED_WORLD_BUDGET;}w->arena=arena;w->config=*config;
    if(config->asset_root&&snprintf(w->asset_root,sizeof(w->asset_root),"%s",config->asset_root)>=(int)sizeof(w->asset_root)){free(memory);return STREAMED_WORLD_INVALID;}
    w->scratch=malloc(config->scratch_bytes);if(!w->scratch){free(memory);return STREAMED_WORLD_BUDGET;}
    FILE *file=fopen(config->metadata_path,"rb");if(!file){free(w->scratch);free(memory);return STREAMED_WORLD_IO;}
    if(fseek(file,0,SEEK_END)){fclose(file);free(w->scratch);free(memory);return STREAMED_WORLD_IO;}long bytes=ftell(file);rewind(file);
    if(bytes<0){fclose(file);free(w->scratch);free(memory);return STREAMED_WORLD_IO;}
    if(bytes<128||bytes>256*1024){fclose(file);free(w->scratch);free(memory);return STREAMED_WORLD_FORMAT;}
    w->metadata=arena_alloc(&w->arena,(size_t)bytes);
    if(!w->metadata){fclose(file);free(w->scratch);free(memory);return STREAMED_WORLD_BUDGET;}
    bool ok=fread(w->metadata,1,(size_t)bytes,file)==(size_t)bytes;fclose(file);
    if(!ok){free(w->scratch);free(memory);return STREAMED_WORLD_IO;}
    if(world_streaming_open(w->metadata,(size_t)bytes,&w->database)!=WORLD_STREAMING_OK){free(w->scratch);free(memory);return STREAMED_WORLD_FORMAT;}
    WorldStreamingSceneCacheEntry *entries=arena_alloc(&w->arena,(size_t)config->cache_entries*sizeof(*entries));w->base_info=arena_alloc(&w->arena,(size_t)config->cache_entries*sizeof(*w->base_info));
    world_streaming_scene_cache_init(&w->cache,entries,config->cache_entries,config->normal_bytes,config->linear_bytes);
    for(unsigned i=0;i<2;i++){
        Frame *f=w->frames+i;f->objects=arena_alloc(&w->arena,(size_t)config->object_capacity*sizeof(*f->objects));f->runs=arena_alloc(&w->arena,(size_t)config->run_capacity*sizeof(*f->runs));
        f->references=arena_alloc(&w->arena,config->cache_entries);f->reference_slots=arena_alloc(&w->arena,(size_t)config->cache_entries*2);
        if(!f->objects||!f->runs||!f->references||!f->reference_slots)ok=false;
    }
    if(!entries||!w->base_info||!ok){free(w->scratch);free(memory);return STREAMED_WORLD_BUDGET;}
    world_streaming_selector_init(&w->database,&w->selector);AttrInfo_Init(&w->attributes);AttrInfo_AddLoader(&w->attributes,0,GPU_FLOAT,3);AttrInfo_AddLoader(&w->attributes,1,GPU_FLOAT,2);AttrInfo_AddLoader(&w->attributes,2,GPU_FLOAT,4);
    *out=w;update_stats(w);return STREAMED_WORLD_OK;
}
static bool same_view(const StreamedWorldView *a,const StreamedWorldView *b){
    for(unsigned i=0;i<3;i++)if(a->camera_viewer[i]!=b->camera_viewer[i]||a->forward_viewer[i]!=b->forward_viewer[i]||a->up_viewer[i]!=b->up_viewer[i])return false;
    return a->vertical_fov_radians==b->vertical_fov_radians&&a->aspect==b->aspect&&
        a->near_world==b->near_world&&a->far_world==b->far_world&&
        a->original_fov_turn==b->original_fov_turn&&a->original_view_state==b->original_view_state&&
        a->original_context_flags==b->original_context_flags;
}
StreamedWorldResult streamed_world_prepare(StreamedWorld *w,float source_x,float source_y,const StreamedWorldView *view){
    if(!w||!view||!isfinite(source_x)||!isfinite(source_y))return STREAMED_WORLD_INVALID;
    for(unsigned a=0;a<3;a++)if(!isfinite(view->camera_viewer[a])||fabs(view->camera_viewer[a])>1e7||!isfinite(view->forward_viewer[a])||!isfinite(view->up_viewer[a]))return error(w,STREAMED_WORLD_INVALID,"Invalid camera",0);
    float forward_length=0,up_length=0,dot=0;
    for(unsigned a=0;a<3;a++){forward_length+=view->forward_viewer[a]*view->forward_viewer[a];up_length+=view->up_viewer[a]*view->up_viewer[a];dot+=view->forward_viewer[a]*view->up_viewer[a];}
    if(forward_length<.9f||forward_length>1.1f||up_length<.9f||up_length>1.1f||dot*dot>forward_length*up_length-.0001f)return error(w,STREAMED_WORLD_INVALID,"Invalid camera basis",0);
    WorldStreamingSelector candidate=w->selector;uint16_t selected;
    WorldStreamingResult selection=world_streaming_select(&w->database,&candidate,source_x,source_y,&selected);
    if(selection!=WORLD_STREAMING_OK){update_stats(w);return error(w,selection==WORLD_STREAMING_NEAREST_REQUIRED?STREAMED_WORLD_NEAREST_REQUIRED:STREAMED_WORLD_FORMAT,"Original region selection",0);}
    uint32_t region=(uint32_t)(w->database.data[w->database.dependencies+selected*12]|(uint16_t)w->database.data[w->database.dependencies+selected*12+1]<<8);
    Frame *current=&w->frames[w->active];
    if(current->section_count&&current->region==region&&same_view(&current->view,view)){
        /* Immutable resources and exact same camera/context: preserve the
           complete draw plan, without touching references or GPU ownership. */
        w->selector=candidate;w->stats.result=STREAMED_WORLD_OK;w->stats.detail[0]=0;return STREAMED_WORLD_OK;
    }
    C3D_FrameSync();Frame *next=&w->frames[1-w->active];release_frame(w,next);collect_unused(w);next->view=*view;
    next->region=region;
    StreamedWorldResult result=stage_sections(w,next,selected);if(!result)result=stage_draws(w,next);
    if(result){release_frame(w,next);collect_unused(w);update_stats(w);return result;}
    unsigned old=w->active;if(next->borrowed_providers){w->frames[old].models=NULL;w->frames[old].textures=NULL;next->borrowed_providers=false;}
    w->active=1-old;w->selector=candidate;release_frame(w,&w->frames[old]);collect_unused(w);update_stats(w);w->stats.result=STREAMED_WORLD_OK;w->stats.detail[0]=0;return STREAMED_WORLD_OK;
}
static void object_matrix(StreamedWorld *w,const Frame *f,const Object *object,C3D_Mtx *out,const C3D_Mtx *rotation){
    WorldStreamingSceneInstance instance;world_streaming_scene_instance(&f->sections[object->section]->view,object->instance,&instance);
    Model *m=w->cache.entries[object->model].resource;C3D_Mtx local;Mtx_Identity(&local);
    double origin[3];for(unsigned a=0;a<3;a++){origin[a]=instance.translation[a];for(unsigned c=0;c<3;c++)origin[a]+=(double)m->origin[c]*instance.matrix[c*3+a];}
    float *r=instance.matrix;
    local.r[0]=FVec4_New(r[0],r[3],r[6],(float)((origin[0]-f->view.camera_viewer[0])*w->config.render_scale));
    local.r[1]=FVec4_New(r[2],r[5],r[8],(float)((origin[2]-f->view.camera_viewer[1])*w->config.render_scale));
    local.r[2]=FVec4_New(-r[1],-r[4],-r[7],(float)((-origin[1]-f->view.camera_viewer[2])*w->config.render_scale));
    Mtx_Multiply(out,rotation,&local);
}
void streamed_world_draw(StreamedWorld *w,shaderProgram_s *program,int projection_location,int model_location,const C3D_Mtx *projection){
    if(!w||!program||!projection||projection_location<0||model_location<0)return;
    Frame *f=&w->frames[w->active];if(!f->object_count)return;
    C3D_Mtx rotation;Mtx_LookAt(&rotation,FVec3_New(0,0,0),FVec3_New(f->view.forward_viewer[0],f->view.forward_viewer[1],f->view.forward_viewer[2]),FVec3_New(f->view.up_viewer[0],f->view.up_viewer[1],f->view.up_viewer[2]),false);
    C3D_BindProgram(program);C3D_SetAttrInfo(&w->attributes);C3D_CullFace(GPU_CULL_NONE);C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,projection_location,projection);
    C3D_TexEnv *environment=C3D_GetTexEnv(0);C3D_TexEnvInit(environment);C3D_TexEnvSrc(environment,C3D_Both,GPU_TEXTURE0,GPU_PRIMARY_COLOR,0);C3D_TexEnvFunc(environment,C3D_Both,GPU_MODULATE);
    for(unsigned pass=0;pass<2;pass++){
        unsigned last_object=UINT_MAX,last_texture=UINT_MAX;
        for(uint32_t i=0;i<f->run_count;i++){
            const Run *run=f->runs+i;Texture *texture=w->cache.entries[run->texture].resource;
            if((texture->blend!=0)!=(pass!=0))continue;
            const Object *object=f->objects+run->object;Model *model=w->cache.entries[object->model].resource;
            if(last_object!=run->object){C3D_Mtx matrix;object_matrix(w,f,object,&matrix,&rotation);C3D_FVUnifMtx4x4(GPU_VERTEX_SHADER,model_location,&matrix);C3D_SetBufInfo(&model->buffer);last_object=run->object;}
            if(last_texture!=run->texture){
                C3D_TexBind(0,&texture->texture);C3D_AlphaTest(texture->alpha_test==1,GPU_GREATER,w->config.alpha_reference);
                C3D_DepthTest(true,GPU_GREATER,texture->blend?GPU_WRITE_COLOR:GPU_WRITE_ALL);
                C3D_AlphaBlend(GPU_BLEND_ADD,GPU_BLEND_ADD,texture->blend?GPU_SRC_ALPHA:GPU_ONE,texture->blend==2?GPU_ONE:(texture->blend?GPU_ONE_MINUS_SRC_ALPHA:GPU_ZERO),GPU_ONE,texture->blend?GPU_ONE_MINUS_SRC_ALPHA:GPU_ZERO);
                last_texture=run->texture;
            }
            C3D_DrawElements(GPU_TRIANGLES,(int)run->count,C3D_UNSIGNED_SHORT,model->indices+run->first);
        }
    }
}
void streamed_world_stats(const StreamedWorld *w,StreamedWorldStats *out){if(w&&out)*out=w->stats;}
StreamedWorldResult streamed_world_sections(const StreamedWorld *w,uint16_t *ids,size_t capacity,size_t *count){
    if(!w||!count||(!ids&&capacity))return STREAMED_WORLD_INVALID;
    const Frame *f=&w->frames[w->active];size_t needed=0;
    for(uint32_t i=0;i<f->section_count;i++)if(f->sections[i]->id)needed++;
    *count=needed;if(capacity<needed)return STREAMED_WORLD_CAPACITY;
    size_t used=0;for(uint32_t i=0;i<f->section_count;i++)if(f->sections[i]->id)ids[used++]=f->sections[i]->id;
    return STREAMED_WORLD_OK;
}
void streamed_world_destroy(StreamedWorld *w){
    if(!w)return;
    C3D_FrameSync();release_frame(w,w->frames);release_frame(w,w->frames+1);collect_unused(w);void *scratch=w->scratch,*memory=w->arena.base;free(scratch);free(memory);
}
