#include "mw_race_session.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
int main(int argc,char **argv)
{
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);rewind(f);assert(n>128);
    unsigned char *raw=malloc((size_t)n);assert(raw&&fread(raw,1,(size_t)n,f)==(size_t)n);fclose(f);
    MwEventCatalog catalog;assert(mw_event_catalog_open(&catalog,raw,(size_t)n));
    MwAliasStore aliases={0};assert(mw_alias_create(&aliases,"Player"));
    uint32_t course_keys[512],sentinel=0xabcdef;size_t count=0;
    assert(mw_race_session_courses(&catalog,false,course_keys,512,&count)&&count==82);
    size_t localized=0;assert(mw_race_session_courses(&catalog,true,course_keys,512,&localized));
    for(size_t i=0;i<localized;i++){MwEventDefinition named;assert(mw_event_catalog_find(&catalog,course_keys[i],&named)&&*named.display_title);}
    assert(!mw_race_session_courses(&catalog,false,&sentinel,1,&count)&&count==82&&sentinel==0xabcdef);
    printf("%zu localized course candidates; ",localized);
    unsigned sessions=0,unsupported=0;
    for(uint32_t i=0;i<catalog.events;i++){
        MwEventDefinition event;assert(mw_event_catalog_get(&catalog,i,&event));MwRaceSession s={0};
        bool prepared=mw_race_session_prepare(&s,&catalog,event.key,&aliases,0x1234);
        if(!prepared){unsupported++;assert(s.phase==MW_SESSION_IDLE);continue;}
        sessions++;assert(s.alias_id==aliases.selected&&s.event_key==event.key&&s.source_start.key==event.start);
        assert(s.route.checkpoints==s.checkpoint_keys);assert(!mw_race_session_start(&s));
        assert(!mw_race_session_admit(&s,true,false,true));assert(!mw_race_session_admit(&s,true,true,false));
        assert(s.phase==MW_SESSION_LOADING);assert(mw_race_session_admit(&s,true,true,true));
        assert(mw_race_session_start(&s));assert(s.progress.route.checkpoints==s.checkpoint_keys);
        MwRaceSession before=s;assert(!mw_race_session_prepare(&s,&catalog,event.key,&aliases,0x1234));assert(!memcmp(&before,&s,sizeof(s)));
        assert(mw_race_session_tick(&s,1000000));assert(mw_race_session_pause(&s));assert(!mw_race_session_tick(&s,5000000));
        assert(mw_race_session_enter(&s,0x1234,s.checkpoint_keys[0])==MW_RACE_IGNORED);assert(mw_race_session_resume(&s));
        assert(mw_race_session_enter(&s,0x5678,s.checkpoint_keys[0])==MW_RACE_IGNORED);
        for(unsigned lap=0;lap<s.route.laps;lap++){
            assert(mw_race_session_enter(&s,0x1234,s.route.finish)==MW_RACE_IGNORED);
            for(size_t j=0;j<s.route.count;j++)assert(mw_race_session_enter(&s,0x1234,s.checkpoint_keys[j])==MW_RACE_CHECKPOINT);
            assert(mw_race_session_enter(&s,0x1234,s.route.finish)==(lap+1==s.route.laps?MW_RACE_FINISHED:MW_RACE_LAP));
        }
        assert(s.phase==MW_SESSION_FINISHED&&s.progress.elapsed_us==1000000);
        assert(!mw_race_session_tick(&s,1000));assert(mw_race_session_enter(&s,0x1234,s.route.finish)==MW_RACE_IGNORED);
        assert(mw_race_session_prepare(&s,&catalog,event.key,&aliases,0x1234));assert(mw_race_session_cancel(&s));
        assert(!mw_race_session_admit(&s,true,true,true));assert(!mw_race_session_start(&s));
    }
    assert(sessions>0&&unsupported>0);
    MwRaceSession empty={0},before=empty;MwAliasStore no_alias={0};
    assert(!mw_race_session_prepare(&empty,&catalog,0xc3309945,&no_alias,0x1234));assert(!memcmp(&empty,&before,sizeof(empty)));
    assert(!mw_race_session_prepare(&empty,&catalog,0xc3309945,&aliases,0));assert(!memcmp(&empty,&before,sizeof(empty)));
    printf("%u source-bound P2P/circuit session lifecycles pass; %u unsupported/incomplete definitions remain unavailable.\n",sessions,unsupported);
    free(raw);
}
