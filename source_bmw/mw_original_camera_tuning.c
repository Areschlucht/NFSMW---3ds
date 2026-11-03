#include "mw_original_camera_tuning.h"
#include <math.h>
_Static_assert(sizeof(MwOriginalCameraTuning)==176,"Original tuning layout");
bool mw_original_camera_tuning_parameter(float speed,float *out)
{
    if(!out || !isfinite(speed) || speed<0)return false;
    float t=speed*0.014084506779909134f;
    if(t>1)t=1;
    *out=t;return true;
}
bool mw_original_camera_tuning_blend(const MwOriginalCameraTuning *lower,
    const MwOriginalCameraTuning *upper,float t,MwOriginalCameraTuning *out)
{
    if(!lower || !upper || !out || !isfinite(t))return false;
    MwOriginalCameraTuning result=*out;
    float complement=1.0f-t;
    for(unsigned i=0;i<4;++i){
        if(!isfinite(lower->scalar[i]) || !isfinite(upper->scalar[i]))return false;
        float base=complement*lower->scalar[i];
        result.scalar[i]=fmaf(t,upper->scalar[i],base);
        if(!isfinite(result.scalar[i]))return false;
    }
    for(unsigned i=0;i<10;++i)for(unsigned j=0;j<3;++j){
        if(!isfinite(lower->vector[i][j]) || !isfinite(upper->vector[i][j]))return false;
        float base=t*upper->vector[i][j];
        result.vector[i][j]=fmaf(complement,lower->vector[i][j],base);
        if(!isfinite(result.vector[i][j]))return false;
    }
    *out=result;return true;
}
