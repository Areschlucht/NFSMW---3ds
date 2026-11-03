#ifndef WORLD_VISIBILITY_H
#define WORLD_VISIBILITY_H
#include <stdbool.h>
typedef struct { float center[3],extent[3]; } WorldBounds;
typedef struct { float plane[6][4]; } WorldFrustum;
bool world_frustum(WorldFrustum *out,const float eye[3],const float at[3],float fov,float aspect,float near_clip,float far_clip);
bool world_visible(const WorldFrustum *view,const WorldBounds *bounds);
#endif
