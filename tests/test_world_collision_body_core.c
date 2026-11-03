#include "mw_body_collision_response.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <string.h>
static uint32_t bits(float value){uint32_t u;memcpy(&u,&value,4);return u;}
static MwBodyCollisionState state(void){
    MwBodyCollisionState s={0};s.mass=2;
    for(unsigned k=0;k<3;k++){s.inertia[k]=2;s.moment_scale[k]=1;}
    for(unsigned k=0;k<4;k++)s.orientation[k*5]=1;
    s.velocity[0]=-10;s.velocity[1]=1;return s;
}
int main(void){
    MwBodyCollisionState s=state(),saved=s;
    MwBodyCollisionInput c={{0,0,1},{1,0,0},{.3f,.55f},16};
    MwBodyCollisionResponse r;
    /* Original uploaded USA 80083C74, explicit synthetic producer inputs.
     * Off-center response demonstrates coupled angular/linear impulses. */
    assert(mw_body_collision_response(&s,&c,&r)==1);
    assert(r.velocity[0]==-5&&r.velocity[1]==.5f&&r.velocity[2]==0);
    assert(r.angular_velocity[0]==.5f&&r.angular_velocity[1]==5&&r.angular_velocity[2]==0);
    assert(r.initial_normal_velocity[0]==-10&&r.initial_normal_velocity[1]==0);
    assert(r.initial_tangent_velocity[0]==0&&r.initial_tangent_velocity[1]==1);
    assert(r.normal_impulse[0]==10&&r.friction_branch==1);
    assert(r.initial_friction_impulse[1]==-2);
    assert(memcmp(&s,&saved,sizeof s)==0);
    /* First iteration observes friction/contact statistics but applies no J. */
    c.passes=1;assert(mw_body_collision_response(&s,&c,&r)==1);
    assert(memcmp(r.velocity,s.velocity,sizeof s.velocity)==0);
    assert(r.normal_impulse[0]==0&&r.friction_branch==1&&r.iterations==1);
    /* Point at COM: original weighted 16-pass residual, not single bounce. */
    c.passes=16;c.point[2]=0;assert(mw_body_collision_response(&s,&c,&r)==1);
    assert(bits(r.velocity[0])==bits(-.00001239776611328125f));
    assert(bits(r.velocity[1])==bits(.000001132488250732421875f));
    assert(r.angular_velocity[0]==0&&r.angular_velocity[1]==0);
    /* Uniformly scaling mass and inertia preserves velocities, scales J. */
    MwBodyCollisionResponse first=r;s.mass=4;
    for(unsigned k=0;k<3;k++)s.inertia[k]=4;
    assert(mw_body_collision_response(&s,&c,&r)==1);
    assert(memcmp(r.velocity,first.velocity,sizeof r.velocity)==0);
    assert(r.normal_impulse[0]==first.normal_impulse[0]*2);
    /* Separating, zero-normal, frictionless, and sliding contacts. */
    s=state();s.velocity[0]=10;assert(mw_body_collision_response(&s,&c,&r)==0);
    assert(r.velocity[0]==10&&r.friction_branch==0);
    s=state();c.normal[0]=0;assert(mw_body_collision_response(&s,&c,&r)==0);
    c.normal[0]=2;c.friction[0]=0;c.friction[1]=0;
    assert(mw_body_collision_response(&s,&c,&r)==1&&r.friction_branch==2);
    assert(r.velocity[1]==1);
    c.friction[0]=.3f;c.friction[1]=.55f;s.velocity[1]=100;c.passes=1;
    assert(mw_body_collision_response(&s,&c,&r)==1&&r.friction_branch==2);
    assert(r.initial_friction_impulse[1]==-6);
    /* Explicit producer validation is transactional. */
    memset(&r,0x5a,sizeof r);first=r;s.mass=0;
    assert(mw_body_collision_response(&s,&c,&r)==-1&&memcmp(&first,&r,sizeof r)==0);
    s=state();s.orientation[0]=NAN;
    assert(mw_body_collision_response(&s,&c,&r)==-1&&memcmp(&first,&r,sizeof r)==0);
    s=state();c.passes=0;
    assert(mw_body_collision_response(&s,&c,&r)==-1&&memcmp(&first,&r,sizeof r)==0);
    return 0;
}
