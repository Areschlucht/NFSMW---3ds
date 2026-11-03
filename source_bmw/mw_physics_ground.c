#include "mw_physics_ground.h"
#include <string.h>
static float f32(float value){volatile float result=value;return result;}
void mw_physics_ground_antiroll(const MwPhysicsGroundWheel wheels[4],const float sway[2],float out[4])
{
    if(!wheels||!sway||!out)return;
    float previous[4];
    for(unsigned i=0;i<4;i++)previous[i]=wheels[i].compression;
    mw_physics_suspension_antiroll(previous,sway,out);
}
bool mw_physics_ground_wheel_step(MwPhysicsGroundWheel *wheel,const MwPhysicsGroundInput *input,const MwPhysicsSuspensionAxle *axle,const MwPhysicsContactParameters *parameters,MwPhysicsGroundOutput *output,const MwPhysicsSuspensionMath *suspension_math,const MwPhysicsContactMath *contact_math)
{
    if(!wheel||!input||!axle||!parameters||!output||!(input->seconds>0))return false;
    memset(output,0,sizeof(*output));
    mw_physics_contact_frame(&input->normal,&input->steered_direction,&input->point_velocity,&output->frame,contact_math);
    MwPhysicsSuspensionInput suspension_input={
        input->query_relative_plane_w,
        mw_physics_contact_normal_dot_up(&input->normal,&input->body_up),
        wheel->compression,input->seconds,input->additional_ride_height_inches,
        input->antiroll_force,input->body_mass
    };
    mw_physics_suspension_load(axle,&suspension_input,&output->suspension,suspension_math);
    if(output->suspension.has_contact){
        MwPhysicsContactInput tire_input={output->frame.lateral_velocity,
            output->frame.longitudinal_velocity,input->vehicle_speed_mps,
            f32(output->frame.normal_load_factor*output->suspension.normal_force),input->seconds};
        if(!mw_physics_contact_step(&wheel->tire,&tire_input,parameters,contact_math))return false;
        mw_physics_contact_world_force(&output->frame,&input->body_up,
            output->suspension.normal_force,input->body_mass,input->seconds,
            wheel->tire.lateral_force,wheel->tire.longitudinal_force,&output->world_force);
    }else if(!mw_physics_contact_free_step(&wheel->tire,parameters,input->seconds))return false;
    /* Original8024AE98..AECC tests compression, independently of the normal
     * angle/contact branch. A compressed wheel on a steep surface is free
     * spinning yet does not accumulate airborne time. */
    wheel->air_seconds=output->suspension.compression==0?f32(wheel->air_seconds+input->seconds):0;
    wheel->compression=output->suspension.compression;
    return true;
}
