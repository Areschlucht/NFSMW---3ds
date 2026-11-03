#include "world_streaming_scene.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void cache_tests(void){
    WorldStreamingSceneCache c;WorldStreamingSceneCacheEntry entries[512];
    world_streaming_scene_cache_init(&c,entries,512,51200,512000);
    uint8_t a[32]={1},b[32]={2};size_t first,again,second;uint32_t ga,gb,gagain;
    assert(world_streaming_scene_cache_acquire(&c,WORLD_SCENE_TEXTURE,42,a,100,1000,&first,&ga)==WORLD_SCENE_OK);
    assert(world_streaming_scene_cache_acquire(&c,WORLD_SCENE_TEXTURE,42,a,0,0,&again,&gagain)==WORLD_SCENE_OK&&again==first&&ga==gagain);
    assert(c.normal_used==100&&c.linear_used==1000&&entries[first].references==2);
    assert(world_streaming_scene_cache_ready(&c,first,ga,(void *)1)==WORLD_SCENE_OK);
    assert(world_streaming_scene_cache_acquire(&c,WORLD_SCENE_TEXTURE,42,b,100,1000,&second,&gb)==WORLD_SCENE_OK);
    assert(world_streaming_scene_cache_ready(&c,second,gb,(void *)2)==WORLD_SCENE_OK);
    assert(world_streaming_scene_cache_find(&c,WORLD_SCENE_TEXTURE,42,&again)==WORLD_SCENE_AMBIGUOUS);
    assert(world_streaming_scene_cache_pin(&c,first,true)==WORLD_SCENE_OK);
    assert(world_streaming_scene_cache_release(&c,first)==WORLD_SCENE_OK);
    assert(world_streaming_scene_cache_release(&c,first)==WORLD_SCENE_OK);
    void *resource=NULL;
    assert(world_streaming_scene_cache_evict(&c,first,&resource)==WORLD_SCENE_STATE);
    assert(world_streaming_scene_cache_pin(&c,first,false)==WORLD_SCENE_OK);
    assert(world_streaming_scene_cache_evict(&c,first,&resource)==WORLD_SCENE_OK&&resource==(void *)1);
    uint32_t newer;
    assert(world_streaming_scene_cache_acquire(&c,WORLD_SCENE_MODEL,7,a,100,1000,&again,&newer)==WORLD_SCENE_OK&&again==first&&newer!=ga);
    assert(world_streaming_scene_cache_ready(&c,again,ga,(void *)3)==WORLD_SCENE_STATE);
    assert(world_streaming_scene_cache_ready(&c,again,newer,(void *)3)==WORLD_SCENE_OK);
    assert(world_streaming_scene_cache_acquire(&c,WORLD_SCENE_MODEL,8,a,60000,1,&first,&ga)==WORLD_SCENE_BUDGET);
    /* Explicit512-slot support and no implicit eviction. */
    world_streaming_scene_cache_init(&c,entries,512,51200,512000);
    for(unsigned i=0;i<512;i++){
        a[0]=(uint8_t)i;a[1]=(uint8_t)(i>>8);
        assert(world_streaming_scene_cache_acquire(&c,WORLD_SCENE_TEXTURE,i,a,100,1000,&first,&ga)==WORLD_SCENE_OK);
    }
    assert(c.normal_used==51200&&c.linear_used==512000);
    assert(world_streaming_scene_cache_acquire(&c,WORLD_SCENE_TEXTURE,513,b,1,1,&first,&ga)==WORLD_SCENE_CAPACITY);
}
int main(int argc,char **argv){
    cache_tests();if(argc==1)return 0;assert(argc==2);
    FILE *list=fopen(argv[1],"r");assert(list);char line[4096];unsigned models=0,textures=0,sections=0;unsigned long long vertices=0,indices=0,instances=0;
    while(fgets(line,sizeof(line),list)){
        char type=line[0];char *path=line+2;path[strcspn(path,"\r\n")]=0;
        FILE *file=fopen(path,"rb");assert(file);assert(!fseek(file,0,SEEK_END));long bytes=ftell(file);assert(bytes>0&&bytes<64*1024*1024);rewind(file);
        unsigned char *data=malloc((size_t)bytes);assert(data);assert(fread(data,1,(size_t)bytes,file)==(size_t)bytes);fclose(file);
        if(type=='M'){
            WorldStreamingSceneModel m;assert(world_streaming_scene_model_open(data,(size_t)bytes,&m)==WORLD_SCENE_OK);
            if(!m.index_count){
                assert(!m.vertex_count&&!m.batch_count&&data[60]==1&&bytes==416);
                assert(world_streaming_scene_model_expand(&m,NULL,0,NULL,0)==WORLD_SCENE_OK);
                models++;data[12]^=1;assert(world_streaming_scene_model_open(data,(size_t)bytes,&m)==WORLD_SCENE_INVALID&&!m.data);free(data);continue;
            }
            WorldVertex *v=malloc(m.vertex_count*sizeof(*v));uint16_t *ix=malloc(m.index_count*sizeof(*ix));assert(v&&ix);
            assert(world_streaming_scene_model_expand(&m,v,m.vertex_count,ix,m.index_count)==WORLD_SCENE_OK);
            float origin[3]={m.bounds[0],m.bounds[1],m.bounds[2]},scale=.25f;
            WorldVertex reference=v[0];
            assert(world_streaming_scene_model_expand_rebased(&m,origin,scale,v,m.vertex_count,ix,m.index_count)==WORLD_SCENE_OK);
            for(unsigned a=0;a<3;a++)assert(v[0].position[a]==(reference.position[a]-origin[a])*scale);
            assert(!memcmp(v[0].uv,reference.uv,sizeof(reference.uv))&&!memcmp(v[0].color,reference.color,sizeof(reference.color)));
            WorldVertex untouched;memset(&untouched,0x5a,sizeof(untouched));WorldVertex before=untouched;
            assert(world_streaming_scene_model_expand(&m,&untouched,0,ix,m.index_count)==WORLD_SCENE_CAPACITY&&!memcmp(&untouched,&before,sizeof(before)));
            WorldStreamingSceneBatch batch;for(uint32_t i=0;i<m.batch_count;i++)assert(world_streaming_scene_model_batch(&m,i,&batch));
            vertices+=m.vertex_count;indices+=m.index_count;models++;free(v);free(ix);
        }else if(type=='T'){
            WorldStreamingSceneTexture t;assert(world_streaming_scene_texture_open(data,(size_t)bytes,&t)==WORLD_SCENE_OK);textures++;
        }else if(type=='S'){
            WorldStreamingSceneSection s;assert(world_streaming_scene_section_open(data,(size_t)bytes,&s)==WORLD_SCENE_OK);
            WorldStreamingSceneInstance instance;for(uint32_t i=0;i<s.instance_count;i++)assert(world_streaming_scene_instance(&s,i,&instance));
            instances+=s.instance_count;sections++;
        }else assert(0);
        /* Both source payload AND material/header corruption must fail CRC. */
        data[12]^=1;
        if(type=='M'){WorldStreamingSceneModel m;assert(world_streaming_scene_model_open(data,(size_t)bytes,&m)==WORLD_SCENE_INVALID&&!m.data);}
        if(type=='T'){WorldStreamingSceneTexture t;assert(world_streaming_scene_texture_open(data,(size_t)bytes,&t)==WORLD_SCENE_INVALID&&!t.data);}
        if(type=='S'){WorldStreamingSceneSection s;assert(world_streaming_scene_section_open(data,(size_t)bytes,&s)==WORLD_SCENE_INVALID&&!s.data);}
        free(data);
    }
    fclose(list);
    printf("{\"models\":%u,\"textures\":%u,\"sections\":%u,\"vertices\":%llu,\"indices\":%llu,\"instances\":%llu}\n",models,textures,sections,vertices,indices,instances);
    return 0;
}
