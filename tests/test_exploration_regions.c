#include "streamed_world.h"
#include "streamed_world_pack.h"
#include "world_collision_runtime.h"
#include "mw_world_state.h"
#include "mw_free_roam.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
static WorldCollisionRuntime collision;
static unsigned char arena[1024*1024];
static void *load(const char *path,size_t *n){FILE *f=fopen(path,"rb");assert(f);assert(!fseek(f,0,SEEK_END));long bytes=ftell(f);rewind(f);assert(bytes>0);void *p=malloc((size_t)bytes);assert(p&&fread(p,1,(size_t)bytes,f)==(size_t)bytes);fclose(f);*n=(size_t)bytes;return p;}
int main(int argc,char **argv){
 assert(argc==6);size_t n;void *state_data=load(argv[4],&n);MwWorldState state;assert(mw_world_state_open(&state,state_data,n));void *locations=load(argv[5],&n);MwFreeRoam places;assert(mw_free_roam_open(&places,locations,n));
 assert(!world_collision_runtime_open(&collision,argv[3],arena,sizeof(arena)));assert(mw_world_state_source_matches(&state,collision.source_sha256));assert(!world_collision_runtime_bind_groups(&collision,mw_world_state_group,&state));
 MwScenePack pack={0};assert(mw_scene_pack_open(&pack,argv[1],2*1024*1024)==MW_SCENE_PACK_OK);
 StreamedWorldConfig cfg={.read_asset=streamed_world_pack_read,.read_context=&pack,.metadata_path=argv[2],.normal_bytes=12*1024*1024,.linear_bytes=20*1024*1024,.scratch_bytes=4*1024*1024,.cache_entries=2048,.object_capacity=4096,.run_capacity=32768,.render_scale=.1f,.lod_mode=STREAMED_WORLD_SOURCE_LOD_COMPONENTS,.alpha_reference=40,.boot_global_provider_bank=true,.original_missing_texture_hash=0x66994f4a,.instance_state=mw_world_state_instance,.instance_state_context=&state};
 StreamedWorld *world;assert(streamed_world_create(&cfg,&world)==STREAMED_WORLD_OK);unsigned tested=0;
 for(uint32_t i=0;i<places.count;i++){
  MwDestination d;assert(mw_free_roam_get(&places,i,&d));if(d.kind!=MW_DEST_SAFEHOUSE)continue;
  float *p=d.respawn_position;StreamedWorldView v={.camera_viewer={p[0],p[2]+8,-p[1]+12},.forward_viewer={0,-.37139068f,-.92847669f},.up_viewer={0,1,0},.vertical_fov_radians=1,.aspect=400.f/240,.near_world=.15f,.far_world=700,.original_fov_turn=10430,.original_context_flags=state.context};
  StreamedWorldResult result=streamed_world_prepare(world,p[0],p[1],&v);StreamedWorldStats stats;streamed_world_stats(world,&stats);if(result)fprintf(stderr,"regiontest %08x load%d %s\n",d.key,result,stats.detail);assert(!result);
  uint16_t ids[147];size_t count;assert(!streamed_world_sections(world,ids,147,&count));assert(!world_collision_runtime_activate(&collision,ids,count,NULL));
  float point[]={-p[1],p[2]+2,p[0]};WorldCollisionContact ground;assert(world_collision_runtime_ground(&collision,point,0,&ground)==1);
  printf("safehouse %08x: source %.2f %.2f %.2f; region%u; %u objects/%u runs; groundgroup%u\n",d.key,(double)p[0],(double)p[1],(double)p[2],stats.region,stats.visible_instances,stats.draw_runs,ground.group_id);tested++;
 }
 assert(tested==4);streamed_world_destroy(world);assert(!mock_linear_used);world_collision_runtime_close(&collision);mw_scene_pack_close(&pack);free(state_data);free(locations);return 0;
}
