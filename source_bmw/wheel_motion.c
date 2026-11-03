#include "wheel_motion.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
static uint32_t word(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static float real(const uint8_t *p)
{ uint32_t u=word(p);float f;memcpy(&f,&u,4);return f; }
static uint32_t crc32(const uint8_t *data,size_t size)
{
    uint32_t crc=0xffffffff;
    for (size_t i=0;i<size;++i) {
        crc^=data[i];
        for (unsigned b=0;b<8;++b) crc=(crc>>1)^((0-(crc&1))&0xedb88320);
    }
    return ~crc;
}
void wheel_rig_free(WheelRig *rig)
{ if (rig) { free(rig->groups);memset(rig,0,sizeof(*rig)); } }
bool wheel_rig_decode(const uint8_t *data,size_t size,uint32_t batches,uint32_t body_crc,WheelRig *out)
{
    if (!out) return false;
    memset(out,0,sizeof(*out));
    if (!data || size<32 || memcmp(data,"NWA1",4) || word(data+4)!=1 || word(data+8)!=4 ||
        word(data+12)!=batches || !batches || batches>2048 || word(data+24)!=body_crc || word(data+28)) return false;
    uint32_t bytes=96+batches*4;
    if (word(data+16)!=bytes || size-32!=bytes || crc32(data+32,bytes)!=word(data+20)) return false;
    WheelRig rig={.batches=batches};unsigned fronts=0,seen=0;
    for (unsigned i=0;i<4;++i) {
        const uint8_t *p=data+32+i*24;
        for (unsigned a=0;a<3;++a) {
            rig.wheels[i].pivot[a]=real(p+a*4);
            if (!isfinite(rig.wheels[i].pivot[a]) || fabsf(rig.wheels[i].pivot[a])>1.01f) return false;
        }
        rig.wheels[i].radius=real(p+12);
        if (!isfinite(rig.wheels[i].radius) || rig.wheels[i].radius<=.1f || rig.wheels[i].radius>=1 || word(p+16)>1 || word(p+20)) return false;
        rig.wheels[i].front=word(p+16)!=0;fronts+=rig.wheels[i].front;
    }
    if (fronts!=2) return false;
    rig.groups=malloc(batches);
    if (!rig.groups) return false;
    for (uint32_t i=0;i<batches;++i) {
        uint32_t group=word(data+128+i*4);
        if (group>4) { wheel_rig_free(&rig);return false; }
        rig.groups[i]=(uint8_t)group;seen|=1u<<group;
    }
    if (seen!=31) { wheel_rig_free(&rig);return false; }
    *out=rig;return true;
}
void wheel_motion_reset(WheelMotion *motion)
{ if (motion) memset(motion,0,sizeof(*motion)); }
bool wheel_motion_lock_rear(const WheelRig *rig,const WheelMotion *previous,WheelMotion *next)
{
    if (!rig || !previous || !next) return false;
    for (unsigned i=0;i<4;++i) if (!isfinite(previous->angle[i]) || !isfinite(next->angle[i])) return false;
    for (unsigned i=0;i<4;++i) if (!rig->wheels[i].front) next->angle[i]=previous->angle[i];
    return true;
}
bool wheel_motion_update(const WheelRig *rig,WheelMotion *motion,const DriveState *previous,const DriveState *next)
{
    if (!rig || !motion || !previous || !next || !isfinite(previous->x) || !isfinite(previous->z) ||
        !isfinite(next->x) || !isfinite(next->z) || !isfinite(next->heading)) return false;
    float distance=(next->x-previous->x)*sinf(next->heading)+(next->z-previous->z)*cosf(next->heading);
    WheelMotion candidate=*motion;
    for (unsigned i=0;i<4;++i) {
        float radius=rig->wheels[i].radius;
        if (!isfinite(radius) || radius<=.1f || radius>=1 || !isfinite(motion->angle[i])) return false;
        candidate.angle[i]=fmodf(motion->angle[i]-distance/radius,6.2831853f);
        if (!isfinite(candidate.angle[i])) return false;
    }
    *motion=candidate;return true;
}
