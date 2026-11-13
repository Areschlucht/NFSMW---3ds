#include "mw_career.h"
#include <math.h>
#include <string.h>
static uint32_t word(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void put(unsigned char *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
static float real(const unsigned char *p){uint32_t v=word(p);float f;memcpy(&f,&v,4);return f;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static const char *string(const MwCareerPack *p,uint32_t at)
{
    if(at>=p->string_bytes)return NULL;
    const unsigned char *s=p->data+p->string_at+at;
    for(uint32_t i=at;i<p->string_bytes;i++){
        unsigned c=p->data[p->string_at+i];if(!c)return (const char*)s;
        if(c<32||c>126)return NULL;
    }
    return NULL;
}
bool mw_career_stage(const MwCareerPack *p,unsigned i,MwCareerStage *out)
{
    if(!p||!p->data||!out||i>=5)return false;
    const unsigned char *r=p->data+p->stage_at+i*64;
    *out=(MwCareerStage){.event=word(r),.flags=word(r+4),.linked_event=word(r+8),
        .intro_movie=string(p,word(r+12)),.outro_movie=string(p,word(r+16)),
        .intro_nis=string(p,word(r+20)),.outro_nis=string(p,word(r+24)),
        .trigger=word(r+28),.preset=string(p,word(r+32)),.reward=word(r+36)};
    return true;
}
bool mw_career_car(const MwCareerPack *p,unsigned i,MwCareerCar *out)
{
    if(!p||!p->data||!out||i>=4)return false;
    const unsigned char *r=p->data+p->car_at+i*64;
    *out=(MwCareerCar){.key=word(r),.cost=word(r+4),.source_unlock=word(r+8),.model=string(p,word(r+12))};return true;
}
bool mw_career_trigger_get(const MwCareerPack *p,uint32_t key,MwCareerTrigger *out)
{
    if(!p||!p->data||!out)return false;
    for(unsigned i=0;i<2;i++){
        const unsigned char *r=p->data+p->trigger_at+i*64;if(word(r)!=key)continue;
        MwCareerTrigger t={.key=key,.present=word(r+4),.rotation=real(r+20),.radius=real(r+36),.width=real(r+40)};
        for(unsigned a=0;a<3;a++){t.position[a]=real(r+8+a*4);t.dimensions[a]=real(r+24+a*4);}*out=t;return true;
    }
    return false;
}
bool mw_career_pack_open(MwCareerPack *out,const void *data,size_t bytes)
{
    if(!out||!data||bytes<865||bytes>65536)return false;
    const unsigned char *r=data;
    if(memcmp(r,"NFC1",4)||word(r+4)!=1||word(r+8)!=bytes||word(r+12)!=crc(r+16,bytes-16)||word(r+16)!=5||word(r+20)!=4||word(r+24)!=2||word(r+28)!=160||word(r+32)!=480||word(r+36)!=736||word(r+40)!=864||word(r+44)!=bytes-864)return false;
    for(unsigned i=48;i<64;i++)if(r[i])return false;
    if(r[864])return false;
    MwCareerPack p={.data=r,.bytes=bytes,.stage_at=160,.car_at=480,.trigger_at=736,.string_at=864,.string_bytes=(uint32_t)bytes-864};
    static const uint32_t events[]={0x42938ce2,0xd348f2cd,0x6ddd8383,0x9f60a40e,0xf7e4440a};
    for(unsigned i=0;i<5;i++){
        MwCareerStage s;mw_career_stage(&p,i,&s);
        if(s.event!=events[i]||s.flags!=(i==0?1u:i==4?2u:0u)||!s.intro_movie||!s.outro_movie||!s.intro_nis||!s.outro_nis||!s.preset||strcmp(s.preset,"M3GTRCAREERSTART"))return false;
        if(s.trigger!=(i==0?0x40caf8c1u:i==4?0xf73bbbcbu:0u))return false;
        if(s.reward!=(i>=1&&i<=3?10000u:0u))return false;
        for(unsigned b=40;b<64;b++)if(r[p.stage_at+i*64+b])return false;
    }
    for(unsigned i=0;i<4;i++){
        MwCareerCar c;mw_career_car(&p,i,&c);if(!c.key||!c.cost||c.cost>10000000||c.source_unlock!=16||!c.model||!*c.model)return false;
        for(unsigned j=0;j<i;j++){MwCareerCar other;mw_career_car(&p,j,&other);if(other.key==c.key)return false;}
        for(unsigned b=16;b<64;b++)if(r[p.car_at+i*64+b])return false;
    }
    for(unsigned i=0;i<2;i++){
        uint32_t key=word(r+p.trigger_at+i*64);MwCareerTrigger t;
        if(key!=(i?0xf73bbbcbu:0x40caf8c1u)||!mw_career_trigger_get(&p,key,&t)||(t.present&1u)==0||t.present>31||!isfinite(t.rotation)||!isfinite(t.radius)||t.radius<0||!isfinite(t.width)||t.width<0)return false;
        for(unsigned a=0;a<3;a++)if(!isfinite(t.position[a])||!isfinite(t.dimensions[a])||t.dimensions[a]<0)return false;
        if(!(t.present&8u)&&((t.present&6u)!=6u)&&((t.present&18u)!=18u||t.width<=0))return false;
        for(unsigned b=44;b<64;b++)if(r[p.trigger_at+i*64+b])return false;
    }
    *out=p;return true;
}
static bool car_exists(const MwCareerPack *p,uint32_t key,MwCareerCar *out)
{
    for(unsigned i=0;i<4;i++){MwCareerCar c;if(mw_career_car(p,i,&c)&&c.key==key){if(out)*out=c;return true;}}return false;
}
static bool valid(const MwCareer *s,const MwCareerPack *p)
{
    if(!s||!p||!p->data||!s->alias_id||s->step>5||s->phase<MW_CAREER_INTRO_MOVIE||s->phase>MW_CAREER_FREE_ROAM||s->flags>31)return false;
    if((s->step==5)!=(s->phase>=MW_CAREER_CAR_CHOICE)||(!s->cash_known&&s->cash))return false;
    if(s->phase<MW_CAREER_CAR_CHOICE&&s->selected_car)return false;
    if(s->selected_car&&!car_exists(p,s->selected_car,NULL))return false;
    if(s->phase==MW_CAREER_FREE_ROAM){if(!s->cash_known||!s->owned_car||s->owned_car!=s->selected_car)return false;}
    else if(s->owned_car)return false;
    if(s->flags&&s->phase!=MW_CAREER_RACING)return false;
    if(s->step==0){
        if(s->flags!=0&&s->flags!=1&&s->flags!=3&&s->flags!=7)return false;
        if(s->flags>=3&&!s->timer_us)return false;
        if(s->flags==7&&s->timer_us>3000000)return false;
    }
    else if(s->step==4){
        if(s->flags!=0&&s->flags!=8&&s->flags!=24)return false;
        if(s->flags==24&&(!s->timer_us||s->timer_us>1000000))return false;
    }
    else if(s->flags)return false;
    if(s->timer_us&&(s->phase!=MW_CAREER_RACING||s->timer_us>8000000||!((s->step==0&&(s->flags&MW_CAREER_CALL_STARTED))||(s->step==4&&(s->flags&MW_CAREER_ENGINE_BLOWN)))))return false;
    return true;
}
static void begin(MwCareer *s,const MwCareerPack *p)
{
    s->flags=0;s->timer_us=0;
    if(s->step==5){s->phase=MW_CAREER_CAR_CHOICE;return;}
    MwCareerStage stage;mw_career_stage(p,s->step,&stage);
    s->phase=*stage.intro_movie?MW_CAREER_INTRO_MOVIE:*stage.intro_nis?MW_CAREER_INTRO_NIS:MW_CAREER_RACING;
}
bool mw_career_start(MwCareer *out,const MwCareerPack *p,uint32_t alias)
{
    if(!out||!p||!p->data||!alias)return false;
    MwCareer s={.alias_id=alias,.cash_known=true};begin(&s,p);*out=s;return true;
}
const char *mw_career_media(const MwCareer *s,const MwCareerPack *p)
{
    if(!valid(s,p)||s->step>=5)return NULL;
    MwCareerStage stage;mw_career_stage(p,s->step,&stage);
    return s->phase==MW_CAREER_INTRO_MOVIE?stage.intro_movie:s->phase==MW_CAREER_INTRO_NIS?stage.intro_nis:s->phase==MW_CAREER_OUTRO_NIS?stage.outro_nis:s->phase==MW_CAREER_OUTRO_MOVIE?stage.outro_movie:NULL;
}
static void post(MwCareer *s,const MwCareerPack *p)
{
    MwCareerStage stage;mw_career_stage(p,s->step,&stage);s->timer_us=0;s->flags=0;
    if(*stage.outro_nis)s->phase=MW_CAREER_OUTRO_NIS;
    else if(*stage.outro_movie)s->phase=MW_CAREER_OUTRO_MOVIE;
    else {s->step++;begin(s,p);}
}
bool mw_career_media_finished(MwCareer *s,const MwCareerPack *p)
{
    if(!valid(s,p)||s->step>=5)return false;
    MwCareerStage stage;mw_career_stage(p,s->step,&stage);
    if(s->phase==MW_CAREER_INTRO_MOVIE)s->phase=*stage.intro_nis?MW_CAREER_INTRO_NIS:MW_CAREER_RACING;
    else if(s->phase==MW_CAREER_INTRO_NIS)s->phase=MW_CAREER_RACING;
    else if(s->phase==MW_CAREER_OUTRO_NIS){if(*stage.outro_movie)s->phase=MW_CAREER_OUTRO_MOVIE;else{s->step++;begin(s,p);}}
    else if(s->phase==MW_CAREER_OUTRO_MOVIE){s->step++;begin(s,p);}
    else return false;
    return true;
}
bool mw_career_race_result(MwCareer *s,const MwCareerPack *p,uint32_t event,bool won)
{
    if(!valid(s,p)||s->phase!=MW_CAREER_RACING||s->step<1||s->step>3||!won)return false;
    MwCareerStage stage;mw_career_stage(p,s->step,&stage);if(event!=stage.event)return false;
    if(!s->cash_known)return false;
    s->cash+=stage.reward;post(s,p);return true;
}
bool mw_career_retry(MwCareer *s,const MwCareerPack *p)
{if(!valid(s,p)||s->step>=5)return false;begin(s,p);return true;}
bool mw_career_trigger_enter(MwCareer *s,const MwCareerPack *p,uint32_t trigger)
{
    if(!valid(s,p)||s->phase!=MW_CAREER_RACING||s->step>=5)return false;
    MwCareerStage stage;mw_career_stage(p,s->step,&stage);if(!trigger||trigger!=stage.trigger||s->flags)return false;
    s->flags=s->step==0?MW_CAREER_CALL_REQUEST:MW_CAREER_SABOTAGE;return true;
}
bool mw_career_call_started(MwCareer *s)
{
    if(!s||s->phase!=MW_CAREER_RACING||s->step||s->flags!=MW_CAREER_CALL_REQUEST)return false;
    s->flags|=MW_CAREER_CALL_STARTED;s->timer_us=8000000;return true;
}
bool mw_career_engine_blown(MwCareer *s)
{
    if(!s||s->phase!=MW_CAREER_RACING||s->step!=4||s->flags!=MW_CAREER_SABOTAGE)return false;
    s->flags|=MW_CAREER_ENGINE_BLOWN;s->timer_us=1000000;return true;
}
bool mw_career_tick(MwCareer *s,const MwCareerPack *p,uint64_t delta)
{
    if(!valid(s,p))return false;
    if(!s->timer_us)return true;
    for(unsigned i=0;i<2&&s->timer_us;i++){
        if(delta<s->timer_us){s->timer_us-=delta;return true;}
        delta-=s->timer_us;s->timer_us=0;
        if(s->step==0&&!(s->flags&MW_CAREER_FORCE_AI)){s->flags|=MW_CAREER_FORCE_AI;s->timer_us=3000000;}
        else post(s,p);
    }
    return true;
}
bool mw_career_select_car(MwCareer *s,const MwCareerPack *p,uint32_t key)
{if(!valid(s,p)||s->phase!=MW_CAREER_CAR_CHOICE||!car_exists(p,key,NULL))return false;s->selected_car=key;return true;}
bool mw_career_set_wallet(MwCareer *s,uint32_t cash)
{if(!s||!s->alias_id||s->phase==MW_CAREER_INACTIVE)return false;s->cash=cash;s->cash_known=true;return true;}
bool mw_career_purchase(MwCareer *s,const MwCareerPack *p)
{
    MwCareerCar car;if(!valid(s,p)||s->phase!=MW_CAREER_CAR_CHOICE||!s->cash_known||!car_exists(p,s->selected_car,&car)||s->cash<car.cost)return false;
    s->cash-=car.cost;s->owned_car=s->selected_car;s->phase=MW_CAREER_FREE_ROAM;return true;
}
bool mw_career_save(const MwCareer *s,const MwCareerPack *p,void *out,size_t bytes)
{
    if(!valid(s,p)||!out||bytes!=128)return false;
    unsigned char r[128]={0};memcpy(r,"NCS1",4);put(r+4,1);put(r+8,128);
    put(r+16,s->alias_id);put(r+20,s->step);put(r+24,(uint32_t)s->phase);put(r+28,s->flags);put(r+32,s->selected_car);put(r+36,s->owned_car);put(r+40,s->cash);put(r+44,s->cash_known);put(r+48,(uint32_t)s->timer_us);put(r+52,(uint32_t)(s->timer_us>>32));put(r+56,word(p->data+12));memcpy(r+64,p->data+64,32);put(r+12,crc(r+16,112));memcpy(out,r,128);return true;
}
bool mw_career_load(MwCareer *out,const MwCareerPack *p,uint32_t alias,const void *data,size_t bytes)
{
    if(!out||!p||!p->data||!data||bytes!=128||!alias)return false;
    const unsigned char *r=data;
    if(memcmp(r,"NCS1",4)||word(r+4)!=1||word(r+8)!=128||word(r+12)!=crc(r+16,112)||word(r+16)!=alias||word(r+44)>1||word(r+56)!=word(p->data+12)||word(r+60)||memcmp(r+64,p->data+64,32))return false;
    for(unsigned i=96;i<128;i++)if(r[i])return false;
    MwCareer s={.alias_id=alias,.step=word(r+20),.phase=(MwCareerPhase)word(r+24),.flags=word(r+28),.selected_car=word(r+32),.owned_car=word(r+36),.cash=word(r+40),.cash_known=word(r+44)!=0,.timer_us=(uint64_t)word(r+48)|(uint64_t)word(r+52)<<32};
    if(!valid(&s,p))return false;
    *out=s;return true;
}
