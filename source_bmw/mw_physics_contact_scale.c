#include "mw_physics_contact_scale.h"
#include <math.h>
static float f32(float v){volatile float f=v;return f;}
static const float grip_curve[10]={.909f,1.045f,1.09f,1.09f,1.09f,1.09f,1.09f,1.045f,1,1};
static const float force_curve[10]={.833f,.958f,1.008f,1.0167f,1.033f,1.033f,1.033f,1.0167f,1,1};
static float sample(const float *data,float position)
{
    float x=f32(9.0f*f32(position-0.0f));int index=(int)x;
    if(index<0||x<0)return data[0];
    if(index>=9)return data[9];
    float fraction=f32(x-(float)index);
    return fmaf(f32(1.0f-fraction),data[index],f32(fraction*data[index+1]));
}
void mw_physics_contact_scales(const MwPhysicsContactScaleInput *in,MwPhysicsContactScales *out)
{
    if(!in||!out)return;
    float budget=f32(f32(in->speed_mps-10.0f)/f32(71.0f-10.0f));
    if(budget>1)budget=1;
    if(budget<0)budget=0;
    budget=f32(budget+0.5f);out->slip_budget=in->gear_slot==0?71.0f:budget;
    float position=f32(in->speed_mps/f32(85.0f*0.44703f));
    if(position>1)position=1;
    if(position<0)position=0;
    out->curve_scale=in->vehicle_mode_c8==1?3.0f:f32(sample(force_curve,position)*1.2f);
    out->grip_factor=in->vehicle_mode_c8==1?1.1f:f32(sample(grip_curve,position)*1.1f);
    if(in->gear_slot==0)out->grip_factor=2.0f;
    out->coupling_13c=fmaf(in->effect_100,f32(1.0f-0.15f),0.15f);
    if(in->include_additional_grip&&in->additional_grip_argument>0)out->grip_factor=fmaf(in->additional_grip_argument,0.25f,out->grip_factor);
}
