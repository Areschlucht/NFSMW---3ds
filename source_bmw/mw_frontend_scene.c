#include "mw_frontend_scene.h"
#include <math.h>
#include <string.h>
enum { HEADER=192,CAMERAS=18,CAMERA_BYTES=96,PLACEMENTS=5,PLACEMENT_BYTES=64,
       PLACE_AT=HEADER+CAMERAS*CAMERA_BYTES,TOTAL_BYTES=PLACE_AT+PLACEMENTS*PLACEMENT_BYTES };
static uint32_t word(const unsigned char *p){return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float number(const unsigned char *p){uint32_t u=word(p);float f;memcpy(&f,&u,4);return f;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static bool source(const unsigned char *p,const char *hex){
    for(unsigned i=0;i<32;i++){unsigned a=(unsigned char)hex[i*2],b=(unsigned char)hex[i*2+1];a=a>='a'?a-'a'+10:a-'0';b=b>='a'?b-'a'+10:b-'0';if(p[i]!=a*16+b)return false;}return true;
}
static bool name_valid(const unsigned char *p){
    unsigned n=0;for(;n<48&&p[n];n++)if(!((p[n]>='a'&&p[n]<='z')||(p[n]>='0'&&p[n]<='9')||p[n]=='_'))return false;
    if(!n||n==48)return false;
    for(;n<48;n++)if(p[n])return false;
    return true;
}
bool mw_frontend_scene_open(MwFrontendScenePack *out,const void *data,size_t bytes){
    if(!out||!data||bytes!=TOTAL_BYTES)return false;
    const unsigned char *p=data;
    if(memcmp(p,"NFP1",4)||word(p+4)!=1||word(p+8)!=bytes||word(p+12)!=crc(p+16,bytes-16)||
       word(p+16)!=CAMERAS||word(p+20)!=HEADER||word(p+24)!=CAMERA_BYTES||
       word(p+28)!=PLACEMENTS||word(p+32)!=PLACE_AT||word(p+36)!=PLACEMENT_BYTES)return false;
    static const char *const hashes[]={
        "33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166",
        "6ee16d55d92ad1b337a9b655989c32b2976f95e7c64e148cf83f482c613f79f7",
        "5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c",
        "adbb364d58f348ee95d2b59e99d0312b1bd8079d77be7bc76bd40461ee2cc9c2"};
    for(unsigned i=0;i<4;i++)if(!source(p+40+i*32,hashes[i]))return false;
    for(unsigned i=168;i<HEADER;i++)if(p[i])return false;
    for(unsigned i=0;i<CAMERAS;i++){
        const unsigned char *r=p+HEADER+i*CAMERA_BYTES;
        if(!name_valid(r)||!word(r+88)||word(r+92))return false;
        for(unsigned j=0;j<i;j++)if(!strcmp((const char*)r,(const char*)p+HEADER+j*CAMERA_BYTES)||word(r+88)==word(p+HEADER+j*CAMERA_BYTES+88))return false;
        for(unsigned k=0;k<10;k++)if(!isfinite(number(r+48+k*4)))return false;
        float fov=number(r+84),direction=0,up=0;
        if(fov<=1||fov>=179)return false;
        for(unsigned a=0;a<3;a++){float d=number(r+48+a*4)-number(r+60+a*4);direction+=d*d;float u=number(r+72+a*4);up+=u*u;}
        if(!(direction>0)||!isfinite(direction)||!(up>0)||!isfinite(up))return false;
    }
    for(unsigned i=0;i<PLACEMENTS;i++){
        const unsigned char *r=p+PLACE_AT+i*PLACEMENT_BYTES;
        if(word(r)!=i+1)return false;
        for(unsigned j=0;j<8;j++)if(!isfinite(number(r+4+j*4)))return false;
        for(unsigned j=36;j<PLACEMENT_BYTES;j++)if(r[j])return false;
    }
    *out=(MwFrontendScenePack){p,bytes};return true;
}
bool mw_frontend_scene_camera(const MwFrontendScenePack *p,const char *name,MwFrontendSceneCamera *out){
    if(!p||!p->data||p->bytes!=TOTAL_BYTES||!name||!out)return false;
    for(unsigned i=0;i<CAMERAS;i++){
        const unsigned char *r=p->data+HEADER+i*CAMERA_BYTES;
        if(strcmp((const char*)r,name))continue;
        MwFrontendSceneCamera c;
        for(unsigned a=0;a<3;a++){c.eye[a]=number(r+48+a*4);c.target[a]=number(r+60+a*4);c.up[a]=number(r+72+a*4);}
        c.fov_degrees=number(r+84);c.collection_key=word(r+88);*out=c;return true;
    }return false;
}
bool mw_frontend_scene_placement(const MwFrontendScenePack *p,uint32_t garage,MwFrontendScenePlacement *out){
    if(!p||!p->data||p->bytes!=TOTAL_BYTES||!garage||garage>PLACEMENTS||!out)return false;
    const unsigned char *r=p->data+PLACE_AT+(garage-1)*PLACEMENT_BYTES;MwFrontendScenePlacement v={.garage_type=garage};
    for(unsigned a=0;a<3;a++){v.geometry_position[a]=number(r+4+a*4);v.car_rotation_degrees[a]=number(r+20+a*4);}
    v.geometry_z_degrees=number(r+16);v.car_height_bias=number(r+32);*out=v;return true;
}
