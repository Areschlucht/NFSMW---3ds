#include "mw_physics_lateral.h"
#include <math.h>
#include <stdint.h>
const MwPhysicsLateralCurves mw_physics_original_lateral_curves={{{0,0,0,0,0,0},
 {0,1.2f,2.3f,3,3,2.8f},{0,1.7f,3.2f,4.3f,5.1f,5.2f},
 {0,1.8f,3.5f,4.9f,5.8f,6.1f},{0,1.83f,3.6f,5,5.96f,6.4f},
 {0,1.86f,3.7f,5.1f,6.13f,6.7f},{0,1.9f,3.8f,5.2f,6.3f,7.1f}}};
static float f32(float v){volatile float f=v;return f;}
static float sample(const float *values,float x)
{
    float position=f32(0.5f*f32(x-0.0f));
    if(position<0)return values[0];
    if(position>=5)return values[5];
    int index=(int)position;
    float fraction=f32(position-f32((float)index));
    return fmaf(f32(1.0f-fraction),values[index],f32(fraction*values[index+1]));
}
float mw_physics_lateral_curve_raw(const MwPhysicsLateralCurves *curves,float force,float turns,float grip,float scale)
{
    if(!curves||!isfinite(force)||!isfinite(turns)||turns<0)return NAN;
    float coordinate=f32(f32(turns*360.0f)*0.5f);
    if(coordinate>2147483520.0f)return NAN;
    int index=(int)coordinate;
    float fraction=f32(coordinate-f32((float)index));
    float load=f32(f32(force*0.001f)*0.8f);
    float value;
    if(index<=5){
        float lo=sample(curves->samples[index],load),hi=sample(curves->samples[index+1],load);
        value=fmaf(fraction,f32(hi-lo),lo);
    }else value=sample(curves->samples[6],load);
    float multiplier=f32(grip*f32(scale*1000.0f));
    value=f32(value*2.5f);
    return f32(multiplier*value);
}
