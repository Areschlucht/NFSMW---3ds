#include "mw_career.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void *load(const char *path,size_t *bytes){FILE *f=fopen(path,"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0);rewind(f);void *p=malloc((size_t)n);assert(p&&fread(p,1,(size_t)n,f)==(size_t)n);assert(!fclose(f));*bytes=(size_t)n;return p;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void put(unsigned char *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
static void media(MwCareer *s,const MwCareerPack *p)
{
    unsigned count=0;
    while(s->phase==MW_CAREER_INTRO_MOVIE||s->phase==MW_CAREER_INTRO_NIS){assert(++count<=2);assert(mw_career_media(s,p)&&*mw_career_media(s,p));assert(mw_career_media_finished(s,p));}
    assert(s->phase==MW_CAREER_RACING);
}
int main(int argc,char **argv)
{
    assert(argc==2);size_t bytes;unsigned char *raw=load(argv[1],&bytes);MwCareerPack p;assert(mw_career_pack_open(&p,raw,bytes));
    const uint32_t keys[]={0x42938ce2,0xd348f2cd,0x6ddd8383,0x9f60a40e,0xf7e4440a};
    for(unsigned i=0;i<5;i++){MwCareerStage stage;assert(mw_career_stage(&p,i,&stage)&&stage.event==keys[i]&&stage.reward==(i>=1&&i<=3?10000u:0u));}
    MwCareerTrigger trigger;assert(mw_career_trigger_get(&p,0x40caf8c1,&trigger)&&trigger.present&1u);assert(mw_career_trigger_get(&p,0xf73bbbcb,&trigger)&&trigger.present&1u);assert(!mw_career_trigger_get(&p,0,&trigger));
    MwCareer s;assert(mw_career_start(&s,&p,71)&&s.cash_known&&!s.cash&&!s.owned_car&&!s.step);assert(!strcmp(mw_career_media(&s,&p),"storyfmv_rac01"));
    assert(!mw_career_purchase(&s,&p));media(&s,&p);
    assert(!mw_career_race_result(&s,&p,keys[0],true));assert(!mw_career_call_started(&s));assert(!mw_career_trigger_enter(&s,&p,0xf73bbbcb));
    assert(mw_career_trigger_enter(&s,&p,0x40caf8c1));assert(!mw_career_trigger_enter(&s,&p,0x40caf8c1));assert(mw_career_tick(&s,&p,50000000)&&s.step==0);
    assert(mw_career_call_started(&s)&&s.timer_us==8000000);assert(!mw_career_call_started(&s));
    assert(mw_career_tick(&s,&p,7999999)&&s.timer_us==1&&!(s.flags&MW_CAREER_FORCE_AI));
    unsigned char save[128],bad[128];assert(mw_career_save(&s,&p,save,sizeof(save)));MwCareer resumed;assert(mw_career_load(&resumed,&p,71,save,sizeof(save))&&resumed.timer_us==1&&resumed.step==0);
    MwCareer impossible=resumed;impossible.flags=MW_CAREER_FORCE_AI;assert(!mw_career_save(&impossible,&p,bad,sizeof(bad)));impossible=resumed;impossible.timer_us=0;assert(!mw_career_save(&impossible,&p,bad,sizeof(bad)));
    assert(mw_career_tick(&s,&p,1)&&s.flags&MW_CAREER_FORCE_AI&&s.timer_us==3000000);assert(mw_career_tick(&s,&p,2999999)&&s.step==0);assert(mw_career_tick(&s,&p,1)&&s.step==1&&!s.cash);
    for(unsigned i=1;i<=3;i++){
        assert(s.step==i);media(&s,&p);MwCareer unchanged=s;
        assert(!mw_career_race_result(&s,&p,keys[i],false)&&!memcmp(&s,&unchanged,sizeof(s)));assert(!mw_career_race_result(&s,&p,keys[0],true));
        assert(mw_career_race_result(&s,&p,keys[i],true)&&s.cash==i*10000);assert(!mw_career_race_result(&s,&p,keys[i],true));
    }
    assert(s.step==3&&s.phase==MW_CAREER_OUTRO_NIS&&!strcmp(mw_career_media(&s,&p),"EndingNis03"));
    assert(mw_career_media_finished(&s,&p)&&s.step==4);assert(!strcmp(mw_career_media(&s,&p),"storyfmv_pin11"));media(&s,&p);
    assert(!mw_career_race_result(&s,&p,keys[4],true));assert(!mw_career_engine_blown(&s));assert(mw_career_trigger_enter(&s,&p,0xf73bbbcb));assert(s.flags==MW_CAREER_SABOTAGE);assert(mw_career_tick(&s,&p,2000000)&&s.phase==MW_CAREER_RACING);
    assert(mw_career_engine_blown(&s)&&!mw_career_engine_blown(&s));assert(mw_career_tick(&s,&p,999999)&&s.phase==MW_CAREER_RACING);assert(mw_career_tick(&s,&p,1)&&s.phase==MW_CAREER_OUTRO_MOVIE&&!strcmp(mw_career_media(&s,&p),"storyfmv_bus12"));
    assert(mw_career_media_finished(&s,&p)&&s.step==5&&s.phase==MW_CAREER_CAR_CHOICE&&s.cash==30000&&!s.owned_car);
    assert(mw_career_select_car(&s,&p,0x79054b53)&&!mw_career_purchase(&s,&p)&&!s.owned_car&&s.cash==30000);
    assert(mw_career_select_car(&s,&p,0x5a784095)&&mw_career_purchase(&s,&p)&&s.owned_car==0x5a784095&&s.phase==MW_CAREER_FREE_ROAM&&s.cash==4000);assert(!mw_career_purchase(&s,&p));
    assert(mw_career_save(&s,&p,save,sizeof(save)));assert(mw_career_load(&resumed,&p,71,save,sizeof(save))&&resumed.owned_car==s.owned_car&&resumed.cash==s.cash);
    MwCareer sentinel=resumed;
    assert(!mw_career_load(&resumed,&p,72,save,sizeof(save))&&!memcmp(&resumed,&sentinel,sizeof(resumed)));
    for(unsigned i=0;i<128;i++)for(unsigned bit=0;bit<8;bit++){memcpy(bad,save,128);bad[i]^=1u<<bit;assert(!mw_career_load(&resumed,&p,71,bad,128));assert(!memcmp(&resumed,&sentinel,sizeof(resumed)));}
    memcpy(bad,save,128);put(bad+24,MW_CAREER_RACING);put(bad+12,crc(bad+16,112));assert(!mw_career_load(&resumed,&p,71,bad,128));
    MwCareerPack before=p;raw[bytes-1]^=1;assert(!mw_career_pack_open(&p,raw,bytes)&&!memcmp(&p,&before,sizeof(p)));
    free(raw);puts("Opening career: source five-stage order, media/NIS, partial8s+3s, finalengine-loss1s, three once-only10000 wins, authentic affordable car purchase and1024 save corruptions passed.");
    return 0;
}
