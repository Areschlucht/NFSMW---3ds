#include "streamed_world.h"
#include "streamed_world_pack.h"
#include "mw_world_state.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
typedef struct {MwWorldState state;bool hide,fail;} State;
static bool flags(void *ctx,uint32_t offset,uint32_t source,uint32_t *effective){
 State *s=ctx;if(s->fail||!mw_world_state_instance(&s->state,offset,source,effective))return false;
 if(s->hide)*effective|=16;
 return true;
}
int main(int argc,char **argv){
 assert(argc==6);FILE *f=fopen(argv[5],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);rewind(f);assert(n>0);
 void *raw=malloc((size_t)n);assert(raw&&fread(raw,1,(size_t)n,f)==(size_t)n);fclose(f);State state={0};assert(mw_world_state_open(&state.state,raw,(size_t)n));
 MwScenePack pack={0};assert(mw_scene_pack_open(&pack,argv[1],2*1024*1024)==MW_SCENE_PACK_OK);
 StreamedWorldConfig cfg={.read_asset=streamed_world_pack_read,.read_context=&pack,.metadata_path=argv[2],.normal_bytes=12*1024*1024,.linear_bytes=20*1024*1024,.scratch_bytes=4*1024*1024,.cache_entries=2048,.object_capacity=4096,.run_capacity=32768,.render_scale=.001f,.lod_mode=STREAMED_WORLD_SOURCE_LOD_COMPONENTS,.alpha_reference=40,.boot_global_provider_bank=true,.original_missing_texture_hash=0x66994f4a,.instance_state=flags,.instance_state_context=&state};
 StreamedWorld *world=NULL;assert(!streamed_world_create(&cfg,&world));
 StreamedWorldView view={.camera_viewer={360,180,-2410},.forward_viewer={0,0,1},.up_viewer={0,1,0},.vertical_fov_radians=1,.aspect=400.f/240,.near_world=.15f,.far_world=350,.original_fov_turn=0x3000,.original_context_flags=16};
 assert(!streamed_world_prepare(world,360,2410,&view));StreamedWorldStats first,next;streamed_world_stats(world,&first);assert(first.visible_instances&&first.linear_used);
 state.hide=true;assert(!streamed_world_prepare(world,360,2410,&view));streamed_world_stats(world,&next);assert(next.visible_instances==first.visible_instances);
 streamed_world_invalidate_instances(world);assert(!streamed_world_prepare(world,360,2410,&view));streamed_world_stats(world,&next);assert(!next.visible_instances&&!next.draw_runs);
 state.hide=false;state.fail=true;streamed_world_invalidate_instances(world);assert(streamed_world_prepare(world,360,2410,&view)==STREAMED_WORLD_FORMAT);streamed_world_stats(world,&next);assert(!next.visible_instances);
 state.fail=false;assert(!streamed_world_prepare(world,360,2410,&view));streamed_world_stats(world,&next);assert(next.visible_instances==first.visible_instances&&next.draw_runs==first.draw_runs);
 streamed_world_suspend(world);streamed_world_stats(world,&next);assert(!next.visible_instances&&!next.draw_runs&&!next.linear_used);
 assert(!streamed_world_prepare(world,360,2410,&view));streamed_world_stats(world,&next);assert(next.visible_instances==first.visible_instances&&next.draw_runs==first.draw_runs);
 streamed_world_destroy(world);assert(!mock_linear_used);mw_scene_pack_close(&pack);free(raw);
 puts("Same-camera state invalidation, failed-stage rollback, world GPU eviction and exact workload restoration passed.");return 0;
}
