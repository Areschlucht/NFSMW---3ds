#include "driving_controller.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
static void duration(DriveState *car,DriveInput input,float seconds,float fps)
{
    unsigned frames=(unsigned)(seconds*fps);
    for (unsigned i=0;i<frames;++i) assert(drive_step(car,input,1/fps));
    float remainder=seconds-frames/fps;
    if (remainder>1e-6f) assert(drive_step(car,input,remainder));
}

int main(void)
{
    DriveState car;drive_reset(&car,0,0,0);
    for (unsigned i=0;i<120;++i) assert(drive_step(&car,(DriveInput){0},1.0f/120));
    assert(car.speed==0 && car.x==0 && car.z==0);
    for (unsigned i=0;i<120;++i) assert(drive_step(&car,(DriveInput){.throttle=1,.brake=1},1.0f/120));
    assert(car.speed==0 && car.x==0 && car.z==0);
    for (unsigned i=0;i<600;++i) assert(drive_step(&car,(DriveInput){.throttle=1},1.0f/120));
    assert(car.speed>20 && car.speed<=65 && car.z>50 && fabsf(car.x)<1e-6);
    for (unsigned i=0;i<360;++i) assert(drive_step(&car,(DriveInput){.brake=1},1.0f/120));
    assert(car.speed==0);
    drive_reset(&car,0,0,0);
    for (unsigned i=0;i<300;++i) assert(drive_step(&car,(DriveInput){.throttle=-1},1.0f/120));
    assert(car.speed<0 && car.speed>=-7 && car.z<0);
    drive_reset(&car,0,0,0);
    for (unsigned i=0;i<360;++i) assert(drive_step(&car,(DriveInput){.throttle=1,.steering=.5f},1.0f/120));
    assert(car.x>1 && car.heading>0);
    DriveState one,two;drive_reset(&one,0,0,0);drive_reset(&two,0,0,0);
    for (unsigned i=0;i<180;++i) assert(drive_step(&one,(DriveInput){.throttle=1,.steering=.2f},1.0f/60));
    for (unsigned i=0;i<360;++i) assert(drive_step(&two,(DriveInput){.throttle=1,.steering=.2f},1.0f/120));
    assert(fabsf(one.x-two.x)<.001f && fabsf(one.z-two.z)<.001f && fabsf(one.speed-two.speed)<.001f);
    /* Yaw builds over time and higher speed limits the steering angle. */
    drive_reset(&one,0,0,0);one.speed=25;
    assert(drive_step(&one,(DriveInput){.steering=1},1.0f/120));
    assert(one.yaw_rate>0 && one.yaw_rate<.1f);
    DriveState grip,slide;drive_reset(&grip,0,0,0);grip.speed=25;slide=grip;
    for (unsigned i=0;i<120;++i) {
        assert(drive_step(&grip,(DriveInput){.throttle=1,.steering=.8f},1.0f/120));
        assert(drive_step(&slide,(DriveInput){.throttle=1,.steering=.8f,.handbrake=true},1.0f/120));
    }
    assert(fabsf(slide.lateral_speed)>fabsf(grip.lateral_speed)*1.5f);
    assert(slide.yaw_rate>grip.yaw_rate);
    for (unsigned i=0;i<1200;++i) assert(drive_step(&slide,(DriveInput){.brake=1},1.0f/120));
    assert(slide.speed==0 && slide.lateral_speed==0 && slide.yaw_rate==0);
    /* A short handbrake tap initiates a slide that survives release, then
       regains grip rather than requiring the button to stay held. */
    drive_reset(&slide,0,0,0);slide.speed=14;
    for (unsigned i=0;i<42;++i) assert(drive_step(&slide,(DriveInput){.throttle=1,.steering=.8f,.handbrake=true},1.0f/120));
    float entry=fabsf(atan2f(slide.lateral_speed,slide.speed))*57.29578f;assert(entry>12);
    for (unsigned i=0;i<36;++i) assert(drive_step(&slide,(DriveInput){.throttle=1},1.0f/120));
    float released=fabsf(atan2f(slide.lateral_speed,slide.speed))*57.29578f;assert(released>8 && slide.drift>0);
    for (unsigned i=0;i<120;++i) assert(drive_step(&slide,(DriveInput){.throttle=1},1.0f/120));
    assert(fabsf(slide.lateral_speed)<.1f && slide.drift==0);
    printf("Handbrake tap: %.1f deg entry, %.1f deg after release, recovered grip.\n",entry,released);
    drive_reset(&one,0,0,0);one.speed=14;two=one;
    for (unsigned i=0;i<8;++i) assert(drive_step(&one,(DriveInput){.throttle=1,.steering=.8f,.handbrake=true},.05f));
    for (unsigned i=0;i<48;++i) assert(drive_step(&two,(DriveInput){.throttle=1,.steering=.8f,.handbrake=true},1.0f/120));
    for (unsigned i=0;i<8;++i) assert(drive_step(&one,(DriveInput){.throttle=1,.steering=-.3f},.05f));
    for (unsigned i=0;i<48;++i) assert(drive_step(&two,(DriveInput){.throttle=1,.steering=-.3f},1.0f/120));
    assert(fabsf(one.x-two.x)<.001f && fabsf(one.z-two.z)<.001f && fabsf(one.lateral_speed-two.lateral_speed)<.001f);
    DriveState low;drive_reset(&low,0,0,0);low.speed=14;DriveState high=low;
    duration(&low,(DriveInput){.throttle=1,.steering=.8f,.handbrake=true},.4f,18);
    duration(&high,(DriveInput){.throttle=1,.steering=.8f,.handbrake=true},.4f,120);
    duration(&low,(DriveInput){.throttle=1,.steering=-.3f},.4f,18);
    duration(&high,(DriveInput){.throttle=1,.steering=-.3f},.4f,120);
    assert(hypotf(low.x-high.x,low.z-high.z)<.05f && fabsf(low.heading-high.heading)<.02f);
    DriveState unchanged=car;
    assert(!drive_step(&car,(DriveInput){0},0));assert(!drive_step(&car,(DriveInput){0},NAN));
    assert(!drive_step(&car,(DriveInput){.throttle=NAN},.01f));assert(!drive_step(NULL,(DriveInput){0},.01f));
    assert(car.x==unchanged.x && car.z==unchanged.z && car.speed==unchanged.speed);
    puts("Driving controller checks passed (map-independent prototype; not game integration).");
    return 0;
}
