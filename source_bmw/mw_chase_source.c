#include "mw_chase_source.h"
#include "mw_original_camera_direction.h"
#include <math.h>
#include <string.h>
static uint32_t word(const unsigned char *p){return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const unsigned char *p){uint32_t n=word(p);float f;memcpy(&f,&n,4);return f;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void tuning(const unsigned char *p,MwOriginalCameraTuning *out)
{
    for(unsigned i=0;i<4;i++)out->scalar[i]=real(p+i*4);
    for(unsigned i=0;i<10;i++)for(unsigned j=0;j<4;j++)out->vector[i][j]=real(p+16+i*16+j*4);
}
static void profile(const unsigned char *p,MwOriginalCameraProfile *out)
{
    for(unsigned i=0;i<2;i++){
        out->angle_degrees[i]=real(p+i*4);out->lag[i]=real(p+8+i*4);out->height[i]=real(p+16+i*4);
        out->lateral_offset[i]=real(p+24+i*4);out->fov_degrees[i]=real(p+32+i*4);out->stiffness[i]=real(p+40+i*4);out->tilting[i]=word(p+48+i*4);
    }
}
bool mw_chase_asset_open(MwChaseAsset *out,const void *data,size_t bytes)
{
    if(!out||!data||bytes<128||bytes>128*1024)return false;
    const unsigned char *p=data;uint32_t count=word(p+16),profiles=word(p+28),tunings=word(p+32);
    if(memcmp(p,"NCP1",4)||word(p+4)!=1||word(p+8)!=bytes||word(p+12)!=crc(p+16,bytes-16)||!count||count>128||word(p+20)!=128||word(p+24)!=48||profiles!=128+count*48||tunings!=profiles+count*7*56||word(p+36)!=56||word(p+40)!=7||word(p+44)!=176||bytes!=(uint64_t)tunings+7*352)return false;
    for(unsigned i=48;i<64;i++)if(p[i])return false;
    static const unsigned char dol_sha[32]={0x33,0xc5,0xea,0xe6,0x99,0xf8,0x71,0xbe,0xac,0x05,0x9b,0x69,0x32,0x47,0x5c,0xad,0x5e,0x9f,0x61,0x0b,0xb2,0xb2,0x29,0x8e,0x04,0x6d,0x04,0x37,0x57,0xb9,0x41,0x66};
    static const unsigned char attr_sha[32]={0x5b,0x69,0xc4,0x4f,0xfc,0xfc,0x70,0x13,0xa3,0xf2,0x49,0x00,0xb3,0x36,0x17,0x00,0x2b,0x1f,0x68,0xf2,0x48,0x4a,0x91,0x08,0xda,0xa5,0xbf,0xe5,0xd7,0x2a,0xd2,0x0c};
    if(memcmp(p+64,dol_sha,32)||memcmp(p+96,attr_sha,32))return false;
    uint32_t previous=0;
    for(unsigned i=0;i<count;i++){
        const unsigned char *r=p+128+i*48;uint32_t key=word(r);
        if(!key||(i&&key<=previous)||word(r+4)!=profiles+i*7*56||word(r+8)!=7||word(r+12))return false;
        previous=key;bool zero=false;
        for(unsigned c=16;c<48;c++){if(!r[c])zero=true;else if(zero||r[c]<32||r[c]>=127)return false;}
        if(!r[16]||!zero)return false;
        for(unsigned mode=0;mode<7;mode++){
            MwOriginalCameraProfile v;MwOriginalCameraProfileCache cache;profile(p+profiles+(i*7+mode)*56,&v);
            if(!mw_original_camera_profile_cache(&v,0,1,&cache)||!mw_original_camera_profile_cache(&v,3,1,&cache))return false;
        }
    }
    for(unsigned i=0;i<7*88;i++)if(!isfinite(real(p+tunings+i*4)))return false;
    for(unsigned mode=0;mode<7;mode++)for(unsigned sample=0;sample<2;sample++)for(unsigned a=0;a<3;a++)
        if(real(p+tunings+mode*352+sample*176+160+a*4)<0)return false;
    *out=(MwChaseAsset){.data=p,.bytes=bytes,.vehicles=count,.profiles_at=profiles,.tuning_at=tunings};return true;
}
bool mw_chase_asset_vehicle(const MwChaseAsset *asset,uint32_t ecar,unsigned mode,int view,float scale,MwChaseSourceConfig *out)
{
    if(!asset||!asset->data||!out||mode>=7)return false;
    uint32_t lo=0,hi=asset->vehicles;
    while(lo<hi){uint32_t mid=lo+(hi-lo)/2,key=word(asset->data+128+mid*48);if(key<ecar)lo=mid+1;else hi=mid;}
    if(lo>=asset->vehicles||word(asset->data+128+lo*48)!=ecar)return false;
    MwChaseSourceConfig c={.ecar_key=ecar,.mode=mode};profile(asset->data+asset->profiles_at+(lo*7+mode)*56,&c.profile);
    if(!mw_original_camera_profile_cache(&c.profile,view,scale,&c.cache))return false;
    tuning(asset->data+asset->tuning_at+mode*352,&c.lower);tuning(asset->data+asset->tuning_at+mode*352+176,&c.upper);*out=c;return true;
}
static bool blended(const MwChaseSourceConfig *c,float speed,MwOriginalCameraTuning *out)
{
    float parameter;if(!c||!mw_original_camera_tuning_parameter(speed,&parameter))return false;
    memset(out,0,sizeof(*out));return mw_original_camera_tuning_blend(&c->lower,&c->upper,parameter,out);
}
bool mw_chase_source_reset(MwChaseSourceMotion *out,const MwChaseSourceConfig *c,const float velocity[3],const float body[3],float speed)
{
    if(!out)return false;
    MwChaseSourceMotion m={0};MwOriginalCameraTuning sample;
    if(!blended(c,speed,&sample)||!mw_original_camera_direction_target(velocity,body,speed,m.direction,NULL))return false;
    for(unsigned a=0;a<3;a++){
        float duration=sample.vector[9][a];if(!isfinite(duration)||duration<0)return false;
        m.channel[a]=(MwOriginalCameraCubic){.value=m.direction[a],.target=m.direction[a],.cubic={0,0,0,m.direction[a]},.duration=duration,.mode=1};
    }
    m.initialized=true;*out=m;return true;
}
bool mw_chase_source_step(MwChaseSourceMotion *state,const MwChaseSourceConfig *c,const float velocity[3],const float body[3],float speed,float delta)
{
    if(!state||!state->initialized||!isfinite(delta)||delta<=0||delta>.1f)return false;
    MwChaseSourceMotion m=*state;MwOriginalCameraTuning sample;float target[3];
    if(!blended(c,speed,&sample)||!mw_original_camera_direction_target(velocity,body,speed,target,NULL))return false;
    for(unsigned a=0;a<3;a++){
        float duration=sample.vector[9][a];if(!isfinite(duration)||duration<0)return false;
        /* Matches the proven original update-before-target order. Controller
           +A4/+A8 duration biases and post-target attenuation are absent in the
           current native controller, explicitly zero rather than invented. */
        m.channel[a].duration=duration;
        if(!mw_original_camera_cubic_step(&m.channel[a],delta,0,0))return false;
        m.direction[a]=m.channel[a].value;
        if(!mw_original_camera_cubic_target(&m.channel[a],target[a]))return false;
    }
    *state=m;return true;
}
