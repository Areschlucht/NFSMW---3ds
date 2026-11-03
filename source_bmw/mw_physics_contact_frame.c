#include "mw_physics_contact_frame.h"
#include "mw_gekko_math.h"
#include <math.h>
static float f32(float v){volatile float f=v;return f;}
static MwPhysicsContactVector cross(MwPhysicsContactVector a,MwPhysicsContactVector b)
{
    MwPhysicsContactVector out={fmaf(a.y,b.z,-f32(a.z*b.y)),-fmaf(a.x,b.z,-f32(a.z*b.x)),-fmaf(a.y,b.x,-f32(a.x*b.y))};return out;
}
static float dot(MwPhysicsContactVector a,MwPhysicsContactVector b)
{return fmaf(a.z,b.z,f32(f32(a.x*b.x)+f32(a.y*b.y)));}
static MwPhysicsContactVector normalize(MwPhysicsContactVector a,const MwPhysicsContactMath *math)
{
    float squared=dot(a,a),length=math&&math->sqrt_raw?math->sqrt_raw(squared,math->context):mw_gekko_sqrt_newton1(squared);
    float inverse=length==0?0:f32(1.0f/length);
    MwPhysicsContactVector result={f32(a.x*inverse),f32(a.y*inverse),f32(a.z*inverse)};return result;
}
void mw_physics_contact_frame(const MwPhysicsContactVector *normal,const MwPhysicsContactVector *direction,const MwPhysicsContactVector *velocity,MwPhysicsContactFrame *out,const MwPhysicsContactMath *math)
{
    if(!normal||!direction||!velocity||!out)return;
    out->lateral_axis=normalize(cross(*normal,*direction),math);
    out->lateral_velocity=dot(*velocity,out->lateral_axis);
    out->longitudinal_velocity=dot(*velocity,*direction);
    MwPhysicsContactVector projected=cross(cross(*direction,*normal),*direction);
    float factor=fmaf(dot(projected,*normal),4.0f,-3.0f);
    out->normal_load_factor=factor>0.3f?factor:0.3f;
    out->longitudinal_force_axis=normalize(cross(out->lateral_axis,*normal),math);
}

void mw_physics_contact_world_force(const MwPhysicsContactFrame *frame,const MwPhysicsContactVector *up,float spring,float mass,float dt,float lateral,float longitudinal,MwPhysicsContactVector *out)
{
    if(!frame||!up||!out||!(dt>0))return;
    float cap=fabsf(f32(f32(f32(frame->lateral_velocity/dt)*0.25f)*mass));
    if(lateral>cap)lateral=cap;
    if(lateral< -cap)lateral=-cap;
    out->x=f32(f32(f32(frame->lateral_axis.x*lateral)+f32(frame->longitudinal_force_axis.x*longitudinal))+f32(up->x*spring));
    out->y=f32(f32(f32(frame->lateral_axis.y*lateral)+f32(frame->longitudinal_force_axis.y*longitudinal))+f32(up->y*spring));
    out->z=f32(f32(f32(frame->lateral_axis.z*lateral)+f32(frame->longitudinal_force_axis.z*longitudinal))+f32(up->z*spring));
}

float mw_physics_contact_normal_dot_up(const MwPhysicsContactVector *normal,const MwPhysicsContactVector *up)
{
    if(!normal||!up)return 0;
    float value=dot(*normal,*up);
    if(value>1)value=1;
    if(value<0)value=0;
    return value;
}
void mw_physics_contact_rotate_vector(const float m[16],const MwPhysicsContactVector *v,MwPhysicsContactVector *out)
{
    if(!m||!v||!out)return;
    MwPhysicsContactVector result;
    result.x=fmaf(m[8],v->z,fmaf(m[4],v->y,f32(m[0]*v->x)));
    result.y=fmaf(m[9],v->z,fmaf(m[5],v->y,f32(m[1]*v->x)));
    result.z=fmaf(m[10],v->z,fmaf(m[6],v->y,f32(m[2]*v->x)));
    *out=result;
}
void mw_physics_contact_point_velocity(const float m[16],const MwPhysicsContactVector *mount,const MwPhysicsContactVector *cg,const MwPhysicsContactVector *linear,const MwPhysicsContactVector *angular,MwPhysicsContactVector *query,MwPhysicsContactVector *velocity)
{
    if(!m||!mount||!cg||!linear||!angular||!query||!velocity)return;
    MwPhysicsContactVector offset;mw_physics_contact_rotate_vector(m,mount,&offset);
    MwPhysicsContactVector lever={f32(offset.x-cg->x),f32(offset.y-cg->y),f32(offset.z-cg->z)};
    MwPhysicsContactVector spin=cross(*angular,lever);
    *velocity=(MwPhysicsContactVector){f32(spin.x+linear->x),f32(spin.y+linear->y),f32(spin.z+linear->z)};
    *query=(MwPhysicsContactVector){f32(offset.x+m[12]),f32(offset.y+m[13]),f32(offset.z+m[14])};
}

void mw_physics_contact_force_moment(const float m[16],const MwPhysicsContactVector *mount,float compression,float ride_height,const MwPhysicsContactVector *cg,const MwPhysicsContactVector *force,MwPhysicsContactVector *point,MwPhysicsContactVector *moment)
{
    if(!m||!mount||!cg||!force||!point||!moment)return;
    MwPhysicsContactVector adjusted=*mount;
    adjusted.y=f32(f32(adjusted.y+compression)-ride_height);
    MwPhysicsContactVector rotated;mw_physics_contact_rotate_vector(m,&adjusted,&rotated);
    *point=(MwPhysicsContactVector){f32(rotated.x+m[12]),f32(rotated.y+m[13]),f32(rotated.z+m[14])};
    MwPhysicsContactVector lever={f32(f32(point->x-cg->x)-m[12]),f32(f32(point->y-cg->y)-m[13]),f32(f32(point->z-cg->z)-m[14])};
    *moment=cross(lever,*force);
}
