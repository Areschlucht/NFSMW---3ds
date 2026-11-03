#include "mw_physics_drivetrain.h"
#include <math.h>
static float f32(float v){volatile float f=v;return f;}
float mw_physics_requested_rpm(const MwPhysicsTireDimensions *t,const float *ratios,size_t count,unsigned gear,float final,float idle,float redline,float speed)
{
    if(!t||!ratios||gear>=count||!isfinite(speed))return NAN;
    float rear=f32(mw_physics_tire_diameter_m(t,0)*0.5f);
    float diameter_average=fmaf(mw_physics_tire_diameter_m(t,1),0.5f,rear);
    float radius=f32(diameter_average*0.5f);
    if(!(radius>0.0f))return idle;
    float omega=f32(fabsf(speed)/radius);
    float idle_omega=f32(idle*0.10471976548433304f);
    float redline_omega=f32(redline*0.10471976548433304f);
    float range=f32(redline_omega-idle_omega);
    float result=f32(final*ratios[gear]);
    result=f32(omega*result);
    result=f32(result*range);
    result=f32(result/redline_omega);
    result=f32(idle_omega+result);
    result=f32(result*9.549296379089355f);
    if(result>redline)result=redline;
    if(result<idle)result=idle;
    return result;
}
