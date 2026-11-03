#include "mw_original_camera_direction.h"
#include "mw_gekko_math.h"
#include <math.h>
bool mw_original_camera_direction_target(const float velocity[3],const float forward[3],float speed,float target[3],float *weight)
{
    if (!velocity || !forward || !target || !isfinite(speed) || speed<0) return false;
    float v[3];for (unsigned a=0;a<3;++a) {
        if (!isfinite(velocity[a]) || !isfinite(forward[a])) return false;
        v[a]=velocity[a];
    }
    float dot=v[1]*forward[1];dot=fmaf(v[0],forward[0],dot);dot=fmaf(v[2],forward[2],dot);
    if (!isfinite(dot)) return false;
    if (dot<0) {float reflection=dot*-2.0f;for(unsigned a=0;a<3;++a)v[a]=fmaf(forward[a],reflection,v[a]);}
    /* Source startup80080F8C..80081004 installs [(8,0),(13,1)] in8045ACB0. */
    float blend=speed<=8?0:speed>=13?1:(speed-8.0f)/5.0f;
    float squared=v[1]*v[1];squared=fmaf(v[0],v[0],squared);squared=fmaf(v[2],v[2],squared);
    if (!isfinite(squared)) return false;
    float length=mw_gekko_sqrt_newton2(squared);
    if (length!=0) {float reciprocal=1.0f/length;for(unsigned a=0;a<3;++a)v[a]=v[a]*reciprocal;}
    else {v[0]=1;v[1]=v[2]=0;}
    float rest=1.0f-blend,next[3];
    for(unsigned a=0;a<3;++a){float scaled=v[a]*blend;next[a]=fmaf(forward[a],rest,scaled);if(!isfinite(next[a]))return false;}
    for(unsigned a=0;a<3;++a) target[a]=next[a];
    if(weight) *weight=blend;
    return true;
}
