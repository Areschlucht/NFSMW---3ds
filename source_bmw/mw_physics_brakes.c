#include "mw_physics_brakes.h"
#include <math.h>
const MwPhysicsBrakeCalibration mw_physics_original_brake_calibration={4.0f,10.0f,1.2f,100.0f,10.0f};
static float f32(float v) { volatile float f=v;return f; }
static float normal_torque(const MwPhysicsBrakeAttributes *a,const MwPhysicsBrakeCalibration *c,unsigned axle)
{ return f32(f32(a->normal_raw[axle]*1.3558f)*c->normal_scale); }
static float hand_torque(const MwPhysicsBrakeAttributes *a,const MwPhysicsBrakeCalibration *c)
{ return f32(f32(a->handbrake_raw*1.3558f)*c->handbrake_scale); }
void mw_physics_brake_lock_raw(const MwPhysicsBrakeAttributes *a,const MwPhysicsBrakeCalibration *c,MwPhysicsWheelBrakeState *s,float force)
{
    if (!a||!c||!s||s->axle>1) return;
    float hand=f32(s->handbrake_input*hand_torque(a,c));
    float normal=f32(f32(a->lock_multiplier[s->axle]*f32(a->normal_raw[s->axle]*1.3558f))*c->normal_scale);
    float threshold=f32(fmaf(s->normal_input,normal,hand)*c->lock_scale);
    float required=fmaf(force,s->radius_m,f32(fabsf(s->angular_speed)*c->angular_resistance));
    if (threshold>required) {
        s->locked=threshold>0.0f;
        s->angular_speed=0.0f;
    } else s->locked=0;
}
void mw_physics_wheel_spin_transition(MwPhysicsWheelBrakeState *s)
{
    if (!s) return;
    if ((s->direction==0 && s->angular_speed<0.0f)||(s->direction==2 && s->angular_speed>0.0f))s->angular_speed=0.0f;
    s->direction=s->angular_speed>0.000001f?0:s->angular_speed< -0.000001f?2:1;
}
void mw_physics_free_wheel_brake_step(const MwPhysicsBrakeAttributes *a,const MwPhysicsBrakeCalibration *c,MwPhysicsWheelBrakeState *s,float dt)
{
    if (!a||!c||!s||s->axle>1)return;
    mw_physics_brake_lock_raw(a,c,s,0.0f);
    if (s->locked) {s->angular_speed=0.0f;s->angular_acceleration=0.0f;}
    else {
        float normal=f32(s->normal_input*normal_torque(a,c,s->axle));
        float hand=f32(s->handbrake_input*hand_torque(a,c));
        if(s->angular_speed>0.0f)normal=-normal;
        s->accumulated_brake_torque=f32(s->accumulated_brake_torque+normal);
        if(s->angular_speed>0.0f)hand=-hand;
        s->accumulated_brake_torque=f32(s->accumulated_brake_torque+hand);
        s->angular_acceleration=f32(f32(s->drive_torque+s->accumulated_brake_torque)/c->inertia);
        s->angular_speed=fmaf(s->angular_acceleration,dt,s->angular_speed);
    }
    mw_physics_wheel_spin_transition(s);
}
