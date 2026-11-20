#include "mw_vehicle_world.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static void put16(unsigned char *p,unsigned x){p[0]=(unsigned char)x;p[1]=(unsigned char)(x>>8);}
static void put32(unsigned char *p,uint32_t x){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(x>>(8*i));}
static void putf(unsigned char *p,float x){uint32_t u;memcpy(&u,&x,4);put32(p,u);}
static void bound(unsigned char *p,unsigned flags,unsigned children)
{
    put16(p+6,32767);put16(p+14,flags);put16(p+16,1000);put16(p+18,500);put16(p+20,2000);
    p[22]=(unsigned char)children;p[23]=255;put16(p+30,children?1:65535);putf(p+32,.5f);
}
static void near(float x,float y){assert(fabsf(x-y)<.0001f);}
int main(void)
{
    unsigned char pack[176]={0};put32(pack,0x12345678);put32(pack+4,3);
    bound(pack+16,64,2);bound(pack+64,66,0);bound(pack+112,130,0);put16(pack+64+8,1000);
    const float pad[3]={0,0,0};MwVehicleWorldActor a;
    assert(mw_vehicle_world_actor_open(pack,sizeof(pack),0x12345678,pad,&a)==0);assert(a.count==2);
    assert(a.primitives[0].kind==1&&a.primitives[1].kind==2);
    MwOriginalRigidBody s={0};s.quaternion[3]=1;for(unsigned i=0;i<4;i++)s.orientation[i*5]=1;
    s.position[0]=100;s.position[1]=2;MwVehicleWorldGeometry g;
    assert(!mw_vehicle_world_geometry(&a,0,&s,&g));
    assert(mw_vehicle_world_prepare(&a,&s));s.position[0]=103;
    assert(mw_vehicle_world_geometry(&a,0,&s,&g));near(g.position[0],104);near(g.delta[0],3);near(g.dimension[2],2);
    near(g.normal[0][0],1);near(g.extent[1][1],.5f);near(g.overlap,-100000);
    assert(mw_vehicle_world_geometry(&a,1,&s,&g));near(g.dimension[0],.5f);near(g.position[3],1);
    MwVehicleWorldGeometry old=g;s.position[0]=NAN;
    assert(!mw_vehicle_world_geometry(&a,0,&s,&g));assert(!memcmp(&g,&old,sizeof(g)));
    MwVehicleWorldActor before=a;pack[8]=1;
    assert(mw_vehicle_world_actor_open(pack,sizeof(pack),0x12345678,pad,&a)<0);assert(!memcmp(&a,&before,sizeof(a)));
    MwBodyCollisionState response={0};response.inertia[0]=100;response.inertia[1]=200;response.inertia[2]=300;
    response.local_cg[1]=.5f;response.extra_normal_accumulation=.25f;
    const float forward[3]={0,0,1},velocity[3]={0,0,20},normal[3]={0,0,-1},scale[3]={1,.4f,2};
    MwBodyCollisionState npc=response;
    assert(mw_vehicle_world_modify_collision(&response,true,forward,velocity,normal,scale));
    near(response.inertia[1],1800);near(response.local_cg[1],0);near(response.extra_normal_accumulation,0);near(response.moment_scale[1],.4f);
    assert(mw_vehicle_world_modify_collision(&npc,false,forward,velocity,normal,scale));
    near(npc.inertia[1],200);near(npc.local_cg[1],0);near(npc.extra_normal_accumulation,.25f);
    MwBodyCollisionState saved=response;float bad[3]={NAN,0,1};
    assert(!mw_vehicle_world_modify_collision(&response,true,bad,velocity,normal,scale));assert(!memcmp(&response,&saved,sizeof(saved)));
    MwVehicleWorldGeometry box={0};box.shape=1;box.overlap=-100000;
    box.position[1]=1;box.position[2]=.1f;
    for(unsigned i=0;i<3;i++){box.dimension[i]=.5f;box.normal[i][i]=1;box.extent[i][i]=.5f;}
    WorldCollisionBarrier barrier={0};barrier.endpoint_native[0][0]=-5;barrier.endpoint_native[0][1]=3;
    barrier.endpoint_native[1][0]=5;barrier.endpoint_native[1][1]=-1;barrier.inverse_local_length=.1f;barrier.flags=16;
    barrier.material_key=0x1234;barrier.source_ci_offset=0x4567;MwVehicleWorldContact contact;
    assert(mw_vehicle_world_wall_contact(&box,&barrier,0,false,&contact)==1);
    assert(contact.material_key==0x1234&&contact.source_ci_offset==0x4567);assert(contact.penetration>=0);
    old=box;MwVehicleWorldContact previous=contact;
    assert(mw_vehicle_world_wall_contact(&box,&barrier,16,false,&contact)==0);
    assert(!memcmp(&box,&old,sizeof(box))&&!memcmp(&contact,&previous,sizeof(contact)));
    barrier.endpoint_native[0][0]=NAN;
    assert(mw_vehicle_world_wall_contact(&box,&barrier,0,false,&contact)<0);
    assert(!memcmp(&box,&old,sizeof(box))&&!memcmp(&contact,&previous,sizeof(contact)));
    puts("physical compound, primitive geometry, original wall contacts and vehicle collision modifier: PASS");return 0;
}
