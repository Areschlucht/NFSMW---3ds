#include "mw_physics_transmission_policy.h"
#include <math.h>
#include <string.h>
static float f32(float value){volatile float rounded=value;return rounded;}
static float bounded01(float value)
{
    if(value>1)return 1;
    if(value<0)return 0;
    return value;
}
float mw_physics_transmission_induction_raw(const MwPhysicsEngineCurve *engine,
    const MwPhysicsTransmissionInduction *p,float rpm,float amount)
{
    if(!engine||!p||!isfinite(rpm)||!isfinite(amount)||!isfinite(engine->idle_rpm)||
       !isfinite(engine->red_line_rpm)||!isfinite(p->low_boost)||!isfinite(p->high_boost)||
       !isfinite(p->vacuum)||!isfinite(p->spool))return NAN;
    amount=bounded01(amount);
    float threshold=fmaf(p->spool,f32(engine->red_line_rpm-engine->idle_rpm),engine->idle_rpm);
    float boost=0;
    if(p->high_boost>0 || p->low_boost>0) {
        if(rpm>=threshold) {
            float distance=f32(engine->red_line_rpm-threshold),fraction=0;
            if(distance>0.0000009999999974752427f)fraction=bounded01(f32(f32(rpm-threshold)/distance));
            boost=fmaf(fraction,p->high_boost,f32(f32(1.0f-fraction)*p->low_boost));
        } else if(p->vacuum<0) {
            float distance=f32(threshold-engine->idle_rpm),fraction=0;
            if(distance>0.0000009999999974752427f)fraction=bounded01(f32(f32(rpm-engine->idle_rpm)/distance));
            boost=f32(fraction*p->vacuum);
        }
    }
    return f32(boost*amount);
}
bool mw_physics_transmission_shift_tables(const MwPhysicsEngineCurve *engine,
    const MwPhysicsTransmissionInduction *induction,const float *ratios,size_t count,
    MwPhysicsTransmissionShiftTables *out)
{
    if(!out)return false;
    memset(out,0,sizeof(*out));
    if(!engine||!induction||!ratios||count<3||count>MW_PHYSICS_TRANSMISSION_MAX_GEARS||
       !isfinite(engine->idle_rpm)||!isfinite(engine->red_line_rpm)||
       engine->red_line_rpm<engine->idle_rpm)return false;
    for(size_t i=0;i<count;++i)if(!isfinite(ratios[i]))return false;
    for(size_t gear=2;gear+1<count;++gear) {
        float current=ratios[gear],next=ratios[gear+1];
        float rpm=f32(f32(engine->idle_rpm+engine->red_line_rpm)*0.5f);
        bool found=false;unsigned iterations=0;
        while(rpm<engine->red_line_rpm) {
            if(++iterations>4096)return false;
            float torque=mw_physics_engine_curve_raw(engine,rpm);
            /* Original startup function supplies(1,RPM), even though the
             * induction leaf consumes(RPM,amount). Preserve that call order. */
            float boost=mw_physics_transmission_induction_raw(engine,induction,1.0f,rpm);
            float now=f32(torque*f32(boost+1.0f)),after=0;
            if(fabsf(current)>0.000009999999747378752f) {
                float next_rpm=f32(f32(next/current)*rpm);
                after=mw_physics_engine_curve_raw(engine,next_rpm);
                boost=mw_physics_transmission_induction_raw(engine,induction,1.0f,next_rpm);
                after=f32(f32(f32(after*next)/current)*f32(boost+1.0f));
            }
            if(!isfinite(now)||!isfinite(after))return false;
            if(after>now){out->up[gear]=rpm;found=true;break;}
            rpm=f32(rpm+50.0f);
        }
        if(!found)out->up[gear]=f32(engine->red_line_rpm-100.0f);
        if(fabsf(current)>0.000009999999747378752f)
            out->down[gear+1]=f32(f32(out->up[gear]*next)/current);
    }
    out->up[count-1]=engine->red_line_rpm;out->count=count;return true;
}
unsigned mw_physics_transmission_shift_request(const MwPhysicsTransmissionShiftTables *tables,
    const float *ratios,size_t count,unsigned gear,float rpm,float throttle,float idle)
{
    if(!tables||!ratios||count<3||count>MW_PHYSICS_TRANSMISSION_MAX_GEARS||
       tables->count!=count||gear>=count||!isfinite(rpm)||!isfinite(throttle)||!isfinite(idle))return 0;
    if(gear<=1)return 0;
    float up=tables->up[gear],down=tables->down[gear],previous=ratios[gear-1];
    if(gear!=2 && previous>0) {
        float prior_up=tables->up[gear-1];
        float limit=f32(f32(f32(prior_up*ratios[gear])/previous)-200.0f);
        float low=fmaf(f32(down-idle),0.6499999761581421f,idle);
        down=fmaf(f32(down-low),throttle,low);
        if(down>limit)down=limit;
    }
    if(rpm>=up && gear<count-1)return 2;
    if(rpm<=down && gear>2)return 1;
    return 0;
}


bool mw_physics_transmission_peak_torque(const MwPhysicsEngineCurve *engine,
    const MwPhysicsTransmissionInduction *induction,float *torque,float *rpm)
{
    if(!engine||!induction||!torque||!rpm||!engine->torque||!engine->count||
       engine->count>4096||!isfinite(engine->idle_rpm)||!isfinite(engine->max_rpm)||
       !isfinite(engine->red_line_rpm))return false;
    float peak=0,selected=engine->idle_rpm;
    if(engine->count>1) {
        float step=f32(f32(engine->max_rpm-engine->idle_rpm)/(float)(engine->count-1));
        float current=engine->idle_rpm;
        for(size_t i=0;i<engine->count;++i) {
            float boost=mw_physics_transmission_induction_raw(engine,induction,current,1);
            float sample=f32(engine->torque[i]*f32(boost+1.0f));
            if(!isfinite(sample))return false;
            if(sample>peak){peak=sample;selected=current;}
            current=f32(current+step);
        }
        if(selected>engine->red_line_rpm)selected=engine->red_line_rpm;
        if(selected<engine->idle_rpm)selected=engine->idle_rpm;
    }
    *torque=peak;*rpm=selected;return true;
}
