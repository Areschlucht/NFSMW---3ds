#include "mw_body_collision.h"
#include "mw_gekko_math.h"
#include <math.h>
static float f32(float v){volatile float value=v;return value;}
int mw_body_collision_tangent_response_with_math(const float coefficients[2],const float velocity[3],
    const float normal[3],float normal_component,float correction[3],const MwBodyCollisionMath *math){
    if(!coefficients||!velocity||!normal||!correction||!isfinite(normal_component))return -1;
    for(unsigned a=0;a<2;a++)if(!isfinite(coefficients[a])||coefficients[a]<0)return -1;
    for(unsigned a=0;a<3;a++)if(!isfinite(velocity[a])||!isfinite(normal[a]))return -1;
    float tangent[3],approach=-normal_component;
    correction[0]=0;correction[1]=0;correction[2]=0;
    if(approach<=0)return 0;
    for(unsigned a=0;a<3;a++)tangent[a]=f32(velocity[a]+f32(normal[a]*approach));
    float xy=f32(f32(tangent[0]*tangent[0])+f32(tangent[1]*tangent[1]));
    float squared=fmaf(tangent[2],tangent[2],xy);
    float speed=math&&math->sqrt_raw?math->sqrt_raw(squared,math->context):mw_gekko_sqrt_newton1(squared);
    if(!isfinite(speed))return -1;
    if(speed<=0)return 1;
    if(speed<=f32(approach*coefficients[1])){
        for(unsigned a=0;a<3;a++)correction[a]=-tangent[a];
        return 1;
    }
    float scale=f32(-f32(approach*coefficients[0])/speed);
    for(unsigned a=0;a<3;a++)correction[a]=f32(tangent[a]*scale);
    return 2;
}

int mw_body_collision_tangent_response(const float coefficients[2],const float velocity[3],
    const float normal[3],float normal_component,float correction[3]) {
    return mw_body_collision_tangent_response_with_math(coefficients,velocity,normal,normal_component,correction,0);
}
int mw_body_collision_world_friction(const float *values,unsigned count,float surface,float out[2]){
    if(!values||!out||count<1||count>2||!isfinite(surface)||surface<0)return -1;
    for(unsigned i=0;i<count;i++)if(!isfinite(values[i])||values[i]<0)return -1;
    float sticking=values[0],sliding=count>1?values[1]:values[0];
    if(sliding>sticking)sliding=sticking;
    out[0]=f32(sliding*surface);out[1]=f32(sticking*surface);
    return isfinite(out[0])&&isfinite(out[1])?0:-1;
}
