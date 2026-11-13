#include "mw_breakables.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint32_t word(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void put(unsigned char *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(8*i));}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void reject(unsigned char *raw,size_t bytes,size_t offset,uint32_t value)
{
    unsigned char *bad=malloc(bytes);assert(bad);memcpy(bad,raw,bytes);put(bad+offset,value);put(bad+12,crc(bad+16,bytes-16));
    MwBreakables view={.bytes=123};assert(!mw_breakables_open(&view,bad,bytes)&&view.bytes==123);free(bad);
}
static bool only(void *context,uint32_t offset,uint32_t flags){(void)flags;return offset==*(uint32_t*)context;}
int main(int argc,char **argv)
{
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f&&!fseek(f,0,SEEK_END));long length=ftell(f);rewind(f);assert(length>160);
    size_t bytes=(size_t)length;unsigned char *data=malloc(bytes);assert(data&&fread(data,1,bytes,f)==bytes);assert(!fclose(f));
    MwBreakables v;assert(mw_breakables_open(&v,data,bytes)&&v.count==7419&&v.state_count==14307);
    unsigned char *states=malloc(v.state_count+16);assert(states);memset(states,0xa5,v.state_count+16);assert(mw_breakables_reset(&v,states,v.state_count));
    for(unsigned j=0;j<16;j++)assert(states[v.state_count+j]==0xa5);
    for(uint32_t i=0;i<v.count;i++){
        MwBreakable b;assert(mw_breakables_get(&v,i,&b));uint32_t index=UINT32_MAX;assert(mw_breakables_find(&v,b.source_instance_offset,&index)&&index==i);
        float a[3],c[3];for(unsigned axis=0;axis<3;axis++)a[axis]=c[axis]=(float)(((double)b.bounds_viewer[axis]+b.bounds_viewer[axis+3])*.5);
        a[0]=b.bounds_viewer[0]-1;c[0]=b.bounds_viewer[3]+1;
        MwBreakableHit hit;assert(mw_breakables_sweep(&v,states,v.state_count,a,c,0,only,&b.source_instance_offset,&hit));
        assert(hit.index==i&&hit.member==b.member&&hit.source_instance_offset==b.source_instance_offset&&hit.fraction>=0&&hit.fraction<=1);
    }
    uint32_t index;assert(mw_breakables_find(&v,24588704,&index));MwBreakable speed35;assert(mw_breakables_get(&v,index,&speed35));
    assert(speed35.member==5475&&speed35.attribute_key==0x014a1c7d&&speed35.logical_section==101);
    assert(mw_breakables_activate(&v,states,v.state_count,index));assert(!mw_breakables_activate(&v,states,v.state_count,index));
    assert(mw_breakables_active(&v,states,v.state_count,speed35.source_instance_offset));
    unsigned aliases=0;for(uint32_t i=0;i<v.count;i++){MwBreakable b;assert(mw_breakables_get(&v,i,&b));if(b.member==speed35.member){assert(mw_breakables_active(&v,states,v.state_count,b.source_instance_offset));aliases++;}}
    assert(aliases>0&&!mw_breakables_active(&v,states,v.state_count,0x12345678));
    assert(!mw_breakables_activate(&v,states,v.state_count-1,index));assert(!mw_breakables_reset(&v,states,v.state_count-1));
    MwBreakableHit untouched={.index=123},hit=untouched;float a[]={100000,0,100000},b[]={100001,0,100001};
    assert(!mw_breakables_sweep(&v,states,v.state_count,a,b,1,NULL,NULL,&hit)&&!memcmp(&hit,&untouched,sizeof hit));
    a[0]=NAN;assert(!mw_breakables_sweep(&v,states,v.state_count,a,b,1,NULL,NULL,&hit)&&!memcmp(&hit,&untouched,sizeof hit));
    a[0]=100000;assert(!mw_breakables_sweep(&v,states,v.state_count,a,a,1,NULL,NULL,&hit));
    assert(!mw_breakables_sweep(&v,states,v.state_count,a,b,-1,NULL,NULL,&hit));
    MwBreakables sentinel={.bytes=123};assert(!mw_breakables_open(&sentinel,data,bytes-1)&&sentinel.bytes==123);
    reject(data,bytes,20,64);reject(data,bytes,28,160);reject(data,bytes,48,0);
    reject(data,bytes,160+8,v.state_count);reject(data,bytes,160+12,0);reject(data,bytes,160+32,0x7fc00000);
    reject(data,bytes,160+40,2);reject(data,bytes,160+116,1);reject(data,bytes,v.refs_at,v.count);
    uint32_t gi=word(data+v.grid_at+4);reject(data,bytes,v.grid_at+4,v.refs+1);(void)gi;
    free(states);free(data);
    puts("7419 source prop bindings and spatial hits; exact Speed35 identity, shared activation, guards and malformed packs pass.");return 0;
}
