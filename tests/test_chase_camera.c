#include "chase_camera.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    DriveState car={0};ChaseCamera camera;
    assert(chase_reset(&camera,&car,0));ChaseCamera initial=camera;
    for (unsigned i=0;i<120;++i) assert(chase_step(&camera,&car,0,1.0f/60));
    assert(memcmp(camera.eye,initial.eye,sizeof(camera.eye))==0);
    car.heading=1;assert(chase_step(&camera,&car,0,1.0f/60));
    assert(camera.heading>0 && camera.heading<car.heading);assert(fabsf(camera.eye[0])<1);
    for (unsigned i=0;i<600;++i) assert(chase_step(&camera,&car,0,1.0f/60));
    assert(fabsf(camera.heading-1)<.0001f);
    car.heading=3.13f;assert(chase_reset(&camera,&car,0));car.heading=-3.13f;
    assert(chase_step(&camera,&car,0,.01f));assert(fabsf(camera.heading)>3);
    car=(DriveState){0};assert(chase_reset(&camera,&car,0));
    ChaseCamera a=camera,b=camera;car.x=4;car.speed=30;
    for (unsigned i=0;i<60;++i) assert(chase_step(&a,&car,3,1.0f/30));
    for (unsigned i=0;i<240;++i) assert(chase_step(&b,&car,3,1.0f/120));
    for (unsigned i=0;i<3;++i) { assert(fabsf(a.eye[i]-b.eye[i])<.001f);assert(fabsf(a.target[i]-b.target[i])<.001f); }
    /* The look target must remain ahead at high speed, rather than trailing
       behind the car because of target-spring delay. */
    car=(DriveState){.speed=65};assert(chase_reset(&camera,&car,0));
    for (unsigned i=0;i<600;++i) { car.z+=car.speed/120;assert(chase_step(&camera,&car,0,1.0f/120)); }
    assert(camera.target[2]>car.z+3);assert(car.z-camera.eye[2]>6 && car.z-camera.eye[2]<16);
    assert(chase_reset(&camera,&car,3));initial=camera;
    assert(!chase_step(&camera,&car,3,NAN));assert(!chase_step(&camera,&car,3,.2f));
    assert(!chase_step(&camera,NULL,3,.01f));assert(memcmp(&camera,&initial,sizeof(camera))==0);
    puts("Camera checks passed: stationary, yaw lag/wrap, settling, reset, 30/120 Hz and invalid input.");return 0;
}
