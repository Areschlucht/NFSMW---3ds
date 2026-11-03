#include "mw_physics_friction.h"
#include <math.h>
static float f32(float v){volatile float f=v;return f;}
void mw_physics_friction_limit_given_magnitude(MwPhysicsFrictionState *s,float magnitude)
{
    if(!s)return;
    float limit=f32(s->normal_load*s->static_grip);
    limit=f32(limit*s->grip_factor);limit=f32(limit*s->combined_factor);limit=f32(limit*s->speed_factor);
    float budget=s->slip_budget;s->traction_factor=1.0f;
    if(magnitude>limit && magnitude>0.001f){
        float ratio=f32(limit/magnitude);
        s->longitudinal_force=f32(s->longitudinal_force*ratio);
        s->lateral_force=f32(s->lateral_force*ratio);s->traction_factor=ratio;
        budget=f32(budget*f32(ratio*ratio));
    }else if(s->undo_torque_boost)s->longitudinal_force=f32(s->longitudinal_force*0.6666666865348816f);
    float slip=fabsf(s->slip_speed);
    if(slip>budget)s->traction_factor=f32(s->traction_factor*f32(budget/slip));
}
