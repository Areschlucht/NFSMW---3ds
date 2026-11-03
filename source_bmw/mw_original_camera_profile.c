#include "mw_original_camera_profile.h"
#include <math.h>
#include <limits.h>
uint32_t mw_original_camera_profile_field(int mode)
{
    static const uint32_t fields[]={0x585517f3,0xd74c1435,0x0c2da793,0xccf03cb3,0x10204a90,0x4b675dc8,0xd76a6fad};
    return (unsigned)mode<sizeof fields/sizeof *fields?fields[mode]:0;
}
static bool turns(float degrees,uint16_t *result)
{
    float scaled=degrees*65536.0f;
    if (!isfinite(scaled) || scaled>=2147483648.0f || scaled<(-2147483647.0f-1)) return false;
    *result=(uint16_t)((int32_t)scaled/360);return true;
}
bool mw_original_camera_profile_cache(const MwOriginalCameraProfile *p,int view,float scale,MwOriginalCameraProfileCache *out)
{
    if (!p || !out || !isfinite(scale)) return false;
    unsigned i=view==3?1:0;
    if (!isfinite(p->angle_degrees[i]) || !isfinite(p->lag[i]) || !isfinite(p->height[i]) ||
        !isfinite(p->lateral_offset[i]) || !isfinite(p->fov_degrees[i]) || !isfinite(p->stiffness[i]) || p->tilting[i]>1) return false;
    if (scale<=0) scale=1;
    MwOriginalCameraProfileCache next={0};next.profile_index=i;
    float fov=p->fov_degrees[i]*scale;
    if (!turns(p->angle_degrees[i],&next.angle_turns) || !turns(fov,&next.fov_turns)) return false;
    next.lag=p->lag[i]/scale;next.height=p->height[i];next.lateral_offset=p->lateral_offset[i];
    next.stiffness=p->stiffness[i];next.tilting=(uint16_t)p->tilting[i];
    if (!isfinite(next.lag)) return false;
    *out=next;return true;
}

bool mw_original_camera_projection(uint16_t raw,unsigned width,unsigned height,
    unsigned full_height,float correction,float aspect_scale,float fov_scale,
    MwOriginalCameraProjection *out)
{
    if (!out || !width || !height || !full_height || width>65535 || height>65535 ||
        full_height>65535 || !isfinite(correction) || correction<=0 ||
        !isfinite(aspect_scale) || aspect_scale<=0 || !isfinite(fov_scale) || fov_scale<=0) return false;
    MwOriginalCameraProjection next;
    float y_factor=(float)height/(float)full_height;
    y_factor=y_factor*fov_scale;next.viewport_y_factor=y_factor;
    float aspect=(float)width*correction;
    aspect=aspect/(float)height;next.aspect=aspect*aspect_scale;
    float fov=(float)raw*0.0054931640625f;
    next.vertical_fov_degrees=fov*y_factor;
    if (!isfinite(next.aspect) || next.aspect<=0 || !isfinite(next.vertical_fov_degrees) ||
        next.vertical_fov_degrees<=0 || next.vertical_fov_degrees>=180) return false;
    *out=next;return true;
}
