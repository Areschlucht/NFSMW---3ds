/* Host-only profiling bridge to the exact portable camera/culling functions.
   This file is not part of the console renderer or installation ZIP. */
#include "chase_camera.h"
#include "world_visibility.h"
#include <stddef.h>
#include <stdint.h>
bool perf_visible_pose(const WorldBounds *bounds,size_t count,const float spawn[4],float scale,uint8_t *visible)
{
    if (!bounds || !count || !spawn || !visible) return false;
    DriveState car={.x=spawn[0],.z=spawn[2],.heading=spawn[3]};ChaseCamera camera;
    if (!chase_reset(&camera,&car,spawn[1])) return false;
    float eye[3],at[3];for (unsigned a=0;a<3;++a) { eye[a]=camera.eye[a]*scale;at[a]=camera.target[a]*scale; }
    WorldFrustum view;
    if (!world_frustum(&view,eye,at,camera.fov*(3.14159265358979323846f/180.0f),400.0f/240,.15f*scale,700*scale)) return false;
    for (size_t i=0;i<count;++i) visible[i]=(uint8_t)world_visible(&view,&bounds[i]);
    return true;
}
