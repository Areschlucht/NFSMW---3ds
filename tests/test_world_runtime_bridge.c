/* Cross-specialist real-source integration check, not a whole-game collision test.
 * Usage: WST1-metadata NWC1-collision NRD1-road. */
#include "world_streaming.h"
#include "world_collision_runtime.h"
#include "road_contact.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static WorldCollisionRuntime collision;
static unsigned char arena[1024*1024];
static void *read_all(const char *path,size_t *size)
{
    FILE *f=fopen(path,"rb");assert(f);assert(!fseek(f,0,SEEK_END));
    long n=ftell(f);assert(n>0 && n<8*1024*1024);rewind(f);
    void *p=malloc((size_t)n);assert(p);assert(fread(p,1,(size_t)n,f)==(size_t)n);
    assert(!fclose(f));*size=(size_t)n;return p;
}
int main(int argc,char **argv)
{
    assert(argc==4);size_t bytes;void *metadata=read_all(argv[1],&bytes);
    WorldStreamingDatabase db;assert(world_streaming_open(metadata,bytes,&db)==WORLD_STREAMING_OK);
    WorldStreamingSelector selector;world_streaming_selector_init(&db,&selector);
    assert(world_collision_runtime_open(&collision,argv[2],arena,sizeof arena)==0);
    assert(!memcmp(collision.source_sha256,(unsigned char *)metadata+64,32));
    void *raw=read_all(argv[3],&bytes);RoadWorld road;
    assert(road_decode(raw,bytes,&road));free(raw);
    unsigned hits=0,misses=0,outside=0,within10cm=0,queries=0;
    size_t max_cache=0,max_requested=0;float max_error=0;
    for (unsigned i=0;i<road.count;++i) {
        float local[3]={0};
        for (unsigned a=0;a<3;++a) for (unsigned v=0;v<3;++v)
            local[a]+=road.triangles[i].p[v][a]/3;
        float native[3];world_collision_viewer_to_native(local,road.origin,native);
        /* Original render-source XY differs from original collision-native XYZ. */
        uint16_t dependency;WorldStreamingResult selected=world_streaming_select(
            &db,&selector,native[2],-native[0],&dependency);
        if (selected==WORLD_STREAMING_NEAREST_REQUIRED) { ++outside;continue; }
        assert(selected==WORLD_STREAMING_OK);
        uint16_t ids[147];size_t count=0;
        assert(world_streaming_plan(&db,&dependency,1,ids,147,&count)==WORLD_STREAMING_OK);
        WorldCollisionAdmission admission;
        assert(world_collision_runtime_admit(&collision,ids,count,&admission)==0);
        assert(world_collision_runtime_activate(&collision,ids,count,&admission)==0);
        assert(collision.ready && collision.arena_used==admission.required_bytes);
        if (collision.arena_used>max_cache) max_cache=collision.arena_used;
        if (count>max_requested) max_requested=count;
        float point[3]={native[0],native[1]+.25f,native[2]};WorldCollisionContact hit;
        int result=world_collision_runtime_ground(&collision,point,0,&hit);assert(result>=0);
        ++queries;
        if (result) {
            ++hits;float error=fabsf(native[1]-hit.point_native[1]);
            if (error<.10f) ++within10cm;
            if (error>max_error) max_error=error;
            assert(hit.section_id && hit.kind==1);
            float viewer[3];world_collision_native_to_viewer(hit.point_native,road.origin,viewer);
            assert(fabsf(viewer[1]-(hit.point_native[1]-road.origin[1]))<.0001f);
        } else ++misses;
    }
    printf("{\"road_triangles\":%u,\"queries\":%u,\"ground_hits\":%u,\"misses\":%u,"
           "\"outside_region\":%u,\"within_10cm\":%u,\"max_height_error_m\":%.9g,"
           "\"max_cache_bytes\":%zu,\"max_source_sections\":%zu}\n",
           road.count,queries,hits,misses,outside,within10cm,(double)max_error,max_cache,max_requested);
    assert(queries>0 && hits>0);road_free(&road);world_collision_runtime_close(&collision);free(metadata);
    return 0;
}
