#include "mw_lod_select.h"
#include <string.h>
#include <math.h>
#include <limits.h>

bool mw_lod_instance_visible(uint32_t instance_flags,uint32_t context_flags)
{
    return (((instance_flags&0xffu)^0x60u)&context_flags)==0;
}

static float original_sine(uint16_t angle)
{
    float x=(float)angle*9.5873801910784095526e-5f,sign=1.0f;
    if (x>=4.7123889923095703125f) x=x-6.283185482025146484375f;
    else if (x>=1.57079637050628662109375f) { sign=-1.0f;x=x-3.1415927410125732421875f; }
    float x2=x*x,x3=x*x2,x5=x3*x2;
    float result=x-x3*0.16666667163372039794921875f;
    float x7=x5*x2,term7=x7*0.000198412701138295233249664306640625f;
    result=fmaf(x5,0.008333333767950534820556640625f,result);
    float x9=x7*x2;
    result=result-term7;
    result=fmaf(x9,2.755731884462875313125550746917724609375e-6f,result);
    return result*sign;
}
float mw_lod_projection_raw(uint16_t fov)
{
    uint16_t half=(uint16_t)(fov>>1);
    float ratio=original_sine(half)/original_sine((uint16_t)(half+0x4000u));
    return ratio==0.0f?10.0f:256.0f/ratio;
}

bool mw_lod_projected_score(const float translation[3],const float camera[3],
                           const float forward[3],float object_radius,
                           float projection,MwLodSqrt sqrt_stage,
                           void *context,int32_t *score)
{
    if (!translation || !camera || !forward || !score ||
        !isfinite(object_radius) || !isfinite(projection)) return false;
    float d[3];
    for (unsigned a=0;a<3;++a) {
        if (!isfinite(translation[a]) || !isfinite(camera[a]) || !isfinite(forward[a])) return false;
        d[a]=translation[a]-camera[a];
    }
    float radius=object_radius+6.0f;
    float dot=fmaf(d[2],forward[2],fmaf(d[0],forward[0],d[1]*forward[1]));
    if (!(dot>=-radius)) { *score=0;return true; }
    float squared=fmaf(d[2],d[2],fmaf(d[0],d[0],d[1]*d[1]));
    float distance=squared>5.0000000667571598005e-11f?
        (sqrt_stage?sqrt_stage(squared,context):sqrtf(squared)):0.0f;
    float gap=distance-radius;
    float projected=projection;
    if (!(gap<=radius)) projected=(radius*projection)/gap;
    if (!isfinite(projected) || projected>=2147483648.0f || projected<-2147483648.0f) return false;
    *score=(int32_t)projected;return true;
}

int mw_lod_select(const MwLodSelectInput *in)
{
    if (!in || in->projected_score<=1) return -1;
    int32_t score=in->projected_score;
    if (in->instance_flags&0x02000000u) {
        uint32_t bits=(uint32_t)score+10u;
        memcpy(&score,&bits,sizeof(score)); /* original wrapping addi */
    }
    int slot=-1;
    if (in->context_flags&0x1800u) {
        if (score>=32) {
            if (in->instance_flags&0x80u) slot=2;
            else slot=(in->instance_flags&0x01000100u)?0:3;
        }
    } else if (in->context_flags&0x20u) {
        if (score>=32) slot=2;
    } else if (in->original_view_state>2) {
        if (score>22) slot=2;
    } else if (score>17) {
        slot=0;
        if ((in->bound_slot_mask&1u) && in->slot0_has_mesh &&
            in->slot0_header_triangle_statistic>39) {
            float metric=in->slot0_header_metric_9c;
            if (!(metric>=6.0f)) metric=6.0f;
            float ratio=(float)score/metric;
            if (!(ratio>=8.69999980926513671875f)) slot=2;
        }
    }
    return slot>=0 && (in->bound_slot_mask&(1u<<(unsigned)slot))?slot:-1;
}
