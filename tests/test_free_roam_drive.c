/* Real-source renderer/collision/controller bridge. Requires private converted
   scene, WST metadata, NWC collision and NRD spawn assets, in that order. */
#include "streamed_world.h"
#include "streamed_drive.h"
#include "chase_camera.h"
#include "mw_world_state.h"
#include "streamed_world_pack.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
static WorldCollisionRuntime collision;
static unsigned char collision_arena[1024*1024];
static void *read_file(const char *name,size_t *bytes)
{
    FILE *f=fopen(name,"rb");assert(f);assert(!fseek(f,0,SEEK_END));
    long n=ftell(f);assert(n>0&&n<8*1024*1024);rewind(f);
    void *p=malloc((size_t)n);assert(p&&fread(p,1,(size_t)n,f)==(size_t)n);fclose(f);*bytes=(size_t)n;return p;
}
int main(int argc,char **argv)
{
    assert(argc==6);size_t bytes;void *raw=read_file(argv[4],&bytes);RoadWorld road;
    assert(road_decode(raw,bytes,&road));free(raw);
    assert(!world_collision_runtime_open(&collision,argv[3],collision_arena,sizeof(collision_arena)));
    size_t state_bytes;void *state_raw=read_file(argv[5],&state_bytes);MwWorldState state;
    assert(mw_world_state_open(&state,state_raw,state_bytes)&&state.bin==1);
    assert(mw_world_state_source_matches(&state,collision.source_sha256));
    assert(!world_collision_runtime_bind_groups(&collision,mw_world_state_group,&state));
    StreamedWorldConfig config={.asset_root=argv[1],.metadata_path=argv[2],
        .normal_bytes=12*1024*1024,.linear_bytes=20*1024*1024,.scratch_bytes=4*1024*1024,
        .cache_entries=2048,.object_capacity=4096,.run_capacity=32768,.render_scale=road.scale,
        .lod_mode=STREAMED_WORLD_SOURCE_LOD_COMPONENTS,.alpha_reference=40,
        .boot_global_provider_bank=true,.original_missing_texture_hash=0x66994f4a,
        .instance_state=mw_world_state_instance,.instance_state_context=&state};
    MwScenePack pack={0};
    {assert(mw_scene_pack_open(&pack,argv[1],2*1024*1024)==MW_SCENE_PACK_OK);config.read_asset=streamed_world_pack_read;config.read_context=&pack;config.asset_root=NULL;}
    StreamedWorld *world=NULL;assert(streamed_world_create(&config,&world)==STREAMED_WORLD_OK);
    DriveState car;drive_reset(&car,road.spawn[0],road.spawn[2],road.heading);
    float height=road.spawn[1];ChaseCamera camera;assert(chase_reset(&camera,&car,height));
    StreamedDriveSurface surface={&collision,&road};float distance=0;unsigned blocked=0,max_runs=0,max_tris=0;
    for(unsigned frame=0;frame<600;frame++) {
        StreamedWorldView view={.aspect=400.f/240,.near_world=.15f,.far_world=700,.up_viewer={0,1,0},
            .vertical_fov_radians=camera.fov*.01745329252f,.original_fov_turn=(uint16_t)lroundf(camera.fov*(65536.f/360)),.original_context_flags=state.context};
        float length=0;
        for(unsigned a=0;a<3;a++){view.camera_viewer[a]=(double)camera.eye[a]+road.origin[a];view.forward_viewer[a]=camera.target[a]-camera.eye[a];length+=view.forward_viewer[a]*view.forward_viewer[a];}
        length=sqrtf(length);for(unsigned a=0;a<3;a++)view.forward_viewer[a]/=length;
        StreamedWorldResult result=streamed_world_prepare(world,car.x+road.origin[0],-(car.z+road.origin[2]),&view);
        StreamedWorldStats stats;streamed_world_stats(world,&stats);
        if(result)fprintf(stderr,"frame%u load%d %s\n",frame,result,stats.detail);
        assert(result==STREAMED_WORLD_OK);
        uint16_t ids[147];size_t count;
        assert(streamed_world_sections(world,ids,147,&count)==STREAMED_WORLD_OK);
        assert(!world_collision_runtime_activate(&collision,ids,count,NULL));
        shaderProgram_s program={0};C3D_Mtx projection;Mtx_Identity(&projection);
        streamed_world_draw(world,&program,0,1,&projection);
        if(stats.draw_runs>max_runs)max_runs=stats.draw_runs;
        if(stats.triangles>max_tris)max_tris=stats.triangles;
        float x=car.x,z=car.z;
        int step=streamed_drive_step(&surface,&car,&height,(DriveInput){.throttle=1,.steering=frame>350?.15f:0,.handbrake=frame>350&&frame<390},1.f/60);
        assert(step>=0);blocked+=step==0;distance+=hypotf(car.x-x,car.z-z);
        assert(isfinite(height)&&isfinite(car.speed));assert(chase_step(&camera,&car,height,1.f/60));
    }
    assert(distance>80);
    printf("600 integrated frames: %.2fm travelled, %u blocked frames, max%u runs/%u triangles\n",(double)distance,blocked,max_runs,max_tris);
    streamed_world_destroy(world);assert(mock_linear_used==0);
    world_collision_runtime_close(&collision);mw_scene_pack_close(&pack);road_free(&road);free(state_raw);return 0;
}
