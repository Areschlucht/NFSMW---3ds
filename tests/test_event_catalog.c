#include "mw_event_catalog.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned word(const unsigned char *p){return p[0]|(unsigned)p[1]<<8|(unsigned)p[2]<<16|(unsigned)p[3]<<24;}
static void put(unsigned char *p,unsigned v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
static unsigned crc(const unsigned char *p,size_t n){unsigned c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void reject(MwEventCatalog *old,unsigned char *bad,size_t n){MwEventCatalog before=*old;put(bad+12,crc(bad+16,n-16));assert(!mw_event_catalog_open(old,bad,n));assert(!memcmp(old,&before,sizeof(before)));}
int main(int argc,char **argv){
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);rewind(f);assert(n>128);unsigned char *raw=malloc((size_t)n),*bad=malloc((size_t)n);assert(raw&&bad);assert(fread(raw,1,(size_t)n,f)==(size_t)n);fclose(f);
    MwEventCatalog c={0};assert(mw_event_catalog_open(&c,raw,(size_t)n));assert(c.events==277&&c.nodes==2462&&c.refs==1990);
    MwEventDefinition e;assert(mw_event_catalog_find(&c,0xc3309945,&e));assert(!strcmp(e.name,"race_bin_10/10_2_1_sprint"));assert(e.count==9&&e.laps==1&&e.original_type==0);
    MwEventNode start;assert(mw_event_catalog_node(&c,e.start,&start));assert(start.present&1);assert(start.position[0]==1511.823974609375f);
    unsigned routes=0,keys_checked=0,tutorials=0;uint32_t keys[1024];
    for(uint32_t i=0;i<c.events;i++){
        assert(mw_event_catalog_get(&c,i,&e));MwRaceRoute route;MwStoryTutorial tutorial;
        assert(mw_event_catalog_tutorial(&c,e.key,0,&tutorial));
        if(tutorial.movie_stem){tutorials++;MwStoryTutorial repeated;assert(mw_event_catalog_tutorial(&c,e.key,tutorial.profile_flags,&repeated));assert(!repeated.movie_stem);}
        if(!mw_event_catalog_route(&c,e.key,keys,1024,&route))continue;
        MwRaceProgress race;assert(mw_race_begin(&race,&route));
        for(unsigned lap=0;lap<route.laps;lap++){
            for(size_t j=0;j<route.count;j++){assert(keys[j]==word(raw+c.ref_at+(e.first+j)*4));assert(mw_race_gate(&race,keys[j])==MW_RACE_CHECKPOINT);keys_checked++;}
            assert(mw_race_gate(&race,route.finish)==(lap+1==route.laps?MW_RACE_FINISHED:MW_RACE_LAP));
        }routes++;
    }
    assert(tutorials==113);
    const unsigned header_at[]={4,8,16,20,24,28,32,36,40,44,48};
    for(unsigned i=0;i<sizeof(header_at)/sizeof(*header_at);i++){memcpy(bad,raw,(size_t)n);put(bad+header_at[i],0xffffffffu);reject(&c,bad,(size_t)n);}
    const unsigned structural_at[]={c.node_at,c.node_at+4,c.node_at+8,c.ref_at,c.event_at,c.event_at+4,c.event_at+16,c.event_at+20,c.event_at+24,c.event_at+48};
    for(unsigned i=0;i<sizeof(structural_at)/sizeof(*structural_at);i++){memcpy(bad,raw,(size_t)n);put(bad+structural_at[i],0xffffffffu);reject(&c,bad,(size_t)n);}
    memcpy(bad,raw,(size_t)n);bad[n-1]='x';reject(&c,bad,(size_t)n);
    assert(!mw_event_catalog_open(&c,raw,(size_t)n-1));
    printf("Validated %u events, %u nodes, %u data-bound routes and %u ordered gate events, %u source tutorial selections; 23 malformed variants rejected.\n",c.events,c.nodes,routes,keys_checked,tutorials);
    free(bad);free(raw);
}
