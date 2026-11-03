#include "mw_physics_suspension.h"
#include <math.h>
#include <string.h>
static float f32(float v){volatile float f=v;return f;}
void mw_physics_suspension_load(const MwPhysicsSuspensionAxle *a,const MwPhysicsSuspensionInput *in,MwPhysicsSuspensionOutput *out,const MwPhysicsSuspensionMath *math)
{
    if(!a||!in||!out)return;
    memset(out,0,sizeof(*out));if(!(in->seconds>0))return;
    float normal=in->normal_dot_body_up;
    if(normal>1)normal=1;
    if(normal<0)normal=0;
    float travel=f32(a->travel_inches*0.0254f);
    float height=f32(f32(a->ride_height_inches+in->additional_ride_height_inches)*0.0254f);
    float compression=fmaf(height,normal,in->query_relative_plane_w);
    if(compression>travel)out->penetration_excess=f32(compression-travel);
    if(compression<0)compression=0;
    if(compression>travel){compression=travel;out->bottomed_out=true;}
    out->compression=compression;
    if(!(compression>0&&normal>0.2f))return;
    out->has_contact=true;
    float velocity=f32(f32(compression-in->previous_compression)/in->seconds);
    float spring_rate=f32(a->spring_stiffness*175.1268f);
    float progression=fmaf(compression,a->spring_progression,1.0f);
    out->spring_force=f32(f32(compression*spring_rate)*progression);
    float valving=f32(a->shock_valving*0.0254f),exponent=f32(1.0f-a->shock_digression);
    if(valving>0.000001f&&exponent<1&&fabsf(velocity)>valving){
        float ratio=f32(fabsf(velocity)/valving);
        float power=math&&math->power?math->power(ratio,exponent,math->context):powf(ratio,exponent);
        float limited=f32(valving*power);velocity=velocity>0?limited:-limited;
    }
    out->compression_velocity=velocity;
    float shock_rate=f32((velocity>0?a->shock_stiffness:a->shock_ext_stiffness)*175.1268f);
    float damper=f32(velocity*shock_rate);
    float threshold=f32(a->shock_blowout*f32(in->body_mass*9.81f));
    if(damper>threshold)damper=0;
    out->damper_force=damper;
    float force=f32(f32(damper+out->spring_force)+in->antiroll_force);
    out->normal_force=force>0?force:0;
}
void mw_physics_suspension_antiroll(const float previous[4],const float sway[2],float out[4])
{
    if(!previous||!sway||!out)return;
    for(unsigned axle=0;axle<2;axle++){
        float force=f32(f32(previous[axle*2]-previous[axle*2+1])*f32(sway[axle]*175.1268f));
        out[axle*2]=force;out[axle*2+1]=-force;
    }
}
