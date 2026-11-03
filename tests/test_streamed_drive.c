#include "streamed_drive.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
static WorldCollisionRuntime collision;
static unsigned char arena[4096];
int main(int argc,char **argv)
{
    assert(argc==2);
    assert(!world_collision_runtime_open(&collision,argv[1],arena,sizeof(arena)));
    uint16_t section=141;
    assert(!world_collision_runtime_activate(&collision,&section,1,NULL));
    RoadWorld road={.origin={203,4,101},.car_half_extent=2};
    StreamedDriveSurface surface={&collision,&road};float height,normal[3];
    assert(streamed_drive_surface(&surface,.2f,.2f,0,&height,normal));
    assert(fabsf(height)<.00001f && fabsf(normal[1]-1)<.00001f);
    assert(!streamed_drive_surface(&surface,.2f,.2f,4,&height,normal));
    DriveState car;drive_reset(&car,.2f,.2f,0);height=0;
    assert(streamed_drive_step(&surface,&car,&height,(DriveInput){0},1.f/60)==1);
    bool stopped=false;
    for(unsigned i=0;i<240;i++) {
        int result=streamed_drive_step(&surface,&car,&height,(DriveInput){.throttle=1},1.f/60);
        assert(result>=0 && isfinite(car.x) && isfinite(car.z) && height==0);
        if(!result){stopped=true;break;}
    }
    assert(stopped && car.speed==0 && car.z>.2f);
    /* Cross the synthetic original wall at nativeZ200. The centre sweep must
       stop before accepting the candidate pose, independently of floor hits. */
    drive_reset(&car,-3.005f,0,1.57079632679f);car.speed=10;height=0;
    float before=car.x;
    assert(streamed_drive_step(&surface,&car,&height,(DriveInput){0},.01f)==0);
    assert(car.x==before && car.speed==0);
    collision.ready=0;
    assert(streamed_drive_step(&surface,&car,&height,(DriveInput){0},.01f)<0);
    world_collision_runtime_close(&collision);
    puts("Streamed driving: source ground, finite motion, unsupported edge and wall sweep PASS");
}
