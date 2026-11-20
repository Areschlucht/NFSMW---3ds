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
    puts("physical compound actor, primitive preparation, world geometry and transactional rejection: PASS");return 0;
}
