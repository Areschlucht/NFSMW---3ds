#include "mw_breakables.h"
#include <math.h>
#include <string.h>
static uint32_t word(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const unsigned char *p){uint32_t b=word(p);float f;memcpy(&f,&b,4);return f;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
bool mw_breakables_get(const MwBreakables *v,uint32_t index,MwBreakable *out)
{
    if(!v||!v->data||!out||index>=v->count)return false;
    const unsigned char *p=v->data+160+(size_t)index*128;
    MwBreakable b={.source_instance_offset=word(p),.source_parameter_offset=word(p+4),.member=word(p+8),.attribute_key=word(p+12),.logical_section=word(p+16),.original_flags=word(p+20),
        .blueprint_key=word(p+24),.dynamic_collision_key=word(p+28),.mass=real(p+32),.source_scalar_be71dbad=real(p+36),.source_bool_1f989f01=word(p+40),.source_bool_6f002423=word(p+44),.event_sequencer_key=word(p+112)};
    for(unsigned i=0;i<6;i++)b.bounds_viewer[i]=real(p+48+i*4);
    for(unsigned i=0;i<3;i++)b.translation_viewer[i]=real(p+72+i*4);
    *out=b;return true;
}
bool mw_breakables_open(MwBreakables *out,const void *data,size_t bytes)
{
    if(!out||!data||bytes<160||bytes>8*1024*1024)return false;
    const unsigned char *p=data;
    if(memcmp(p,"NBP1",4)||word(p+4)!=1||word(p+8)!=bytes||word(p+12)!=crc(p+16,bytes-16))return false;
    MwBreakables v={.data=p,.bytes=bytes,.count=word(p+16),.grid_at=word(p+28),.refs_at=word(p+32),.min_x=real(p+36),.min_z=real(p+40),.cell=real(p+44),.columns=word(p+48),.rows=word(p+52),.refs=word(p+56),.state_count=word(p+60)};
    uint64_t cells=(uint64_t)v.columns*v.rows;
    if(!v.count||v.count>32768||word(p+20)!=128||word(p+24)!=160||!v.state_count||v.state_count>65536||
       !v.columns||!v.rows||cells>65536||!isfinite(v.min_x)||!isfinite(v.min_z)||!isfinite(v.cell)||v.cell<=0||
       v.grid_at!=160+(uint64_t)v.count*128||v.refs_at!=v.grid_at+(cells+1)*4||v.refs>1048576||bytes!=v.refs_at+(uint64_t)v.refs*4)return false;
    uint32_t previous=0;
    for(uint32_t i=0;i<v.count;i++){
        MwBreakable b;mw_breakables_get(&v,i,&b);const unsigned char *r=p+160+(size_t)i*128;
        if(!b.source_instance_offset||(i&&b.source_instance_offset<=previous)||!b.source_parameter_offset||b.member>=v.state_count||!b.attribute_key||
           b.logical_section>65535||!isfinite(b.mass)||b.mass<=0||!isfinite(b.source_scalar_be71dbad)||b.source_bool_1f989f01>1||b.source_bool_6f002423>1)return false;
        previous=b.source_instance_offset;
        for(unsigned a=0;a<3;a++)if(!isfinite(b.bounds_viewer[a])||!isfinite(b.bounds_viewer[a+3])||b.bounds_viewer[a]>b.bounds_viewer[a+3]||!isfinite(b.translation_viewer[a]))return false;
        for(unsigned a=0;a<4;a++)if(!isfinite(real(r+84+a*4)))return false;
        if(word(r+116)||word(r+120)||word(r+124))return false;
    }
    if(word(p+v.grid_at)||word(p+v.grid_at+cells*4)!=v.refs)return false;
    for(uint32_t cell=0;cell<cells;cell++){
        uint32_t first=word(p+v.grid_at+cell*4),end=word(p+v.grid_at+(cell+1)*4),last=0;
        if(first>end||end>v.refs)return false;
        for(uint32_t i=first;i<end;i++){
            uint32_t index=word(p+v.refs_at+(size_t)i*4);
            if(index>=v.count||(i>first&&index<=last))return false;
            last=index;
        }
    }
    *out=v;return true;
}
bool mw_breakables_find(const MwBreakables *v,uint32_t source,uint32_t *index)
{
    if(!v||!v->data||!index)return false;
    uint32_t lo=0,hi=v->count;
    while(lo<hi){uint32_t m=lo+(hi-lo)/2,key=word(v->data+160+(size_t)m*128);if(key<source)lo=m+1;else hi=m;}
    if(lo==v->count||word(v->data+160+(size_t)lo*128)!=source)return false;
    *index=lo;return true;
}
bool mw_breakables_reset(const MwBreakables *v,unsigned char *states,size_t capacity)
{if(!v||!v->data||!states||capacity<v->state_count)return false;memset(states,0,v->state_count);return true;}
bool mw_breakables_activate(const MwBreakables *v,unsigned char *states,size_t capacity,uint32_t index)
{
    MwBreakable b;if(!states||!v||capacity<v->state_count||!mw_breakables_get(v,index,&b)||states[b.member])return false;
    states[b.member]=1;return true;
}
bool mw_breakables_active(const MwBreakables *v,const unsigned char *states,size_t capacity,uint32_t source)
{
    uint32_t index;MwBreakable b;
    return v&&states&&capacity>=v->state_count&&mw_breakables_find(v,source,&index)&&mw_breakables_get(v,index,&b)&&states[b.member]!=0;
}
static bool segment(const MwBreakable *b,const float a[3],const float c[3],float radius,double *fraction)
{
    double first=0,end=1;
    for(unsigned i=0;i<3;i++){
        double d=(double)c[i]-a[i],low=(double)b->bounds_viewer[i]-radius,high=(double)b->bounds_viewer[i+3]+radius;
        if(d==0){if(a[i]<low||a[i]>high)return false;continue;}
        double near=(low-a[i])/d,far=(high-a[i])/d;
        if(near>far){double t=near;near=far;far=t;}
        if(near>first)first=near;
        if(far<end)end=far;
        if(first>end)return false;
    }
    if(first>1||end<0)return false;
    *fraction=first;return true;
}
bool mw_breakables_sweep(const MwBreakables *v,const unsigned char *states,size_t capacity,
    const float from[3],const float to[3],float radius,MwBreakableAdmitted admitted,void *context,MwBreakableHit *hit)
{
    if(!v||!v->data||!states||capacity<v->state_count||!from||!to||!hit||!isfinite(radius)||radius<0)return false;
    bool moved=false;for(unsigned i=0;i<3;i++){if(!isfinite(from[i])||!isfinite(to[i]))return false;moved|=from[i]!=to[i];}
    if(!moved)return false;
    double lowx=fmin((double)from[0],to[0])-radius,highx=fmax((double)from[0],to[0])+radius;
    double lowz=fmin((double)from[2],to[2])-radius,highz=fmax((double)from[2],to[2])+radius;
    double x0=floor((lowx-v->min_x)/v->cell),x1=floor((highx-v->min_x)/v->cell),z0=floor((lowz-v->min_z)/v->cell),z1=floor((highz-v->min_z)/v->cell);
    if(x1<0||z1<0||x0>=v->columns||z0>=v->rows)return false;
    unsigned ax=(unsigned)fmax(0,x0),bx=(unsigned)fmin(v->columns-1,x1),az=(unsigned)fmax(0,z0),bz=(unsigned)fmin(v->rows-1,z1);
    if((uint64_t)(bx-ax+1)*(bz-az+1)>4096)return false;
    MwBreakableHit closest={0};bool found=false;
    for(unsigned z=az;z<=bz;z++)for(unsigned x=ax;x<=bx;x++){
        unsigned cell=z*v->columns+x;uint32_t first=word(v->data+v->grid_at+cell*4),end=word(v->data+v->grid_at+(cell+1)*4);
        for(uint32_t j=first;j<end;j++){
            uint32_t index=word(v->data+v->refs_at+(size_t)j*4);MwBreakable b;double fraction;
            if(!mw_breakables_get(v,index,&b)||states[b.member])continue;
            if(admitted?!admitted(context,b.source_instance_offset,b.original_flags):(b.original_flags&16)!=0)continue;
            if(!segment(&b,from,to,radius,&fraction)||(found&&(fraction>closest.fraction||(fraction==closest.fraction&&index>=closest.index))))continue;
            closest=(MwBreakableHit){.index=index,.source_instance_offset=b.source_instance_offset,.member=b.member,.fraction=fraction};
            for(unsigned a=0;a<3;a++)closest.point_viewer[a]=(float)((double)from[a]+((double)to[a]-from[a])*fraction);
            found=true;
        }
    }
    if(found)*hit=closest;
    return found;
}
