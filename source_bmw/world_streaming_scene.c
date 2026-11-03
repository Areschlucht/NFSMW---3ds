#include "world_streaming_scene.h"
#include <math.h>
#include <string.h>
#include <limits.h>

static uint16_t u16(const uint8_t *p){return (uint16_t)(p[0]|(uint16_t)p[1]<<8);}
static int16_t s16(const uint8_t *p){uint16_t value=u16(p);int16_t result;memcpy(&result,&value,2);return result;}
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float f32(const uint8_t *p){uint32_t value=u32(p);float result;memcpy(&result,&value,4);return result;}
static uint32_t align4(uint32_t value){return (value+3)&~3u;}
static uint32_t crc(const uint8_t *p,size_t count,size_t checksum_field){
    uint32_t value=0xffffffff;
    for(size_t i=0;i<count;i++){value^=i>=checksum_field&&i<checksum_field+4?0:p[i];for(unsigned b=0;b<8;b++)value=(value>>1)^((0-(value&1))&0xedb88320);}
    return ~value;
}
WorldStreamingSceneResult world_streaming_scene_model_open(const void *bytes,size_t size,WorldStreamingSceneModel *out){
    if(!out)return WORLD_SCENE_INVALID;
    memset(out,0,sizeof(*out));const uint8_t *p=bytes;
    if(!p||size<256||size>32*1024*1024||memcmp(p,"WSM1",4)||u32(p+4)!=1||u32(p+8)!=size||u32(p+60)>1||u32(p+56)!=crc(p,size,56))return WORLD_SCENE_INVALID;
    bool empty=u32(p+60)==1;
    WorldStreamingSceneModel m={0};m.data=p;m.size=size;m.hash=u32(p+12);m.vertex_count=u32(p+16);m.index_count=u32(p+20);m.batch_count=u32(p+24);
    m.declared_triangles=u32(p+28);m.emitted_triangles=u32(p+32);m.vertices=u32(p+36);m.indices=u32(p+40);m.batches=u32(p+44);m.night_alpha=u32(p+48);m.source_header=u32(p+240);
    if((empty&&(m.vertex_count||m.index_count||m.batch_count||m.declared_triangles||m.emitted_triangles||u32(p+52)))||
       (!empty&&(!m.vertex_count||!m.index_count||!m.batch_count||(u32(p+52)!=1&&u32(p+52)!=32)))||
       m.vertex_count>65535||m.index_count%3||m.index_count>3000000||m.batch_count>65535||
       m.vertices!=256||m.indices!=256+m.vertex_count*20||m.batches!=align4(m.indices+m.index_count*2)||
       m.night_alpha!=m.batches+m.batch_count*36||m.source_header!=align4(m.night_alpha+m.vertex_count)||u32(p+244)!=160||
       size!=(size_t)m.source_header+160||u32(p+228)!=m.vertex_count*36+m.index_count*2||u32(p+232)!=size||u32(p+236))return WORLD_SCENE_INVALID;
    for(unsigned i=0;i<6;i++){m.bounds[i]=f32(p+64+i*4);if(!isfinite(m.bounds[i]))return WORLD_SCENE_INVALID;}
    for(unsigned i=0;i<3;i++){
        if(empty){if(u32(p+64+i*4)!=0x7f7fffffu||u32(p+76+i*4)!=0xff7fffffu)return WORLD_SCENE_INVALID;}
        else if(m.bounds[i]>m.bounds[i+3])return WORLD_SCENE_INVALID;
    }
    for(unsigned i=0;i<16;i++){m.header_matrix[i]=f32(p+88+i*4);if(!isfinite(m.header_matrix[i]))return WORLD_SCENE_INVALID;}
    for(uint32_t i=0;i<m.vertex_count;i++){
        const uint8_t *v=p+m.vertices+i*20;
        for(unsigned a=0;a<3;a++){float position=f32(v+a*4);if(!isfinite(position)||position<m.bounds[a]-.05f||position>m.bounds[a+3]+.05f)return WORLD_SCENE_INVALID;}
        if(v[19]!=255)return WORLD_SCENE_INVALID;
    }
    for(uint32_t i=0;i<m.index_count;i++)if(u16(p+m.indices+i*2)>=m.vertex_count)return WORLD_SCENE_INVALID;
    uint32_t expected=0;
    for(uint32_t i=0;i<m.batch_count;i++){
        const uint8_t *b=p+m.batches+i*36;uint32_t first=u32(b),count=u32(b+4);
        if(first!=expected||count%3||count>m.index_count-first||u32(b+8)!=u32(b+28))return WORLD_SCENE_INVALID;
        expected+=count;
    }
    if(expected!=m.index_count||m.emitted_triangles!=m.index_count/3)return WORLD_SCENE_INVALID;
    *out=m;return WORLD_SCENE_OK;
}
WorldStreamingSceneResult world_streaming_scene_model_expand(const WorldStreamingSceneModel *m,WorldVertex *vertices,size_t nv,uint16_t *indices,size_t ni){
    if(!m||!m->data)return WORLD_SCENE_INVALID;
    if(!m->vertex_count&&!m->index_count)return WORLD_SCENE_OK;
    if(!vertices||!indices)return WORLD_SCENE_INVALID;
    if(nv<m->vertex_count||ni<m->index_count)return WORLD_SCENE_CAPACITY;
    for(uint32_t i=0;i<m->vertex_count;i++){
        const uint8_t *v=m->data+m->vertices+i*20;
        for(unsigned a=0;a<3;a++)vertices[i].position[a]=f32(v+a*4);
        vertices[i].uv[0]=(float)s16(v+12)/4096.0f;vertices[i].uv[1]=1.0f-(float)s16(v+14)/4096.0f;
        for(unsigned a=0;a<3;a++)vertices[i].color[a]=(float)v[16+a]/255.0f;
        vertices[i].color[3]=1.0f;
    }
    for(uint32_t i=0;i<m->index_count;i++)indices[i]=u16(m->data+m->indices+i*2);
    return WORLD_SCENE_OK;
}
WorldStreamingSceneResult world_streaming_scene_model_expand_rebased(const WorldStreamingSceneModel *m,const float origin[3],float scale,WorldVertex *vertices,size_t nv,uint16_t *indices,size_t ni){
    if(!m||!m->data||!origin||!isfinite(scale)||scale<=0)return WORLD_SCENE_INVALID;
    if(!m->vertex_count&&!m->index_count)return WORLD_SCENE_OK;
    if(!vertices||!indices)return WORLD_SCENE_INVALID;
    for(unsigned a=0;a<3;a++)if(!isfinite(origin[a]))return WORLD_SCENE_INVALID;
    if(nv<m->vertex_count||ni<m->index_count)return WORLD_SCENE_CAPACITY;
    for(uint32_t i=0;i<m->vertex_count;i++)for(unsigned a=0;a<3;a++){
        float value=(f32(m->data+m->vertices+i*20+a*4)-origin[a])*scale;
        if(!isfinite(value))return WORLD_SCENE_INVALID;
    }
    WorldStreamingSceneResult result=world_streaming_scene_model_expand(m,vertices,nv,indices,ni);
    if(result!=WORLD_SCENE_OK)return result;
    for(uint32_t i=0;i<m->vertex_count;i++)for(unsigned a=0;a<3;a++)vertices[i].position[a]=(vertices[i].position[a]-origin[a])*scale;
    return WORLD_SCENE_OK;
}
bool world_streaming_scene_model_batch(const WorldStreamingSceneModel *m,uint32_t index,WorldStreamingSceneBatch *out){
    if(!m||!m->data||!out||index>=m->batch_count)return false;
    const uint8_t *p=m->data+m->batches+index*36;
    out->first_index=u32(p);out->index_count=u32(p+4);out->texture_hash=u32(p+8);out->original_descriptor=p+12;out->original_material_reference=p+28;return true;
}
WorldStreamingSceneResult world_streaming_scene_texture_open(const void *bytes,size_t size,WorldStreamingSceneTexture *out){
    if(!out)return WORLD_SCENE_INVALID;
    memset(out,0,sizeof(*out));const uint8_t *p=bytes;
    if(!p||size<128||size>64*1024*1024||memcmp(p,"WTX1",4)||u32(p+4)!=1||u32(p+8)!=size||u32(p+24)!=128||u32(p+60))return WORLD_SCENE_INVALID;
    WorldStreamingSceneTexture t={0};t.data=p;t.size=size;t.hash=u32(p+12);t.width=u32(p+16);t.height=u32(p+20);t.rgba=p+128;t.rgba_bytes=u32(p+28);
    t.quality=u32(p+32);t.alpha_test=u32(p+36);t.blend=u32(p+40);t.native_format=u32(p+44);t.source_width=u32(p+48);t.source_height=u32(p+52);t.identity=p+96;
    if(!t.width||!t.height||t.width>4096||t.height>4096||(t.width&(t.width-1))||(t.height&(t.height-1))||
       t.rgba_bytes!=t.width*t.height*4||size!=(size_t)t.rgba_bytes+128||t.source_width<t.width||t.source_height<t.height||
       (t.quality!=0&&t.quality!=256&&t.quality!=512)||(!t.quality&&(t.width!=t.source_width||t.height!=t.source_height))||
       (t.quality&&(t.width>t.quality||t.height>t.quality))||t.alpha_test>255||t.blend>255||u32(p+56)!=crc(p,size,56))return WORLD_SCENE_INVALID;
    *out=t;return WORLD_SCENE_OK;
}
WorldStreamingSceneResult world_streaming_scene_section_open(const void *bytes,size_t size,WorldStreamingSceneSection *out){
    if(!out)return WORLD_SCENE_INVALID;
    memset(out,0,sizeof(*out));const uint8_t *p=bytes;
    if(!p||size<64||size>16*1024*1024||memcmp(p,"WSI1",4)||u32(p+4)!=1||u32(p+8)!=size||u32(p+52)||u32(p+48)!=crc(p,size,48))return WORLD_SCENE_INVALID;
    WorldStreamingSceneSection s={0};s.data=p;s.size=size;s.id=u32(p+12);s.model_count=u32(p+16);s.texture_count=u32(p+20);s.instance_count=u32(p+24);
    s.models=u32(p+28);s.textures=u32(p+32);s.instances=u32(p+36);
    if(s.id>32767||s.model_count>65535||s.texture_count>65535||s.instance_count>65535||s.models!=64||s.textures!=64+s.model_count*40||
       s.instances!=s.textures+s.texture_count*40||size!=(size_t)s.instances+s.instance_count*144)return WORLD_SCENE_INVALID;
    for(uint32_t i=0;i<s.instance_count;i++){
        const uint8_t *r=p+s.instances+i*144+8;
        for(unsigned a=0;a<6;a++)if(!isfinite(f32(r+a*4)))return WORLD_SCENE_INVALID;
        for(unsigned a=0;a<3;a++)if(f32(r+a*4)>f32(r+(a+3)*4)||!isfinite(f32(r+32+a*4)))return WORLD_SCENE_INVALID;
    }
    *out=s;return WORLD_SCENE_OK;
}
static bool binding(const WorldStreamingSceneSection *s,uint32_t index,bool texture,WorldStreamingSceneBinding *out){
    if(!s||!s->data||!out||index>=(texture?s->texture_count:s->model_count))return false;
    const uint8_t *p=s->data+(texture?s->textures:s->models)+index*40;out->hash=u32(p);out->identity=p+4;return true;
}
bool world_streaming_scene_model_binding(const WorldStreamingSceneSection *s,uint32_t i,WorldStreamingSceneBinding *out){return binding(s,i,false,out);}
bool world_streaming_scene_texture_binding(const WorldStreamingSceneSection *s,uint32_t i,WorldStreamingSceneBinding *out){return binding(s,i,true,out);}
bool world_streaming_scene_instance(const WorldStreamingSceneSection *s,uint32_t index,WorldStreamingSceneInstance *out){
    if(!s||!s->data||!out||index>=s->instance_count)return false;
    const uint8_t *p=s->data+s->instances+index*144,*r=p+8,*object=p+72;
    out->source_instance_offset=u32(p);out->source_object_offset=u32(p+4);out->original_instance=r;out->original_object=object;
    for(unsigned a=0;a<6;a++)out->bounds[a]=f32(r+a*4);
    for(unsigned a=0;a<3;a++)out->translation[a]=f32(r+32+a*4);
    for(unsigned a=0;a<9;a++)out->matrix[a]=(float)s16(r+44+a*2)/8192.0f;
    for(unsigned a=0;a<4;a++){uint32_t key=u32(object+24+a*4);out->original_slots[a]=key;out->bound_slots[a]=(key==0xbe43edbb||key==0x90f70174)?0:key;}
    if(!out->bound_slots[2])out->bound_slots[2]=out->bound_slots[1];
    if(!out->bound_slots[0])out->bound_slots[0]=out->bound_slots[1];
    return true;
}

