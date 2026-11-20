#include "mw_native_engine_audio.h"
#include "nfs_scene.h"
#include "streamed_drive.h"
#include "mw_world_state.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static WorldCollisionRuntime collision;
static unsigned char collision_arena[16*1024*1024];
static void *load(const char *path,size_t *bytes){FILE*f=fopen(path,"rb");assert(f&&!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0&&!fseek(f,0,SEEK_SET));void*p=malloc((size_t)n);assert(p&&fread(p,1,(size_t)n,f)==(size_t)n&&!fclose(f));*bytes=(size_t)n;return p;}
typedef struct {const RoadWorld *road;unsigned queries,hits;int failed_wheel;} Ground;
static int ground(void *opaque,unsigned index,const float point[3],float *height,float normal[3])
{
    Ground *g=opaque;g->queries++;
    if((int)index==g->failed_wheel)return -1;
    float p[3]={point[0],point[1]+1,point[2]},native[3];world_collision_viewer_to_native(p,g->road->origin,native);
    WorldCollisionContact hit;int result=world_collision_runtime_ground(&collision,native,0,&hit);
    if(result==1){g->hits++;world_collision_native_to_viewer(hit.point_native,g->road->origin,p);*height=p[1];normal[0]=hit.normal_native[2];normal[1]=hit.normal_native[1];normal[2]=hit.normal_native[0];}
    return result;
}
int main(int argc,char **argv)
{
    assert(argc==3);size_t bytes;void *raw=load(argv[1],&bytes);MwVehicleRuntimeParams profile;assert(mw_vehicle_runtime_params_open(&profile,raw,bytes));free(raw);
    char path[1024];snprintf(path,sizeof(path),"%s/road.nrd",argv[2]);raw=load(path,&bytes);RoadWorld road;assert(road_decode(raw,bytes,&road));free(raw);
    snprintf(path,sizeof(path),"%s/body.nfm",argv[2]);raw=load(path,&bytes);uint32_t body_crc;memcpy(&body_crc,(unsigned char*)raw+24,4);NfsScene body;assert(nfs_scene_decode(raw,bytes,&body));free(raw);
    float ground_offset=0;for(unsigned i=0;i<body.vertex_count;i++)ground_offset=fmaxf(ground_offset,-body.vertices[i].position[1]*road.car_half_extent);
    snprintf(path,sizeof(path),"%s/wheels.nwa",argv[2]);raw=load(path,&bytes);WheelRig rig;assert(wheel_rig_decode(raw,bytes,body.batch_count,body_crc,&rig));free(raw);nfs_scene_free(&body);
    snprintf(path,sizeof(path),"%s/body.origin",argv[2]);raw=load(path,&bytes);assert(bytes==32);float center[3];memcpy(center,(unsigned char*)raw+16,12);free(raw);
    snprintf(path,sizeof(path),"%s/exploration.nws",argv[2]);raw=load(path,&bytes);MwWorldState world;assert(mw_world_state_open(&world,raw,bytes));void *state_bytes=raw;
    snprintf(path,sizeof(path),"%s/world.nwc",argv[2]);assert(!world_collision_runtime_open(&collision,path,collision_arena,sizeof(collision_arena)));assert(!world_collision_runtime_bind_groups(&collision,mw_world_state_group,&world));
    /* Host-only full-cache admission. Production keeps its existing bounded
       renderer/collision section set; adapter itself does no loading/IO. */
    uint16_t sections[WORLD_COLLISION_MAX_ASSOCIATIONS];size_t count=0;
    for(unsigned i=0;i<collision.association_count;i++){uint16_t s=collision.associations[i].section;bool seen=false;for(size_t j=0;j<count;j++)if(sections[j]==s)seen=true;if(!seen)sections[count++]=s;}
    assert(!world_collision_runtime_activate(&collision,sections,count,NULL));
    MwNativeEngineAudio audio={0};assert(mw_native_engine_audio_init(&audio,&profile,&rig,road.car_half_extent,center,0));
    /* Actual legacy BMW rig is side-first; driver repairs original axle order. */
    for(unsigned i=0;i<4;i++)assert(rig.wheels[audio.visual_wheel[i]].front==(i<2));
    DriveState car;drive_reset(&car,road.spawn[0],road.spawn[2],road.heading);float height=road.spawn[1];WheelMotion wheels={0};
    Ground g={.road=&road,.failed_wheel=-1};StreamedDriveSurface surface={&collision,&road};float minimum=INFINITY,maximum=0;unsigned samples=0;
    for(unsigned i=0;i<180;i++){
        DriveState previous=car;WheelMotion previous_wheels=wheels;float old_height=height;
        DriveInput control={.throttle=1,.handbrake=i>=100&&i<120};
        int admitted=streamed_drive_step(&surface,&car,&height,control,1.f/60);assert(admitted>=0);
        assert(wheel_motion_update(&rig,&wheels,&previous,&car));if(control.handbrake)assert(wheel_motion_lock_rear(&rig,&previous_wheels,&wheels));
        MwNativeEngineObservation observation={&previous,&car,&previous_wheels,&wheels,old_height,height,ground_offset,control,1.f/60,false};
        MwEngineAudioAdvance result=mw_native_engine_audio_advance(&audio,&observation,ground,&g);assert(result.status==MW_ENGINE_AUDIO_OK&&result.ticks==1);
        MwEngineAudioSample sample;assert(mw_native_engine_audio_sample(&audio,&sample)&&isfinite(sample.rpm));minimum=fminf(minimum,sample.rpm);maximum=fmaxf(maximum,sample.rpm);samples++;
    }
    assert(g.queries==720&&g.hits>600&&maximum>minimum+100);
    DriveState previous=car;WheelMotion previous_wheels=wheels;MwNativeEngineObservation observation={&previous,&car,&previous_wheels,&wheels,height,height,ground_offset,{.throttle=1},1.f/60,false};
    MwPhysicsTransmissionEngineStepState saved=audio.source.engine;uint64_t ticks=audio.source.ticks;float clock=audio.source.source_clock;g.failed_wheel=2;
    MwEngineAudioAdvance result=mw_native_engine_audio_advance(&audio,&observation,ground,&g);MwEngineAudioSample sample;
    assert(result.status==MW_ENGINE_AUDIO_SOURCE_REJECTED&&!result.ticks&&audio.source.ticks==ticks&&audio.source.source_clock==clock&&!memcmp(&saved,&audio.source.engine,sizeof(saved))&&!mw_native_engine_audio_sample(&audio,&sample));
    g.failed_wheel=-1;assert(mw_native_engine_audio_advance(&audio,&observation,ground,&g).status==MW_ENGINE_AUDIO_OK&&mw_native_engine_audio_sample(&audio,&sample));
    /* A stopped reverse request uses real engine gear-commit, then sourceRPM. */
    observation.control.throttle=-1;assert(mw_native_engine_audio_advance(&audio,&observation,ground,&g).status==MW_ENGINE_AUDIO_OK&&mw_native_engine_audio_sample(&audio,&sample)&&sample.gear_slot==0);
    mw_native_engine_audio_stop(&audio);assert(!audio.initialized&&!mw_native_engine_audio_sample(&audio,&sample));
    printf("Native engine audio: %uaccepted source60Hz ticks, %uactual NWC hits/%uqueries, RPM%.2f..%.2f, real legacy rig mapping, handbrake, missingsection refusal and reverse policy passed\n",samples,g.hits,g.queries,minimum,maximum);
    world_collision_runtime_close(&collision);free(state_bytes);wheel_rig_free(&rig);road_free(&road);return 0;
}
