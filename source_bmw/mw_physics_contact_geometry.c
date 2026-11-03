#include "mw_physics_contact_geometry.h"
static float f32(float v){volatile float f=v;return f;}
void mw_physics_contact_mounts(const MwPhysicsTireDimensions *tires,const float track[2],float front,float base,float half_extent_y,MwPhysicsContactVector mounts[4])
{
    if(!tires||!track||!mounts)return;
    float front_width=f32(track[0]-f32(tires->section_width_mm[0]*0.001f));
    float rear_width=f32(track[1]-f32(tires->section_width_mm[1]*0.001f));
    float rear=f32(front-base),y=-half_extent_y;
    mounts[0]=(MwPhysicsContactVector){f32(-front_width*0.5f),y,front};
    mounts[1]=(MwPhysicsContactVector){f32(front_width*0.5f),y,front};
    mounts[2]=(MwPhysicsContactVector){f32(-rear_width*0.5f),y,rear};
    mounts[3]=(MwPhysicsContactVector){f32(rear_width*0.5f),y,rear};
}
