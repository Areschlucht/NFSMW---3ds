#include "mw_original_rigid_body.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
static MwOriginalRigidBody body(void)
{
    MwOriginalRigidBody s={0};s.quaternion[3]=1;s.inverse_mass=.5f;
    for(unsigned i=0;i<4;i++){s.orientation[i*5]=1;s.world_inverse_inertia[i*5]=1;}
    for(unsigned i=0;i<3;i++)s.inertia[i]=1;
    return s;
}
static void near(float x,float y){assert(fabsf(x-y)<.0001f);}
int main(void)
{
    const int16_t extent[3]={938,621,2284};const float tensor[3]={1,2,1};
    MwOriginalRigidBodyParameters p;
    assert(mw_original_rigid_body_parameters(1300,extent,tensor,&p));
    near(p.mass,1300);near(p.halfextent[0],.938f);assert(p.inertia[1]>p.inertia[0]);
    MwOriginalRigidBodyParameters old=p;
    assert(!mw_original_rigid_body_parameters(0,extent,tensor,&p));assert(!memcmp(&p,&old,sizeof(p)));
    const int16_t bad_extent[3]={0,621,2284};
    assert(!mw_original_rigid_body_parameters(1300,bad_extent,tensor,&p));assert(!memcmp(&p,&old,sizeof(p)));
    MwOriginalRigidBody s=body();s.force[0]=4;s.velocity[0]=1;
    assert(mw_original_rigid_body_integrate(&s,.25f));near(s.velocity[0],1.5f);near(s.position[0],.375f);
    /* Integration deliberately retains force; wrapper owns phase reset. */
    near(s.force[0],4);
    s=body();s.velocity[0]=400;
    assert(mw_original_rigid_body_integrate(&s,.25f));near(s.position[0],100);near(s.velocity[0],300);
    s=body();s.status=1;s.flags=2;s.local_cg[0]=1;
    const float force[3]={0,4,0},point[3]={2,0,0};bool wake=false;
    assert(mw_original_rigid_body_add_force(&s,force,point,&wake));assert(wake&&s.status==0&&s.flags==0x40);
    near(s.force[1],4);near(s.torque[2],4);
    assert(mw_original_rigid_body_integrate(&s,.25f));near(s.torque[2],1);
    /* Rotating around CG must preserve world CG apart from translation. */
    near(s.position[0]+s.orientation[0],1);near(s.position[1]+s.orientation[1],.125f);
    s=body();s.status=2;MwOriginalRigidBody before=s;wake=true;
    assert(mw_original_rigid_body_add_force(&s,force,point,&wake));assert(!wake&&!memcmp(&s,&before,sizeof(s)));
    s.velocity[0]=20;s.angular_velocity[2]=3;
    assert(mw_original_rigid_body_integrate(&s,.25f));near(s.velocity[0],0);near(s.angular_velocity[2],0);
    s=body();s.torque[1]=INFINITY;before=s;
    assert(!mw_original_rigid_body_integrate(&s,.1f));assert(!memcmp(&s,&before,sizeof(s)));
    s=body();before=s;const float bad[3]={NAN,0,0};wake=true;
    assert(!mw_original_rigid_body_add_force(&s,bad,point,&wake));assert(wake&&!memcmp(&s,&before,sizeof(s)));
    assert(!mw_original_rigid_body_integrate(&s,-1));assert(!memcmp(&s,&before,sizeof(s)));
    s=body();const float rotation[16]={-1,0,0,0,0,1,0,0,0,0,-1,0,0,0,0,1};
    assert(mw_original_rigid_body_set_orientation(&s,rotation));near(s.quaternion[1],1);near(s.quaternion[3],0);
    const float torque[3]={1,2,3};assert(mw_original_rigid_body_add_torque(&s,torque,&wake));near(s.torque[1],2);
    assert(mw_original_rigid_body_add_wrench(&s,force,torque,&wake));near(s.torque[1],4);near(s.force[1],4);
    s.status=2;assert(mw_original_rigid_body_raise_position(&s,.25f));near(s.position[1],.25f);assert(s.status==2);
    s=body();s.angular_velocity[1]=2;
    for(unsigned i=0;i<600;i++)assert(mw_original_rigid_body_integrate(&s,1.f/120));
    float norm=0;for(unsigned i=0;i<4;i++)norm+=s.quaternion[i]*s.quaternion[i];near(norm,1);
    float orthogonal=0;for(unsigned i=0;i<3;i++)orthogonal+=s.orientation[i]*s.orientation[4+i];near(orthogonal,0);
    puts("original rigid-body integration, force routing, CG, wake and transactional guards: PASS");return 0;
}
