#include "mw_free_roam.h"
#include <math.h>
#include <string.h>
static uint32_t word(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const unsigned char *p){uint32_t b=word(p);float f;memcpy(&f,&b,4);return f;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
bool mw_free_roam_get(const MwFreeRoam *view,uint32_t i,MwDestination *out)
{
    if(!view||!view->data||!out||i>=view->count)return false;
    const unsigned char *p=view->data+96+(size_t)i*64;
    MwDestination d={.key=word(p),.kind=word(p+4),.radius=real(p+20),.bin=word(p+24),.event=word(p+28),.respawn=word(p+32),.respawn_rotation=real(p+48),.frontend_mode=word(p+52)};
    for(unsigned a=0;a<3;a++){d.position[a]=real(p+8+a*4);d.respawn_position[a]=real(p+36+a*4);}*out=d;return true;
}
bool mw_free_roam_open(MwFreeRoam *out,const void *data,size_t bytes)
{
    if(!out||!data||bytes<96||bytes>512*1024)return false;
    const unsigned char *p=data;uint32_t count=word(p+16);
    if(memcmp(p,"NFD1",4)||word(p+4)!=1||word(p+8)!=bytes||word(p+12)!=crc(p+16,bytes-16)||!count||count>4096||word(p+20)!=96||word(p+24)!=64||word(p+28)||bytes!=96+(uint64_t)count*64)return false;
    MwFreeRoam view={.data=p,.bytes=bytes,.count=count};uint32_t previous=0;
    for(uint32_t i=0;i<count;i++){
        MwDestination d;mw_free_roam_get(&view,i,&d);
        if(!d.key||(i&&d.key<=previous)||d.kind<1||d.kind>4||d.bin>16||!isfinite(d.radius)||d.radius<=0||!isfinite(d.respawn_rotation))return false;
        previous=d.key;
        for(unsigned a=0;a<3;a++)if(!isfinite(d.position[a])||!isfinite(d.respawn_position[a]))return false;
        if(d.kind==MW_DEST_RACE){if(!d.event||d.respawn||d.frontend_mode)return false;}
        else if(!d.respawn||d.event||d.frontend_mode!=(d.kind==MW_DEST_SAFEHOUSE?2u:d.kind==MW_DEST_SHOP?3u:5u))return false;
        if(word(p+96+i*64+56)||word(p+96+i*64+60))return false;
    }
    *out=view;return true;
}
bool mw_free_roam_near(const MwFreeRoam *view,const float point[3],MwDestination *out)
{
    if(!view||!point||!out)return false;
    for(unsigned a=0;a<3;a++)if(!isfinite(point[a]))return false;
    bool found=false;double best=0;MwDestination nearest;
    for(uint32_t i=0;i<view->count;i++){
        MwDestination d;if(!mw_free_roam_get(view,i,&d))return false;
        double squared=0;for(unsigned a=0;a<3;a++){double x=(double)point[a]-d.position[a];squared+=x*x;}
        if(squared>(double)d.radius*d.radius||(found&&squared>=best))continue;
        nearest=d;best=squared;found=true;
    }
    if(found)*out=nearest;
    return found;
}
