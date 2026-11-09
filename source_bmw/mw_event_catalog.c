#include "mw_event_catalog.h"
#include <math.h>
#include <string.h>
static uint32_t word(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const unsigned char *p){uint32_t bits=word(p);float f;memcpy(&f,&bits,4);return f;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static bool text_valid(const MwEventCatalog *c,uint32_t o){if(o>=c->strings||(o&&c->data[c->string_at+o-1]))return false;
    const unsigned char *p=c->data+c->string_at+o;for(size_t i=0;i<c->strings-o;i++){if(!p[i])return true;if(p[i]<32||p[i]>126)return false;}return false;}
bool mw_event_catalog_node(const MwEventCatalog *c,uint32_t key,MwEventNode *out)
{
    if(!c||!c->data||!out||!key)return false;
    uint32_t lo=0,hi=c->nodes;
    while(lo<hi){uint32_t m=lo+(hi-lo)/2,k=word(c->data+c->node_at+(size_t)m*40);if(k<key)lo=m+1;else hi=m;}
    if(lo==c->nodes)return false;
    const unsigned char *p=c->data+c->node_at+(size_t)lo*40;if(word(p)!=key)return false;
    MwEventNode n={.key=key,.present=word(p+4)};
    for(unsigned i=0;i<3;i++){n.position[i]=real(p+8+i*4);n.dimensions[i]=real(p+24+i*4);}n.rotation=real(p+20);n.radius=real(p+36);*out=n;return true;
}
bool mw_event_catalog_get(const MwEventCatalog *c,uint32_t index,MwEventDefinition *out)
{
    if(!c||!c->data||!out||index>=c->events)return false;
    const unsigned char *p=c->data+c->event_at+(size_t)index*64;
    MwEventDefinition e={.key=word(p),.laps=word(p+12),.first=word(p+16),.count=word(p+20),.start=word(p+24),.finish=word(p+28)};
    uint32_t type_bits=word(p+44);memcpy(&e.original_type,&type_bits,4);
    e.name=(const char*)c->data+c->string_at+word(p+4);e.region=(const char*)c->data+c->string_at+word(p+8);
    e.intro_movie=(const char*)c->data+c->string_at+word(p+32);e.outro_movie=(const char*)c->data+c->string_at+word(p+36);e.source_id=(const char*)c->data+c->string_at+word(p+40);*out=e;return true;
}
bool mw_event_catalog_find(const MwEventCatalog *c,uint32_t key,MwEventDefinition *out)
{
    if(!c||!c->data)return false;
    uint32_t lo=0,hi=c->events;
    while(lo<hi){uint32_t m=lo+(hi-lo)/2,k=word(c->data+c->event_at+(size_t)m*64);if(k<key)lo=m+1;else hi=m;}
    return lo<c->events&&word(c->data+c->event_at+(size_t)lo*64)==key&&mw_event_catalog_get(c,lo,out);
}
bool mw_event_catalog_open(MwEventCatalog *out,const void *data,size_t bytes)
{
    if(!out||!data||bytes<128||bytes>4*1024*1024)return false;
    const unsigned char *p=data;
    if(memcmp(p,"NRE1",4)||word(p+4)!=2||word(p+8)!=bytes||word(p+12)!=crc(p+16,bytes-16))return false;
    MwEventCatalog c={.data=p,.bytes=bytes,.events=word(p+16),.nodes=word(p+20),.refs=word(p+24),.strings=word(p+28),.event_at=word(p+32),.node_at=word(p+36),.ref_at=word(p+40),.string_at=word(p+44)};
    if(!c.events||c.events>4096||c.nodes>65536||c.refs>65536||!c.strings||c.event_at!=128||c.node_at!=128+(uint64_t)c.events*64||c.ref_at!=c.node_at+(uint64_t)c.nodes*40||c.string_at!=c.ref_at+(uint64_t)c.refs*4||bytes!=c.string_at+(uint64_t)c.strings)return false;
    for(unsigned i=48;i<64;i++)if(p[i])return false;
    if(p[c.string_at]||p[bytes-1])return false;
    uint32_t previous=0;
    for(uint32_t i=0;i<c.nodes;i++){
        const unsigned char *n=p+c.node_at+(size_t)i*40;uint32_t key=word(n),mask=word(n+4);
        if(!key||key<=previous||(mask&~15u))return false;
        previous=key;
        for(unsigned j=0;j<8;j++)if(!isfinite(real(n+8+j*4)))return false;
        for(unsigned j=0;j<3;j++)if((!(mask&1u)&&word(n+8+j*4))||(!(mask&4u)&&word(n+24+j*4)))return false;
        if((!(mask&2u)&&word(n+20))||(!(mask&8u)&&word(n+36)))return false;
    }
    previous=0;uint32_t next=0;MwEventNode node;
    for(uint32_t i=0;i<c.events;i++){
        const unsigned char *e=p+c.event_at+(size_t)i*64;uint32_t key=word(e),first=word(e+16),count=word(e+20);
        if(!key||key<=previous||first!=next||count>c.refs-next)return false;
        previous=key;next+=count;
        if(word(e+44)>10&&word(e+44)!=UINT32_MAX)return false;
        for(unsigned j=48;j<64;j++)if(e[j])return false;
        const unsigned offsets[]={4,8,32,36,40};for(unsigned j=0;j<5;j++)if(!text_valid(&c,word(e+offsets[j])))return false;
        for(unsigned j=24;j<=28;j+=4)if(word(e+j)&&!mw_event_catalog_node(&c,word(e+j),&node))return false;
    }
    if(next!=c.refs)return false;
    for(uint32_t i=0;i<c.refs;i++)if(!mw_event_catalog_node(&c,word(p+c.ref_at+(size_t)i*4),&node))return false;
    *out=c;return true;
}
bool mw_event_catalog_route(const MwEventCatalog *c,uint32_t key,uint32_t *keys,size_t capacity,MwRaceRoute *out)
{
    MwEventDefinition e;if(!out||!mw_event_catalog_find(c,key,&e)||!e.laps||!e.finish||!e.count||e.count>1024||e.count>capacity||!keys)return false;
    for(uint32_t i=0;i<e.count;i++)keys[i]=word(c->data+c->ref_at+(size_t)(e.first+i)*4);
    *out=(MwRaceRoute){.checkpoints=keys,.count=e.count,.finish=e.finish,.laps=e.laps};return true;
}
bool mw_event_catalog_tutorial(const MwEventCatalog *c,uint32_t key,uint32_t flags,MwStoryTutorial *out)
{
    MwEventDefinition e;
    return mw_event_catalog_find(c,key,&e)&&mw_story_tutorial_select(e.original_type,flags,out);
}
