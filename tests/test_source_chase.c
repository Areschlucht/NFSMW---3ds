#include "chase_camera.h"
#include "mw_original_camera_direction.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void put32(unsigned char *p,uint32_t v){for(unsigned j=0;j<4;j++)p[j]=(unsigned char)(v>>(j*8));}
int main(int argc,char **argv)
{
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>128);rewind(f);
    unsigned char *data=malloc((size_t)n),*bad=malloc((size_t)n);assert(data&&bad&&fread(data,1,(size_t)n,f)==(size_t)n);assert(!fclose(f));
    MwChaseAsset a;assert(mw_chase_asset_open(&a,data,(size_t)n)&&a.vehicles==5);
    const uint32_t cars[]={0x4e085fb3,0x5a784095,0x79054b53,0x5bff2fb0,0xa6ee7a11};unsigned cases=0;
    const float still[]={0,0,0},forward[]={0,0,1};
    for(unsigned car=0;car<5;car++)for(unsigned mode=0;mode<7;mode++){
        MwChaseSourceConfig c;assert(mw_chase_asset_vehicle(&a,cars[car],mode,0,1,&c));assert(c.ecar_key==cars[car]&&c.mode==mode);
        MwChaseSourceMotion m;assert(mw_chase_source_reset(&m,&c,still,forward,0));
        for(unsigned axis=0;axis<3;axis++)assert(m.direction[axis]==forward[axis]&&m.channel[axis].mode==1);
        for(unsigned step=0;step<8;step++)assert(mw_chase_source_step(&m,&c,still,forward,0,1.f/60));
        for(unsigned axis=0;axis<3;axis++)assert(m.direction[axis]==forward[axis]);
        cases++;
    }
    MwChaseSourceConfig c;assert(mw_chase_asset_vehicle(&a,cars[0],3,0,1,&c));assert(c.cache.fov_turns==16384&&fabsf(c.cache.lag+5.436f)<.00001f&&fabsf(c.cache.height-1.7f)<.00001f);
    MwChaseSourceConfig split;assert(mw_chase_asset_vehicle(&a,cars[0],3,3,1,&split));assert(fabsf(split.cache.lag+8.2f)<.00001f&&split.cache.profile_index==1);
    MwChaseSourceMotion m;assert(mw_chase_source_reset(&m,&c,still,forward,0));const float turned[]={1,0,0};
    assert(mw_chase_source_step(&m,&c,still,turned,0,1.f/60));assert(m.direction[0]==0&&m.direction[2]==1);
    assert(mw_chase_source_step(&m,&c,still,turned,0,1.f/60));assert(m.direction[0]>0&&m.direction[0]<1&&m.direction[2]<1);
    float drifting[]={10,0,20},expected[3];assert(mw_original_camera_direction_target(drifting,forward,hypotf(10,20),expected,NULL));
    for(unsigned i=0;i<600;i++)assert(mw_chase_source_step(&m,&c,drifting,forward,hypotf(10,20),1.f/60));
    for(unsigned axis=0;axis<3;axis++)assert(fabsf(m.direction[axis]-expected[axis])<.00001f);
    float reverse[]={0,0,-20};for(unsigned i=0;i<600;i++)assert(mw_chase_source_step(&m,&c,reverse,forward,20,1.f/60));assert(m.direction[2]>.999f);
    MwChaseSourceMotion unchanged=m;assert(!mw_chase_source_step(&m,&c,reverse,forward,20,NAN));assert(!mw_chase_source_step(&m,&c,reverse,forward,20,.2f));assert(!mw_chase_source_step(&m,&c,reverse,forward,-1,.01f));assert(!memcmp(&m,&unchanged,sizeof m));
    DriveState car={.speed=20,.lateral_speed=10};ChaseCamera camera;assert(chase_reset(&camera,&car,0));assert(chase_bind_source(&camera,&a,cars[0],3,0));
    for(unsigned i=0;i<300;i++){car.z+=20.f/60;car.x+=10.f/60;assert(chase_step(&camera,&car,0,1.f/60));}
    assert(fabsf(camera.heading-atan2f(10,20))<.0001f&&isfinite(camera.eye[0])&&camera.target[2]>car.z);
    ChaseCamera before=camera;assert(!chase_bind_source(&camera,&a,0xdeadbeef,3,0));assert(!chase_bind_source(&camera,&a,cars[0],7,0));assert(!memcmp(&camera,&before,sizeof camera));
    assert(chase_reset(&camera,&car,0)&&!camera.source_bound);
    memcpy(bad,data,(size_t)n);bad[n-1]^=1;MwChaseAsset untouched=a;assert(!mw_chase_asset_open(&a,bad,(size_t)n));assert(!memcmp(&a,&untouched,sizeof a));
    memcpy(bad,data,(size_t)n);put32(bad+untouched.profiles_at,0x7f800000);put32(bad+12,crc(bad+16,(size_t)n-16));assert(!mw_chase_asset_open(&a,bad,(size_t)n));
    memcpy(bad,data,(size_t)n);put32(bad+128+4,1);put32(bad+12,crc(bad+16,(size_t)n-16));assert(!mw_chase_asset_open(&a,bad,(size_t)n));
    assert(!mw_chase_asset_open(&a,data,(size_t)n-1));assert(!mw_chase_asset_open(&a,data,(size_t)n+1));
    free(data);free(bad);printf("source chase: %u vehicle/mode bindings, original direction/cubic timing, drift/reverse, reset and corrupt sidecars passed\n",cases);return 0;
}
