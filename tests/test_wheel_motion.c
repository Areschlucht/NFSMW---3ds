#include "wheel_motion.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint32_t word(const unsigned char *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
int main(int argc,char **argv)
{
    assert(argc==3);
    FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long size=ftell(f);rewind(f);
    unsigned char *raw=malloc((size_t)size);assert(raw);assert(fread(raw,1,(size_t)size,f)==(size_t)size);fclose(f);
    f=fopen(argv[2],"rb");assert(f);unsigned char header[32];assert(fread(header,1,32,f)==32);fclose(f);
    uint32_t batches=word(header+12),crc=word(header+24);WheelRig rig;
    assert(wheel_rig_decode(raw,(size_t)size,batches,crc,&rig));
    assert(rig.batches==28 && rig.wheels[0].front && !rig.wheels[1].front);
    WheelMotion motion;wheel_motion_reset(&motion);DriveState a={0},b={.z=.5f};
    assert(wheel_motion_update(&rig,&motion,&a,&b));
    for (unsigned i=0;i<4;++i) assert(fabsf(motion.angle[i]+.5f/rig.wheels[i].radius)<.00001f);
    assert(wheel_motion_update(&rig,&motion,&b,&a));
    for (unsigned i=0;i<4;++i) assert(fabsf(motion.angle[i])<.00001f);
    b=a;b.steering=.5f;b.speed=36;
    assert(wheel_motion_update(&rig,&motion,&a,&b)); /* No accepted travel = no spin. */
    for (unsigned i=0;i<4;++i) assert(fabsf(motion.angle[i])<.00001f);
    for (unsigned i=0;i<100000;++i) {
        a.z=i*.01f;b=a;b.z+=.01f;b.heading=6.2831853f-.0001f;
        assert(wheel_motion_update(&rig,&motion,&a,&b));
        assert(fabsf(motion.angle[0])<=6.2831853f);
    }
    WheelMotion unchanged=motion;b.x=NAN;
    assert(!wheel_motion_update(&rig,&motion,&a,&b));assert(!memcmp(&unchanged,&motion,sizeof(motion)));
    WheelMotion locked={.angle={1,2,3,4}},previous={.angle={.1f,.2f,.3f,.4f}};
    assert(wheel_motion_lock_rear(&rig,&previous,&locked));
    for (unsigned i=0;i<4;++i) assert(locked.angle[i]==(rig.wheels[i].front?(float)i+1:previous.angle[i]));
    previous.angle[0]=NAN;unchanged=locked;
    assert(!wheel_motion_lock_rear(&rig,&previous,&locked));assert(!memcmp(&unchanged,&locked,sizeof(locked)));
    wheel_motion_reset(&motion);for (unsigned i=0;i<4;++i) assert(motion.angle[i]==0);
    wheel_rig_free(&rig);wheel_rig_free(&rig);
    assert(!wheel_rig_decode(raw,(size_t)size,batches,crc^1,&rig));
    assert(!wheel_rig_decode(raw,(size_t)size,batches-1,crc,&rig));
    assert(!wheel_rig_decode(raw,(size_t)size-1,batches,crc,&rig));
    raw[size-1]^=1;assert(!wheel_rig_decode(raw,(size_t)size,batches,crc,&rig));
    free(raw);puts("Wheel checks passed: car/rig binding, forward/reverse rolling, blocked travel, angle wrapping, reset and corruption.");
    return 0;
}
