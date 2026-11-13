#include "mw_playable_race.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void *load(const char *path,size_t *bytes)
{
    FILE *f=fopen(path,"rb");assert(f&&fseek(f,0,SEEK_END)==0);long size=ftell(f);assert(size>128);rewind(f);
    void *p=malloc((size_t)size);assert(p&&fread(p,1,(size_t)size,f)==(size_t)size);assert(!fclose(f));*bytes=(size_t)size;return p;
}
static void close_to(double a,double b){assert(fabs(a-b)<.00001);}
static void word(unsigned char *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(8*i));}
static void real(unsigned char *p,float f){uint32_t b;memcpy(&b,&f,4);word(p,b);}
static uint32_t crc(const unsigned char *p,size_t n)
{
    uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;
}
static void fixture(unsigned char data[405],MwEventCatalog *catalog)
{
    memset(data,0,405);memcpy(data,"NRE1",4);word(data+4,3);word(data+8,405);
    const uint32_t header[]={1,5,3,1,128,192,392,404};for(unsigned i=0;i<8;i++)word(data+16+i*4,header[i]);
    word(data+128,100);word(data+128+12,1);word(data+128+20,3);word(data+128+24,1);word(data+128+28,5);
    for(unsigned i=0;i<5;i++){
        unsigned char *p=data+192+i*40;word(p,i+1);word(p+4,i?7:3);real(p+8,(float)i*10);
        if(i){real(p+24,2);real(p+28,10);real(p+32,3);}
    }
    word(data+392,2);word(data+396,3);word(data+400,4);word(data+12,crc(data+16,405-16));
    assert(mw_event_catalog_open(catalog,data,405));
}
static void native_policy(const MwAliasStore *aliases)
{
    unsigned char data[405];MwEventCatalog catalog;fixture(data,&catalog);
    MwRaceSession session={0};MwPlayableRace race={0};MwPlayableRaceUpdate update;
    float position[]={0,0,0};
    assert(mw_playable_race_prepare(&race,&session,&catalog,100,aliases,1,0));
    assert(mw_playable_race_admit(&race,true,true,true));assert(mw_playable_race_countdown(&race,0,position));
    assert(mw_playable_race_update(&race,1,position,0,&update)&&!update.crossed&&session.progress.elapsed_us==0);
    position[0]=50;assert(!mw_playable_race_update(&race,1,position,0,&update));assert(session.progress.next==0);
    position[0]=50;assert(mw_playable_race_update(&race,1,position,1000000,&update));
    assert(update.crossed==4&&update.finished&&update.gate==5);close_to(update.finish_fraction,.78);
    assert(session.progress.elapsed_us==780000);

    assert(mw_playable_race_prepare(&race,&session,&catalog,100,aliases,1,0));
    assert(mw_playable_race_admit(&race,true,true,true));position[0]=0;assert(mw_playable_race_countdown(&race,0,position));
    position[0]=20;position[1]=30;assert(mw_playable_race_update(&race,1,position,100000,&update));assert(!update.crossed);
    position[1]=0;assert(mw_playable_race_update(&race,1,position,100000,&update));assert(!update.crossed&&session.progress.next==0);
    position[0]=10;assert(mw_playable_race_update(&race,1,position,100000,&update));assert(update.crossed==1&&session.progress.next==1);
    position[0]=30;assert(mw_playable_race_update(&race,1,position,100000,&update));assert(update.crossed==2&&session.progress.next==3);
    position[0]=40;assert(mw_playable_race_update(&race,1,position,100000,&update));assert(update.finished);

    assert(mw_playable_race_prepare(&race,&session,&catalog,100,aliases,1,0));
    assert(mw_playable_race_admit(&race,true,true,true));position[0]=10;assert(mw_playable_race_countdown(&race,0,position));
    position[0]=0;assert(mw_playable_race_update(&race,1,position,100000,&update));assert(!update.crossed);
    position[0]=10;assert(mw_playable_race_update(&race,1,position,100000,&update));assert(update.crossed==1);
    session.progress.elapsed_us=UINT64_MAX-5;MwPlayableRace before=race;MwRaceSession old_session=session;
    MwPlayableRaceUpdate old_update=update;position[0]=20;
    assert(!mw_playable_race_update(&race,1,position,10,&update));
    assert(!memcmp(&before,&race,sizeof race)&&!memcmp(&old_session,&session,sizeof session)&&!memcmp(&old_update,&update,sizeof update));
    position[0]=NAN;assert(!mw_playable_race_update(&race,1,position,0,&update));assert(!memcmp(&before,&race,sizeof race));
    assert(mw_playable_race_cancel(&race));

    /* Repeated source references require exiting and entering again. */
    word(data+396,2);word(data+12,crc(data+16,405-16));assert(mw_event_catalog_open(&catalog,data,405));
    assert(mw_playable_race_prepare(&race,&session,&catalog,100,aliases,1,0));
    assert(mw_playable_race_admit(&race,true,true,true));position[0]=position[1]=position[2]=0;
    assert(mw_playable_race_countdown(&race,0,position));position[0]=50;
    assert(mw_playable_race_update(&race,1,position,100000,&update));assert(update.crossed==1&&session.progress.next==1);
    position[0]=0;assert(mw_playable_race_update(&race,1,position,100000,&update));assert(update.crossed==1&&session.progress.next==2);
    position[0]=50;assert(mw_playable_race_update(&race,1,position,100000,&update));assert(update.finished&&update.crossed==2);
    assert(mw_playable_race_prepare(&race,&session,&catalog,100,aliases,1,0));assert(mw_playable_race_cancel(&race));

    /* Missing gate shape remains an unavailable course, even with a valid pack. */
    word(data+192+40+4,3);memset(data+192+40+24,0,12);word(data+12,crc(data+16,405-16));
    assert(mw_event_catalog_open(&catalog,data,405));before=race;old_session=session;
    assert(!mw_playable_race_prepare(&race,&session,&catalog,100,aliases,1,0));
    assert(!memcmp(&before,&race,sizeof race)&&!memcmp(&old_session,&session,sizeof session));
}
static void geometry(void)
{
    MwEventNode box={.key=1,.present=7,.dimensions={2,10,3}};
    float a[]={-10,0,0},b[]={10,0,0};double t=123;
    assert(mw_playable_race_sweep(&box,a,b,0,&t));close_to(t,.45);
    assert(mw_playable_race_sweep(&box,a,b,2,&t));close_to(t,.35);
    a[1]=b[1]=5;assert(mw_playable_race_sweep(&box,a,b,0,&t));close_to(t,.45);
    a[1]=b[1]=5.01f;t=123;assert(!mw_playable_race_sweep(&box,a,b,0,&t)&&t==123);
    a[1]=b[1]=0;a[2]=b[2]=3;assert(mw_playable_race_sweep(&box,a,b,0,&t));
    a[2]=b[2]=3.01f;assert(!mw_playable_race_sweep(&box,a,b,0,&t));a[2]=b[2]=0;
    a[0]=0;t=123;assert(!mw_playable_race_sweep(&box,a,b,0,&t)&&t==123);
    a[0]=b[0]=0;a[1]=-10;b[1]=10;box.rotation=90;
    assert(mw_playable_race_sweep(&box,a,b,0,&t));close_to(t,.45);
    box.rotation=-90;assert(mw_playable_race_sweep(&box,a,b,0,&t));close_to(t,.45);
    MwEventNode sphere={.key=2,.present=9,.position={1,2,3},.radius=4};
    float sa[]={-9,2,3},sb[]={11,2,3};assert(mw_playable_race_sweep(&sphere,sa,sb,0,&t));close_to(t,.3);
    assert(mw_playable_race_sweep(&sphere,sa,sb,2,&t));close_to(t,.2);
    sa[0]=1;t=123;assert(!mw_playable_race_sweep(&sphere,sa,sb,0,&t)&&t==123);
    sphere.present=15;sphere.dimensions[0]=sphere.dimensions[1]=sphere.dimensions[2]=.1f;
    sa[0]=-9;assert(mw_playable_race_sweep(&sphere,sa,sb,0,&t));close_to(t,.3);
    box.present=1;assert(!mw_playable_race_sweep(&box,a,b,0,&t));
    box.present=7;box.dimensions[1]=0;assert(!mw_playable_race_sweep(&box,a,b,0,&t));box.dimensions[1]=10;
    a[0]=NAN;assert(!mw_playable_race_sweep(&box,a,b,0,&t));a[0]=0;
    assert(!mw_playable_race_sweep(&box,a,b,-1,&t));assert(!mw_playable_race_sweep(&box,a,b,0,NULL));
    MwEventNode width={.key=3,.present=3};float wa[]={-2,49,49},wb[]={2,49,49};
    assert(mw_playable_race_width_sweep(&width,100,wa,wb,0,&t));close_to(t,.375);
    wa[1]=wb[1]=50.01f;assert(!mw_playable_race_width_sweep(&width,100,wa,wb,0,&t));
    wa[1]=wb[1]=0;wa[2]=wb[2]=50.01f;assert(!mw_playable_race_width_sweep(&width,100,wa,wb,0,&t));
    width.rotation=90;wa[0]=wb[0]=49;wa[1]=-2;wb[1]=2;wa[2]=wb[2]=0;
    assert(mw_playable_race_width_sweep(&width,100,wa,wb,0,&t));close_to(t,.375);
    assert(!mw_playable_race_width_sweep(&width,0,wa,wb,0,&t));assert(!mw_playable_race_width_sweep(&width,NAN,wa,wb,0,&t));
    width.present|=8u;assert(!mw_playable_race_width_sweep(&width,100,wa,wb,0,&t));
}
static void outside(const MwEventNode *node,float radius,float p[3])
{
    memcpy(p,node->position,sizeof(node->position));
    if(node->present&8u){p[0]-=node->radius+radius+.5f;return;}
    double angle=(double)node->rotation*.017453292519943295;
    double extent=(double)node->dimensions[0]*.5+radius+.5;
    p[0]-=(float)(cos(angle)*extent);p[1]-=(float)(sin(angle)*extent);
}
int main(int argc,char **argv)
{
    assert(argc==2);geometry();size_t bytes;void *raw=load(argv[1],&bytes);MwEventCatalog catalog;
    assert(mw_event_catalog_open(&catalog,raw,bytes));MwAliasStore aliases={0};assert(mw_alias_create(&aliases,"Driver"));
    native_policy(&aliases);
    uint32_t keys[512];size_t count;assert(mw_race_session_courses(&catalog,false,keys,512,&count)&&count==82);
    unsigned total_crossed=0,opening=0;
    for(size_t i=0;i<count;i++){
        MwRaceSession session={0};MwPlayableRace r={0};MwPlayableRaceUpdate u;
        assert(mw_playable_race_prepare(&r,&session,&catalog,keys[i],&aliases,0x1234,1.2f));
        if(keys[i]==0xf7e4440a||keys[i]==0x42938ce2||keys[i]==0xd348f2cd||keys[i]==0x6ddd8383||keys[i]==0x9f60a40e)opening++;
        MwPlayableRace before=r;MwRaceSession before_session=session;
        assert(!mw_playable_race_prepare(&r,&session,&catalog,keys[i],&aliases,0x1234,1.2f));
        assert(!memcmp(&before,&r,sizeof r)&&!memcmp(&before_session,&session,sizeof session));
        assert(!mw_playable_race_admit(&r,true,false,true));assert(!mw_playable_race_admit(&r,true,true,false));
        assert(mw_playable_race_admit(&r,true,true,true));float position[3],yaw;
        assert(mw_playable_race_start_pose(&r,position,&yaw));assert(!memcmp(position,session.source_start.position,sizeof position));
        close_to(yaw,remainderf(90+remainderf(session.source_start.rotation,360),360)*.017453292519943295);
        assert(mw_playable_race_countdown(&r,2000000,position));
        memset(&u,0xa5,sizeof u);MwPlayableRaceUpdate old_u=u;before=r;
        assert(!mw_playable_race_update(&r,0x4321,position,1000000,&u));assert(!memcmp(&before,&r,sizeof r)&&!memcmp(&old_u,&u,sizeof u));
        assert(mw_playable_race_update(&r,0x1234,position,1000000,&u)&&!u.started&&r.countdown_us==1000000&&session.progress.elapsed_us==0);
        assert(mw_playable_race_pause(&r));before=r;assert(!mw_playable_race_update(&r,0x1234,position,10000000,&u));assert(!memcmp(&before,&r,sizeof r));
        assert(mw_playable_race_resume(&r));assert(mw_playable_race_update(&r,0x1234,position,1500000,&u)&&u.started&&session.progress.elapsed_us==500000);
        assert(r.phase==MW_PLAYABLE_RUNNING);assert(mw_playable_race_pause(&r));assert(session.phase==MW_SESSION_PAUSED);assert(mw_playable_race_resume(&r));
        unsigned crossed=0;size_t limit=(session.route.count+1)*session.route.laps+1;
        for(size_t step=0;r.phase==MW_PLAYABLE_RUNNING&&step<limit;step++){
            MwEventNode gate;assert(mw_playable_race_next(&r,&gate));outside(&gate,r.actor_radius,position);
            uint64_t elapsed=session.progress.elapsed_us;size_t next=session.progress.next;
            assert(mw_playable_race_relocate(&r,0x1234,position));assert(session.progress.elapsed_us==elapsed&&session.progress.next==next);
            assert(mw_playable_race_update(&r,0x1234,gate.position,100000,&u));assert(u.crossed>0);crossed+=u.crossed;
            assert(session.progress.elapsed_us>=elapsed&&session.progress.elapsed_us<=elapsed+100000);
            if(u.finished)assert(u.event==MW_RACE_FINISHED&&u.finish_fraction>=0&&u.finish_fraction<=1);
        }
        assert(r.phase==MW_PLAYABLE_FINISHED&&session.phase==MW_SESSION_FINISHED);
        assert(crossed==(session.route.count+1)*session.route.laps);total_crossed+=crossed;
        before=r;before_session=session;assert(!mw_playable_race_update(&r,0x1234,position,1,&u));
        assert(!memcmp(&before,&r,sizeof r)&&!memcmp(&before_session,&session,sizeof session));
        assert(!mw_playable_race_cancel(&r));assert(!mw_playable_race_next(&r,&(MwEventNode){0}));
        assert(mw_playable_race_recovery_pose(&r,position,&yaw));assert(mw_playable_race_prepare(&r,&session,&catalog,keys[i],&aliases,0x1234,1.2f));
        assert(mw_playable_race_cancel(&r)&&r.phase==MW_PLAYABLE_CANCELLED&&session.phase==MW_SESSION_CANCELLED);
    }
    assert(opening==5);
    printf("%zu source courses, %u swept gate/lap/finish entries, five opening definitions; countdown, pause, actor identity, recovery and one-shot finish pass.\n",count,total_crossed);
    free(raw);return 0;
}
