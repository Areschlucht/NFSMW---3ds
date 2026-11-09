#include "mw_destination_icons.h"
#include <string.h>
static uint32_t word(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
bool mw_destination_icons_open(MwDestinationIcons *out,const void *data,size_t bytes)
{
    if(!out||!data||bytes!=4608)return false;
    const unsigned char *p=data;
    if(memcmp(p,"NFI1",4)||word(p+4)!=1||word(p+8)!=bytes||word(p+12)!=crc(p+96,bytes-96)||word(p+16)!=5||word(p+20)!=96||word(p+24)!=256||word(p+28)!=32)return false;
    static const unsigned char source_sha[32]={14,53,67,245,52,203,148,177,19,22,138,27,95,107,122,114,36,179,45,18,152,111,177,130,83,185,55,241,108,41,61,121};
    static const unsigned char dol_sha[32]={51,197,234,230,153,248,113,190,172,5,155,105,50,71,92,173,94,159,97,11,178,178,41,142,4,109,4,55,87,185,65,102};
    if(memcmp(p+64,source_sha,32)||memcmp(p+32,dol_sha,32))return false;
    static const uint32_t hashes[]={0x2cfd5273,0x1ce551d4,0x12bb8395,0x571cd206,0x25559384};
    size_t expected=256;
    for(unsigned i=0;i<5;i++){
        const unsigned char *r=p+96+i*32;unsigned side=i==3?8:16;
        uint32_t kind=i<3?i+1:4,type=i<3?UINT32_MAX:i-3;
        if(word(r)!=kind||word(r+4)!=type||word(r+8)!=hashes[i]||word(r+12)!=side||word(r+16)!=side||word(r+20)!=expected||word(r+24)!=side*side*4||word(r+28))return false;
        expected+=side*side*4;
    }
    if(expected!=bytes)return false;
    *out=(MwDestinationIcons){.data=p,.bytes=bytes};return true;
}
bool mw_destination_icon_find(const MwDestinationIcons *icons,unsigned kind,int32_t type,MwDestinationIcon *out)
{
    if(!icons||!icons->data||icons->bytes!=4608||!out)return false;
    unsigned index;
    if(kind>=1&&kind<=3)index=kind-1;
    else if(kind==4&&(type==0||type==1))index=3+(unsigned)type;
    else return false;
    const unsigned char *r=icons->data+96+index*32;
    *out=(MwDestinationIcon){.rgba=icons->data+word(r+20),.width=word(r+12),.height=word(r+16),.source_hash=word(r+8)};return true;
}
bool mw_destination_icon_blit(const MwDestinationIcons *icons,unsigned kind,int32_t type,unsigned char *rgb,size_t bytes,unsigned width,unsigned height,int x,int y)
{
    MwDestinationIcon icon;
    if(!rgb||!width||!height||width>4096||height>4096||(uint64_t)width*height*3>bytes||!mw_destination_icon_find(icons,kind,type,&icon))return false;
    int64_t left=(int64_t)x-icon.width/2,top=(int64_t)y-icon.height/2;
    for(unsigned j=0;j<icon.height;j++)for(unsigned i=0;i<icon.width;i++){
        int64_t px=left+i,py=top+j;
        if(px<0||py<0||(uint64_t)px>=width||(uint64_t)py>=height)continue;
        const unsigned char *source=icon.rgba+((size_t)j*icon.width+i)*4;
        unsigned char *target=rgb+((size_t)py*width+(size_t)px)*3;unsigned alpha=source[3];
        for(unsigned c=0;c<3;c++)target[c]=(unsigned char)((source[c]*alpha+target[c]*(255-alpha)+127)/255);
    }
    return true;
}
