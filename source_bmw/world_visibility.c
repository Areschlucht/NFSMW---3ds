#include "world_visibility.h"
#include <math.h>
#include <stddef.h>
bool world_frustum(WorldFrustum *out,const float eye[3],const float at[3],float fov,float aspect,float near_clip,float far_clip)
{
    if (!out || !eye || !at || !isfinite(fov) || !isfinite(aspect) || !isfinite(near_clip) || !isfinite(far_clip) ||
        fov<=0 || fov>=3.0f || aspect<=0 || near_clip<=0 || far_clip<=near_clip) return false;
    float forward[3],right[3],up[3],length=0;
    for (unsigned a=0;a<3;++a) {
        if (!isfinite(eye[a]) || !isfinite(at[a])) return false;
        forward[a]=at[a]-eye[a];length+=forward[a]*forward[a];
    }
    if (length<1e-12f || !isfinite(length)) return false;
    length=1/sqrtf(length);for (unsigned a=0;a<3;++a) forward[a]*=length;
    length=hypotf(forward[0],forward[2]);if (length<1e-6f) return false;
    right[0]=-forward[2]/length;right[1]=0;right[2]=forward[0]/length;
    up[0]=right[1]*forward[2]-right[2]*forward[1];
    up[1]=right[2]*forward[0]-right[0]*forward[2];
    up[2]=right[0]*forward[1]-right[1]*forward[0];
    float vertical=tanf(fov*.5f),horizontal=vertical*aspect;WorldFrustum result={0};
    for (unsigned a=0;a<3;++a) {
        result.plane[0][a]=forward[a];result.plane[1][a]=-forward[a];
        result.plane[2][a]=forward[a]*horizontal+right[a];result.plane[3][a]=forward[a]*horizontal-right[a];
        result.plane[4][a]=forward[a]*vertical+up[a];result.plane[5][a]=forward[a]*vertical-up[a];
    }
    for (unsigned p=0;p<6;++p) for (unsigned a=0;a<3;++a) result.plane[p][3]-=result.plane[p][a]*eye[a];
    result.plane[0][3]-=near_clip;result.plane[1][3]+=far_clip;
    *out=result;return true;
}
bool world_visible(const WorldFrustum *view,const WorldBounds *bounds)
{
    /* Fail open: invalid culling metadata must never hide world geometry. */
    if (!view || !bounds) return true;
    for (unsigned a=0;a<3;++a) if (!isfinite(bounds->center[a]) || !isfinite(bounds->extent[a]) || bounds->extent[a]<0) return true;
    for (unsigned p=0;p<6;++p) {
        float distance=view->plane[p][3];
        for (unsigned a=0;a<3;++a) distance+=view->plane[p][a]*bounds->center[a]+fabsf(view->plane[p][a])*bounds->extent[a];
        if (distance < -1e-5f) return false;
    }
    return true;
}
