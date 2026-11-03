#include "streamed_world.h"
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { const char *root; unsigned fault, faults; } Reader;
static StreamedWorldResult read_asset(void *context,StreamedWorldAssetKind kind,
    uint32_t id,const uint8_t identity[32],void *data,size_t capacity,size_t *bytes)
{
    Reader *r=context;char path[1024],digest[65];
    if(kind==STREAMED_WORLD_TEXTURE) {
        assert(identity);
        for(unsigned i=0;i<32;i++) snprintf(digest+i*2,3,"%02x",identity[i]);
        snprintf(path,sizeof(path),"%s/textures/%08x-%s.wtx",r->root,id,digest);
    }
    if(kind==STREAMED_WORLD_MODEL) snprintf(path,sizeof(path),"%s/models/%08x.wsm",r->root,id);
    if(kind==STREAMED_WORLD_SECTION) snprintf(path,sizeof(path),"%s/sections/%u.wsi",r->root,id);
    FILE *f=fopen(path,"rb");
    if(!f) return errno==ENOENT?STREAMED_WORLD_MISSING:STREAMED_WORLD_IO;
    assert(!fseek(f,0,SEEK_END));long length=ftell(f);assert(length>0);
    *bytes=(size_t)length;
    if(!data) { fclose(f);return STREAMED_WORLD_OK; }
    assert(capacity>=*bytes);rewind(f);
    assert(fread(data,1,*bytes,f)==*bytes);fclose(f);
    if(kind==STREAMED_WORLD_TEXTURE && id!=0x66994f4a && r->fault) {
        r->faults++;
        if(r->fault==1) return STREAMED_WORLD_IO;
        if(r->fault==2) return STREAMED_WORLD_MISSING;
        ((unsigned char *)data)[*bytes-1]^=1;
    }
    return STREAMED_WORLD_OK;
}
int main(int argc,char **argv)
{
    assert(argc==3);Reader reader={.root=argv[1]};
    StreamedWorldConfig config={.metadata_path=argv[2],.read_asset=read_asset,
        .read_context=&reader,.normal_bytes=12*1024*1024,.linear_bytes=20*1024*1024,
        .scratch_bytes=4*1024*1024,.cache_entries=2048,.object_capacity=4096,
        .run_capacity=32768,.render_scale=.001f,.lod_mode=STREAMED_WORLD_REFERENCE_SLOT0,
        .alpha_reference=40,.boot_global_provider_bank=true,
        .original_missing_texture_hash=0x66994f4a};
    StreamedWorldView view={.camera_viewer={360,180,-2410},.forward_viewer={0,0,-1},
        .up_viewer={0,1,0},.vertical_fov_radians=1,.aspect=400.f/240,
        .near_world=.15f,.far_world=350,.original_fov_turn=0x3000};
    StreamedWorld *world=NULL;assert(streamed_world_create(&config,&world)==STREAMED_WORLD_OK);
    StreamedWorldResult result=streamed_world_prepare(world,360,2410,&view);
    StreamedWorldStats first;streamed_world_stats(world,&first);
    if(result) fprintf(stderr,"prepare %d: %s\n",result,first.detail);
    assert(result==STREAMED_WORLD_OK && first.boot_provider_banks==1);
    /* This view originally failed on the real TireShop texture-reference miss. */
    assert(first.texture_fallback_bindings>0 && first.visible_instances>0);
    for(unsigned i=0;i<5;i++) assert(streamed_world_prepare(world,360,2410,&view)==STREAMED_WORLD_OK);
    StreamedWorldStats steady;streamed_world_stats(world,&steady);
    assert(steady.asset_reads==first.asset_reads && steady.asset_queries==first.asset_queries);
    assert(steady.arena_allocations==first.arena_allocations);
    printf("boot bank: %u objects, %u runs, %u triangles, %u original fallback bindings\n",
        first.visible_instances,first.draw_runs,first.triangles,first.texture_fallback_bindings);
    streamed_world_destroy(world);assert(mock_linear_used==0);
    config.lod_mode=STREAMED_WORLD_SOURCE_LOD_COMPONENTS;
    assert(streamed_world_create(&config,&world)==STREAMED_WORLD_OK);
    assert(streamed_world_prepare(world,360,2410,&view)==STREAMED_WORLD_OK);
    streamed_world_stats(world,&steady);
    uint16_t sections[147];size_t count=0;
    assert(streamed_world_sections(world,sections,147,&count)==STREAMED_WORLD_OK);
    assert(count==steady.source_sections && count>0);
    for(size_t i=0;i<count;i++)assert(sections[i]!=0);
    uint16_t guard=0xbeef;size_t required=0;
    assert(streamed_world_sections(world,&guard,0,&required)==STREAMED_WORLD_CAPACITY);
    assert(required==count && guard==0xbeef);
    printf("source LOD: %u objects, %u runs, %u triangles, %u source sections\n",
        steady.visible_instances,steady.draw_runs,steady.triangles,steady.source_sections);
    streamed_world_destroy(world);assert(mock_linear_used==0);
    config.lod_mode=STREAMED_WORLD_REFERENCE_SLOT0;
    /* Declared real providers must fail on IO, missing files and bad CRC;
       DEFAULTALPHA is only for original registry misses, never broken assets. */
    for(unsigned fault=1;fault<=3;fault++) {
        reader.fault=fault;reader.faults=0;
        assert(streamed_world_create(&config,&world)==STREAMED_WORLD_OK);
        result=streamed_world_prepare(world,360,2410,&view);
        assert(reader.faults==1);
        assert(result==(fault==1?STREAMED_WORLD_IO:fault==2?STREAMED_WORLD_MISSING:STREAMED_WORLD_FORMAT));
        streamed_world_destroy(world);assert(mock_linear_used==0);
    }
    puts("declared-provider IO/missing/CRC failures are not masked: PASS");
    return 0;
}
