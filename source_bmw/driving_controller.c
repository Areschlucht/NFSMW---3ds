#include "driving_controller.h"
#include <math.h>
#include <stddef.h>

static float clamp(float x,float low,float high) { return x<low?low:x>high?high:x; }
void drive_reset(DriveState *state,float x,float z,float heading)
{
    if (!state) return;
    *state=(DriveState){.x=x,.z=z,.heading=heading};
}
bool drive_step(DriveState *state,DriveInput input,float seconds)
{
    if (!state || !isfinite(seconds) || seconds<=0 || seconds>0.1f ||
        !isfinite(input.throttle) || !isfinite(input.brake) || !isfinite(input.steering) ||
        !isfinite(state->x) || !isfinite(state->z) || !isfinite(state->heading) ||
        !isfinite(state->speed) || !isfinite(state->steering) || !isfinite(state->lateral_speed) || !isfinite(state->yaw_rate) || !isfinite(state->drift)) return false;
    input.throttle=clamp(input.throttle,-1,1);input.brake=clamp(input.brake,0,1);input.steering=clamp(input.steering,-1,1);
    /* Substep at 120 Hz or finer. The caller applies world ground contact;
       this module supplies only the new arcade handling controller. */
    unsigned count=(unsigned)ceilf(seconds*120);
    float dt=seconds/count;
    float yaw_response=1-expf(-7*dt);
    for (unsigned i=0;i<count;++i) {
        float previous=state->speed;
        /* Provisional arcade handling, not recovered MW vehicle attributes:
           power-limited acceleration, speed-sensitive steering, yaw inertia
           and lateral grip. Handbraking releases rear grip rather than simply
           multiplying an instantaneous kinematic turn. */
        float resistance=.7f+.0014f*previous*previous;
        float force=input.throttle*fminf(10.5f,420/fmaxf(10,fabsf(previous)));
        if (previous>0) force-=resistance;
        if (previous<0) force+=resistance;
        float braking=(input.brake*18)+(input.handbrake?5:0);
        force+=state->lateral_speed*state->yaw_rate;
        if (previous>0) force-=braking;
        if (previous<0) force+=braking;
        if (previous==0 && braking>0) force=copysignf(fmaxf(0,fabsf(force)-braking),force);
        state->speed=clamp(previous+force*dt,-7,65);
        if (previous*state->speed<0 && (braking>0 || input.throttle==0)) state->speed=0;
        if (fabsf(state->speed)<0.015f && input.throttle==0) state->speed=0;
        float speed=fabsf(state->speed);
        bool initiate=input.handbrake && speed>6 && (fabsf(input.steering)>.1f || fabsf(state->yaw_rate)>.1f);
        state->drift=clamp(state->drift+dt*(initiate?6.0f:-.9f),0,1);
        float target=input.steering*.58f/(1+speed*speed/500);
        float steering_rate=fabsf(target)<fabsf(state->steering)?3.5f:2.8f;
        state->steering+=clamp(target-state->steering,-steering_rate*dt,steering_rate*dt);
        float desired=state->speed/2.73f*tanf(state->steering)/(1+speed*speed/1600);
        float yaw_limit=(10+18*state->drift)/fmaxf(speed,4);
        desired*=1+1.4f*state->drift;
        desired=clamp(desired,-yaw_limit,yaw_limit);
        state->yaw_rate+=(desired-state->yaw_rate)*yaw_response;
        float grip=8-7*state->drift;
        state->lateral_speed+=(-state->speed*state->yaw_rate-grip*state->lateral_speed)*dt;
        float slip_limit=fminf(18,fmaxf(3,speed*.95f));
        state->lateral_speed=clamp(state->lateral_speed,-slip_limit,slip_limit);
        if (speed<.05f) { state->lateral_speed=0;state->yaw_rate=0;state->drift=0; }
        state->heading=remainderf(state->heading+state->yaw_rate*dt,6.283185307f);
        float s=sinf(state->heading),c=cosf(state->heading);
        state->x+=(s*state->speed+c*state->lateral_speed)*dt;
        state->z+=(c*state->speed-s*state->lateral_speed)*dt;
    }
    return true;
}
