#include "streamed_drive.h"
#include <math.h>
#include <string.h>
bool streamed_drive_surface(const void *context,float x,float z,float reference,float *height,float normal[3])
{
    const StreamedDriveSurface *s=context;
    if(!s||!s->road||!s->collision||!height||!isfinite(reference))return false;
    float viewer[3]={x,reference+1,z},native[3];
    world_collision_viewer_to_native(viewer,s->road->origin,native);
    WorldCollisionContact hit;
    if(world_collision_runtime_ground(s->collision,native,0,&hit)!=1)return false;
    float position[3];world_collision_native_to_viewer(hit.point_native,s->road->origin,position);
    if(fabsf(position[1]-reference)>2)return false;
    if(normal){
        /* The source query's normal has its own Y clamp. The visual plane fit
           uses the actual triangle, rather than treating that as a unit normal. */
        float a[3],b[3],cross[3];
        for(unsigned k=0;k<3;k++){a[k]=hit.triangle_native[1][k]-hit.triangle_native[0][k];b[k]=hit.triangle_native[2][k]-hit.triangle_native[0][k];}
        cross[0]=a[1]*b[2]-a[2]*b[1];cross[1]=a[2]*b[0]-a[0]*b[2];cross[2]=a[0]*b[1]-a[1]*b[0];
        float length=sqrtf(cross[0]*cross[0]+cross[1]*cross[1]+cross[2]*cross[2]);
        if(!(length>0))return false;
        float sign=cross[1]<0?-1:1;for(unsigned k=0;k<3;k++)cross[k]*=sign/length;
        world_collision_native_vector_to_viewer(cross,normal);
    }
    *height=position[1];return true;
}
int streamed_drive_step(const StreamedDriveSurface *surface,DriveState *car,float *height,DriveInput input,float seconds)
{
    if(!surface||!surface->collision||!surface->collision->ready||!car||!height||!isfinite(seconds)||seconds<=0||seconds>.1f)return WORLD_COLLISION_INVALID;
    unsigned steps=(unsigned)ceilf(seconds*120);
    for(unsigned i=0;i<steps;i++){
        DriveState next=*car;if(!drive_step(&next,input,seconds/steps))return WORLD_COLLISION_INVALID;
        float start_view[3]={car->x,*height+.65f,car->z},end_view[3]={next.x,*height+.65f,next.z},a[3],b[3];
        world_collision_viewer_to_native(start_view,surface->road->origin,a);world_collision_viewer_to_native(end_view,surface->road->origin,b);
        WorldCollisionContact hit;int wall=world_collision_runtime_wall(surface->collision,a,b,0,&hit);
        if(wall<0)return wall;
        float y;
        if(wall || !streamed_drive_surface(surface,next.x,next.z,*height,&y,NULL)){
            car->speed=car->lateral_speed=car->yaw_rate=car->drift=0;car->steering=next.steering;return 0;
        }
        *car=next;*height=y;
    }
    return 1;
}