void world_streaming_scene_cache_init(WorldStreamingSceneCache *c,WorldStreamingSceneCacheEntry *e,size_t n,uint32_t normal,uint32_t linear){
    if(!c)return;
    memset(c,0,sizeof(*c));if(!e||!n||n>65535)return;
    memset(e,0,n*sizeof(*e));c->entries=e;c->capacity=n;c->normal_budget=normal;c->linear_budget=linear;c->next_generation=1;
}
WorldStreamingSceneResult world_streaming_scene_cache_acquire(WorldStreamingSceneCache *c,WorldStreamingSceneKind kind,uint32_t hash,const uint8_t identity[32],uint32_t normal,uint32_t linear,size_t *slot,uint32_t *generation){
    if(!c||!c->entries||!identity||!slot||!generation||(kind!=WORLD_SCENE_MODEL&&kind!=WORLD_SCENE_TEXTURE))return WORLD_SCENE_INVALID;
    size_t empty=c->capacity;
    for(size_t i=0;i<c->capacity;i++){
        WorldStreamingSceneCacheEntry *e=c->entries+i;
        if(!e->state){if(empty==c->capacity)empty=i;continue;}
        if(e->kind==kind&&e->hash==hash&&!memcmp(e->identity,identity,32)){
            if(e->references==UINT32_MAX)return WORLD_SCENE_STATE;
            e->references++;*slot=i;*generation=e->generation;return WORLD_SCENE_OK;
        }
    }
    if(!normal&&!linear)return WORLD_SCENE_INVALID;
    if(!c->next_generation)return WORLD_SCENE_STATE;
    if(empty==c->capacity)return WORLD_SCENE_CAPACITY;
    if(c->normal_used>c->normal_budget||c->linear_used>c->linear_budget||normal>c->normal_budget-c->normal_used||linear>c->linear_budget-c->linear_used)return WORLD_SCENE_BUDGET;
    WorldStreamingSceneCacheEntry *e=c->entries+empty;e->kind=(uint8_t)kind;e->hash=hash;memcpy(e->identity,identity,32);e->normal_bytes=normal;e->linear_bytes=linear;e->references=1;e->state=1;e->generation=c->next_generation++;
    c->normal_used+=normal;c->linear_used+=linear;*slot=empty;*generation=e->generation;return WORLD_SCENE_OK;
}
WorldStreamingSceneResult world_streaming_scene_cache_ready(WorldStreamingSceneCache *c,size_t i,uint32_t generation,void *resource){
    if(!c||!c->entries||i>=c->capacity||!resource)return WORLD_SCENE_INVALID;
    WorldStreamingSceneCacheEntry *e=c->entries+i;if(e->state!=1||e->generation!=generation)return WORLD_SCENE_STATE;e->resource=resource;e->state=2;return WORLD_SCENE_OK;
}
WorldStreamingSceneResult world_streaming_scene_cache_release(WorldStreamingSceneCache *c,size_t i){
    if(!c||!c->entries||i>=c->capacity)return WORLD_SCENE_INVALID;
    WorldStreamingSceneCacheEntry *e=c->entries+i;if(!e->state||!e->references)return WORLD_SCENE_STATE;e->references--;return WORLD_SCENE_OK;
}
WorldStreamingSceneResult world_streaming_scene_cache_pin(WorldStreamingSceneCache *c,size_t i,bool pin){
    if(!c||!c->entries||i>=c->capacity)return WORLD_SCENE_INVALID;
    WorldStreamingSceneCacheEntry *e=c->entries+i;if(!e->state||(pin&&e->pins==UINT32_MAX)||(!pin&&!e->pins))return WORLD_SCENE_STATE;
    if(pin)e->pins++;else e->pins--;return WORLD_SCENE_OK;
}
WorldStreamingSceneResult world_streaming_scene_cache_evict(WorldStreamingSceneCache *c,size_t i,void **resource){
    if(!c||!c->entries||i>=c->capacity||!resource)return WORLD_SCENE_INVALID;
    WorldStreamingSceneCacheEntry *e=c->entries+i;
    if(!e->state||e->references||e->pins)return WORLD_SCENE_STATE;
    if(e->normal_bytes>c->normal_used||e->linear_bytes>c->linear_used)return WORLD_SCENE_INVALID;
    *resource=e->resource;c->normal_used-=e->normal_bytes;c->linear_used-=e->linear_bytes;memset(e,0,sizeof(*e));return WORLD_SCENE_OK;
}
WorldStreamingSceneResult world_streaming_scene_cache_find(const WorldStreamingSceneCache *c,WorldStreamingSceneKind kind,uint32_t hash,size_t *slot){
    if(!c||!c->entries||!slot)return WORLD_SCENE_INVALID;
    size_t found=c->capacity;
    for(size_t i=0;i<c->capacity;i++){
        const WorldStreamingSceneCacheEntry *e=c->entries+i;
        if(e->state!=2||!e->references||e->kind!=kind||e->hash!=hash)continue;
        if(found!=c->capacity)return WORLD_SCENE_AMBIGUOUS;
        found=i;
    }
    if(found==c->capacity)return WORLD_SCENE_MISSING;
    *slot=found;return WORLD_SCENE_OK;
}
