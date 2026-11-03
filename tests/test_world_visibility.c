#include "world_visibility.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
int main(void)
{
    float eye[3]={0},at[3]={0,0,1};WorldFrustum view;
    assert(world_frustum(&view,eye,at,1.570796327f,1,1,100));
    WorldBounds box={.center={0,0,10},.extent={1,1,1}};assert(world_visible(&view,&box));
    box.center[2]=-5;assert(!world_visible(&view,&box));
    box.center[2]=10;box.center[0]=30;assert(!world_visible(&view,&box));
    box.center[0]=11;assert(world_visible(&view,&box));
    box.center[0]=0;box.center[1]=30;assert(!world_visible(&view,&box));
    box.center[1]=0;box.center[2]=102;assert(!world_visible(&view,&box));
    box.center[2]=100;assert(world_visible(&view,&box));
    box=(WorldBounds){.center={0,0,.1f},.extent={.01f,.01f,.01f}};assert(!world_visible(&view,&box));
    box=(WorldBounds){.center={0},.extent={100,100,100}};assert(world_visible(&view,&box));
    /* Every independently projected point inside the frustum must survive. */
    for (int z=1;z<100;z+=3) for (int x=-z;x<=z;x+=3) for (int y=-z;y<=z;y+=5) {
        box=(WorldBounds){.center={(float)x,(float)y,(float)z}};assert(world_visible(&view,&box));
    }
    at[0]=1;at[2]=0;assert(world_frustum(&view,eye,at,1,1,1,100));
    box=(WorldBounds){.center={10,0,0}};assert(world_visible(&view,&box));box.center[0]=-10;assert(!world_visible(&view,&box));
    assert(!world_frustum(&view,eye,eye,1,1,1,100));assert(!world_frustum(&view,eye,at,NAN,1,1,100));
    assert(world_visible(NULL,&box));box.extent[0]=NAN;assert(world_visible(&view,&box));
    puts("Visibility checks passed: six planes, crossing/tangent boxes, rotated camera, projected points and invalid input.");return 0;
}
