#include "mw_nis_actor.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
#define MAX_BYTES (2u*1024u*1024u)
static uint32_t u32(const unsigned char *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint16_t u16(const unsigned char *p){return (uint16_t)(p[0]|((uint16_t)p[1]<<8));}
static float flt(const unsigned char*p){uint32_t v=u32(p);float f;memcpy(&f,&v,4);return f;}
static int read_at(MwNisActorBank*b,uint32_t off,void*out,uint32_t n){
    if(!b||off>b->file_size||n>b->file_size-off)return 0;
    if(b->data){memcpy(out,b->data+off,n);return 1;}
    return b->file&&fseek(b->file,(long)off,SEEK_SET)==0&&fread(out,1,n,b->file)==n;
}
void mw_nis_actor_close(MwNisActorBank*b){if(b){if(b->file)fclose(b->file);free(b->data);memset(b,0,sizeof(*b));}}
int mw_nis_actor_open(MwNisActorBank*b,const char*path){
    unsigned char h[32];long size;if(!b||!path)return 0;memset(b,0,sizeof(*b));
    b->file=fopen(path,"rb");if(!b->file)return 0;
    if(fseek(b->file,0,SEEK_END)||(size=ftell(b->file))<32||(unsigned long)size>MAX_BYTES)goto fail;
    b->file_size=(uint32_t)size;if(!read_at(b,0,h,32)||memcmp(h,"NNA1",4)||u32(h+4)!=1)goto fail;
    b->banks=u32(h+8);b->curves=u32(h+12);b->bank_offset=u32(h+16);b->curve_offset=u32(h+20);
    if(!b->banks||b->banks>8||!b->curves||b->curves>128||b->bank_offset!=32||b->curve_offset!=32+64*b->banks||u32(h+24)!=b->curve_offset+128*b->curves||u32(h+28)!=b->file_size||u32(h+24)>b->file_size)goto fail;
    b->data=(unsigned char*)malloc(b->file_size);if(!b->data)goto fail;
    if(fseek(b->file,0,SEEK_SET)||fread(b->data,1,b->file_size,b->file)!=b->file_size)goto fail;
    fclose(b->file);b->file=NULL;return 1;
fail:mw_nis_actor_close(b);return 0;
}
int mw_nis_actor_find_scene(MwNisActorBank*b,const char*name,MwNisActorScene*s){
    unsigned char r[64];uint32_t i;if(!b||!name||!s)return 0;
    for(i=0;i<b->banks;i++){
        if(!read_at(b,b->bank_offset+i*64,r,64)||!memchr(r,0,48))return 0;
        if(strcmp((const char*)r,name))continue;
        memset(s,0,sizeof(*s));memcpy(s->name,r,48);s->first_curve=u32(r+48);s->curve_count=u32(r+52);
        return s->first_curve<=b->curves&&s->curve_count<=b->curves-s->first_curve;
    }return 0;
}
int mw_nis_actor_find_curve(MwNisActorBank*b,const MwNisActorScene*s,const char*name,MwNisActorCurve*c){
    unsigned char r[128];uint32_t i,j,minimum;if(!b||!s||!name||!c||s->first_curve>b->curves||s->curve_count>b->curves-s->first_curve)return 0;
    minimum=b->curve_offset+b->curves*128;
    for(i=s->first_curve;i<s->first_curve+s->curve_count;i++){
        if(!read_at(b,b->curve_offset+i*128,r,128)||!memchr(r,0,64)||!memchr(r+64,0,32))return 0;
        if(strcmp((const char*)r,name))continue;
        memset(c,0,sizeof(*c));memcpy(c->name,r,64);memcpy(c->actor_token,r+64,32);
        c->frames=u32(r+96);c->channels=u32(r+100);c->data_offset=u32(r+104);c->context_rate=flt(r+108);
        for(j=0;j<4;j++)c->destination[j]=u16(r+112+j*2);
        c->kind=(MwNisActorKind)u32(r+120);
        return c->frames&&c->frames<=20000&&c->channels&&c->channels<=4&&isfinite(c->context_rate)&&c->context_rate>0&&c->context_rate<=240&&c->kind>=MW_NIS_ACTOR_TRANSLATION&&c->kind<=MW_NIS_ACTOR_SCALE&&c->data_offset>=minimum&&c->data_offset<=b->file_size&&c->frames*c->channels*8<=b->file_size-c->data_offset;
    }return 0;
}
int mw_nis_actor_sample(MwNisActorBank*b,const MwNisActorCurve*c,float time,int context,float*out,uint32_t count){
    unsigned char r[32];float t,a;uint32_t frame,i,n;
    if(!b||!c||!out||count<c->channels||!c->frames||!c->channels||c->channels>4||!isfinite(time))return 0;
    t=context?time*c->context_rate:time;if(!isfinite(t))return 0;
    if(t<0)t=0;
    if(t>(float)(c->frames-1))t=(float)(c->frames-1);
    frame=(uint32_t)t;a=t-(float)frame;n=c->channels*4;
    if(!read_at(b,c->data_offset+frame*n*2,r,n*2))return 0;
    for(i=0;i<c->channels;i++){
        float x=flt(r+4*i);out[i]=a==0?x:fmaf(a,flt(r+n+4*i),x);
        if(!isfinite(out[i]))return 0;
    }return 1;
}
