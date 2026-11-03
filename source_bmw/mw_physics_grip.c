#include "mw_physics_grip.h"
#include <math.h>
static float f32(float v){volatile float f=v;return f;}
float mw_physics_rear_grip_assist_raw(float f1,float hand,float f3,float yaw,float f5)
{
    float base=f32(fabsf(f5)+1.0f);
    float absolute=fabsf(f1);
    float bound=f32(20.0f*0.01745329424738884f);
    if(hand>0.5f && absolute<bound)return base;
    float position=f32(f32(f3-0.0f)/f32(30.0f-0.0f));
    float factor=fmaf(f32(1.0f-0.0f),position,0.0f);
    float addition=f32(f32(absolute*yaw)*factor);
    if(addition>0.35f)addition=0.35f;
    return f32(base+addition);
}
