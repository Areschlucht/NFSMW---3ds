#include "mw_world_state.h"
#include <string.h>
static uint32_t word(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
bool mw_world_state_open(MwWorldState *out,const void *data,size_t bytes)
{
    if(!out||!data||bytes<640||bytes>128*1024)return false;
    const unsigned char *p=data;
    uint32_t version=word(p+4);
    if(memcmp(p,"NWS1",4)||(version!=1&&version!=2)||word(p+8)!=bytes||word(p+12)!=crc(p+16,bytes-16))return false;
    MwWorldState s={.data=p,.bytes=bytes,.bin=word(p+16),.context=word(p+20),.count=word(p+24),.groups_at=word(p+28),.overrides_at=word(p+32),.version=version,.event=word(p+36)};
    if(s.bin<1||s.bin>16||s.context!=0x10||s.groups_at!=128||s.overrides_at!=640||s.count>10000||bytes!=640+(uint64_t)s.count*12)return false;
    if((version==1&&s.event)||(version==2&&!s.event))return false;
    for(unsigned i=40;i<64;i++)if(p[i])return false;
    if(p[128]&1u)return false;
    uint32_t previous=0;
    for(uint32_t i=0;i<s.count;i++){
        const unsigned char *r=p+640+i*12;uint32_t offset=word(r),original=word(r+4),effective=word(r+8);
        uint32_t changed=original^effective;
        if(!offset||(i&&offset<=previous)||!changed||(changed&~0x410u)||
           (version==1&&(changed!=0x10||!(original&0x10))))return false;
        previous=offset;
    }
    *out=s;return true;
}
bool mw_world_state_source_matches(const MwWorldState *s,const unsigned char sha[32])
{ return s&&s->data&&sha&&!memcmp(s->data+64,sha,32); }
bool mw_world_state_instance(void *context,uint32_t offset,uint32_t original,uint32_t *effective)
{
    const MwWorldState *s=context;if(!s||!s->data||!effective)return false;
    uint32_t lo=0,hi=s->count;
    while(lo<hi){uint32_t mid=lo+(hi-lo)/2,key=word(s->data+s->overrides_at+mid*12);if(key<offset)lo=mid+1;else hi=mid;}
    if(lo<s->count){const unsigned char *r=s->data+s->overrides_at+lo*12;if(word(r)==offset){if(word(r+4)!=original)return false;*effective=word(r+8);return true;}}
    *effective=original;return true;
}
int mw_world_state_group(void *context,uint16_t group)
{
    const MwWorldState *s=context;if(!s||!s->data||group>=4096)return -1;
    if(!group)return 1;
    return !!(s->data[s->groups_at+group/8]&(1u<<(group%8)));
}
