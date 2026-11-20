#include "mw_ginsu_bindings.h"
#include <math.h>
#include <string.h>
static uint32_t word(const unsigned char*p){return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const unsigned char*p){uint32_t u=word(p);float f;memcpy(&f,&u,4);return f;}
static uint32_t crc(const unsigned char*p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static bool text(const unsigned char*p,unsigned n,bool empty){unsigned i=0;for(;i<n&&p[i];i++)if(p[i]<32||p[i]>126||p[i]=='/'||p[i]=='\\')return false;if(i==n||(!i&&!empty))return false;for(;i<n;i++)if(p[i])return false;return true;}
bool mw_ginsu_binding_get(const MwGinsuBindings*b,uint32_t i,MwGinsuBinding*out){
 if(!b||!b->data||!out||i>=b->count)return false;
 const unsigned char*p=b->data+96+(size_t)i*192;
 *out=(MwGinsuBinding){.model=(const char*)p,.profile=(const char*)p+32,.accel=(const char*)p+80,.decel=(const char*)p+96,.engineaudio=(const char*)p+112,.physical_key=word(p+144),.engineaudio_key=word(p+148),.minimum_rpm=real(p+152),.maximum_rpm=real(p+156),.car_id=word(p+160),.master_volume=word(p+164),.accel_volume=word(p+168),.decel_volume=word(p+172),.decel_minimum_rpm=real(p+176),.decel_maximum_rpm=real(p+180),.flags=word(p+184)};return true;
}
bool mw_ginsu_bindings_open(MwGinsuBindings*out,const void*data,size_t bytes){
 if(!out||!data||bytes<288||bytes>96+256*192)return false;
 const unsigned char*p=data;uint32_t n=word(p+16);
 if(memcmp(p,"NGB1",4)||word(p+4)!=1||word(p+8)!=bytes||word(p+12)!=crc(p+16,bytes-16)||!n||n>256||bytes!=96+(size_t)n*192||word(p+20)!=96||word(p+24)!=192||word(p+28))return false;
 static const unsigned char attr[32]={91,105,196,79,252,252,112,19,163,242,73,0,179,54,23,0,43,31,104,242,72,74,145,8,218,165,191,229,215,42,210,12};
 const char *hex="33c5eae699f871beac059b6932475cad5e9f610bb2b2298e046d043757b94166";
 if(memcmp(p+32,attr,32))return false;
 for(unsigned j=0;j<32;j++){unsigned a=(unsigned char)hex[j*2],b=(unsigned char)hex[j*2+1];a=a>='a'?a-'a'+10:a-'0';b=b>='a'?b-'a'+10:b-'0';if(p[64+j]!=a*16+b)return false;}
 MwGinsuBindings v={p,bytes,n};
 for(uint32_t i=0;i<n;i++){
  const unsigned char*r=p+96+(size_t)i*192;MwGinsuBinding b;mw_ginsu_binding_get(&v,i,&b);
  if(!text(r,32,true)||!text(r+32,48,false)||!text(r+80,16,true)||!text(r+96,16,true)||!text(r+112,32,false)||!b.physical_key||!b.engineaudio_key||word(r+188)||b.flags&~7u)return false;
  if(!isfinite(b.minimum_rpm)||!isfinite(b.maximum_rpm)||!isfinite(b.decel_minimum_rpm)||!isfinite(b.decel_maximum_rpm))return false;
  if((bool)(b.flags&1)!=(*b.accel!=0)||(bool)(b.flags&2)!=(*b.decel!=0))return false;
  if((b.flags&4)&&(b.minimum_rpm<=0||b.maximum_rpm<=b.minimum_rpm))return false;
  if(i&&strcmp((const char*)r-192+32,b.profile)>=0)return false;
 }
 *out=v;return true;
}
bool mw_ginsu_binding_profile(const MwGinsuBindings*b,const char*profile,const char*model,MwGinsuBinding*out){
 if(!b||!profile||!out)return false;
 for(uint32_t i=0;i<b->count;i++){MwGinsuBinding v;if(!mw_ginsu_binding_get(b,i,&v))return false;if(!strcmp(v.profile,profile)&&(!model||!strcmp(v.model,model))){*out=v;return true;}}return false;
}
