#include "mw_original_camera_cubic.h"
#include <math.h>
#include <stddef.h>
_Static_assert(sizeof(MwOriginalCameraCubic)==44,"Original cubic channel layout");
_Static_assert(offsetof(MwOriginalCameraCubic,state)==40,"Original state offset");
static float value_at(const MwOriginalCameraCubic *s,float t)
{return fmaf(fmaf(fmaf(s->cubic[0],t,s->cubic[1]),t,s->cubic[2]),t,s->cubic[3]);}
static float derivative_at(const MwOriginalCameraCubic *s,float t)
{float twice=s->cubic[1]+s->cubic[1],three=t*3.0f;return fmaf(fmaf(s->cubic[0],three,twice),t,s->cubic[2]);}
static float physical_derivative(const MwOriginalCameraCubic *s,float time)
{float reciprocal=1.0f/s->duration;float t=time*reciprocal;return derivative_at(s,t)*reciprocal;}
static float physical_second(const MwOriginalCameraCubic *s,float time)
{
    float reciprocal=1.0f/s->duration,t=time*reciprocal;
    float twice=s->cubic[1]+s->cubic[1],six=t*6.0f;
    float result=fmaf(s->cubic[0],six,twice);reciprocal=reciprocal*reciprocal;
    return result*reciprocal;
}
static void coefficients(MwOriginalCameraCubic *s)
{
    float difference=s->target-s->value,twice=difference+difference;
    float double_rate=s->derivative+s->derivative;
    float b=fmaf(difference,3.0f,-s->target_derivative);
    float a=s->derivative+s->target_derivative;
    s->cubic[2]=s->derivative;s->cubic[3]=s->value;
    a=a-twice;b=b-double_rate;s->cubic[0]=a;s->cubic[1]=b;
}
static bool valid(const MwOriginalCameraCubic *s)
{
    if (!s || s->state<0 || s->state>2) return false;
    const float fields[]={s->value,s->derivative,s->target,s->target_derivative,
        s->cubic[0],s->cubic[1],s->cubic[2],s->cubic[3],s->progress,s->duration};
    for(unsigned i=0;i<sizeof fields/sizeof *fields;++i)if(!isfinite(fields[i]))return false;
    return true;
}
bool mw_original_camera_cubic_target(MwOriginalCameraCubic *s,float target)
{
    if (!s || !isfinite(target)) return false;
    s->target=target;if(target!=s->value)s->state=2;return true;
}
bool mw_original_camera_cubic_step(MwOriginalCameraCubic *state,float delta,float max_rate,float max_second)
{
    if (!valid(state) || !isfinite(delta) || !isfinite(max_rate) || !isfinite(max_second))return false;
    MwOriginalCameraCubic s=*state;
    if (s.state==2) {
        if ((max_rate>0 || max_second>0) && s.duration==0)return false;
        s.progress=0;if(s.mode==0)s.state=1;
        if(max_rate>0) {
            float end_rate=physical_derivative(&s,s.duration),magnitude=fabsf(end_rate);
            if(magnitude>max_rate){float sign=magnitude/end_rate;float limited=sign*max_rate;s.target_derivative=limited*s.duration;}
        }
        coefficients(&s);
        if(max_second>0) {
            float first=physical_second(&s,0),last=physical_second(&s,s.duration);
            bool changed=false;float magnitude=fabsf(first);
            if(magnitude>max_second){float sign=magnitude/first;first=sign*max_second;changed=true;}
            magnitude=fabsf(last);
            if(magnitude>max_second){float sign=magnitude/last;last=sign*max_second;changed=true;}
            if(changed){float duration_squared=s.duration*s.duration;
                first=first*duration_squared;
                float a=fmaf(last,duration_squared,-first);a=a*0.1666666716337204f;
                float b=first*0.5f;s.cubic[0]=a;s.cubic[1]=b;
            }
        }
    }
    if(s.state==1 || s.state==2) {
        float progress;
        if(s.duration>0.000009999999747378752f){float increment=delta/s.duration;progress=s.progress+increment;}
        else progress=1;
        s.progress=progress;
        if(progress>1){s.progress=1;s.value=s.target;s.derivative=s.target_derivative;s.state=0;}
        float parameter=s.progress;s.value=value_at(&s,parameter);s.derivative=derivative_at(&s,parameter);
    }
    if(!valid(&s))return false;
    *state=s;return true;
}
