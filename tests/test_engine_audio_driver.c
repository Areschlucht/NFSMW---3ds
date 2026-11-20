#include "mw_engine_audio_driver.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct {
    MwEngineAudioDriver *driver;
    MwPhysicsTransmissionEngineStepState reference;
    MwStoryEngine story;
    float clock;
    unsigned calls,commits,fail_at,missing_at;
} Context;
static bool produce(void *opaque,const MwEngineAudioDriver *d,MwEngineAudioFrame *f)
{
    Context *c=opaque;assert(d==c->driver);c->calls++;
    if(c->calls==c->fail_at)return false;
    f->present=c->calls==c->missing_at?MW_ENGINE_AUDIO_REQUIRED&~MW_ENGINE_AUDIO_CONTACTS:MW_ENGINE_AUDIO_REQUIRED;
    /* Deliberate numeric test fixture. These are NOT bicycle app providers. */
    f->input.input_present=1;f->input.automatic_enabled=1;
    f->input.raw_throttle=(d->ticks%150<100)?.85f:0;
    f->input.external.seconds=9; /* wrapper must overwrite with actual tick */
    f->input.external.contact_count=d->ticks%13?4:0;
    f->input.external.vehicle_speed_128=(float)(d->ticks%200)*.2f;
    f->input.nos.requested=d->ticks%177==0;
    f->input.nos.tuning_14=0;
    for(unsigned i=0;i<4;i++){
        float omega=(float)(d->ticks%300)*.5f;
        f->wheels[i]=(MwPhysicsTransmissionSpeedWheel){omega,d->ticks%13?.1f:0,1,omega*.33f,.33f,0};
    }
    return true;
}
static void commit(void *opaque,const MwEngineAudioFrame *f,const MwPhysicsTransmissionSpeedWheel actual[4],const MwPhysicsTransmissionGearEvent *actual_event,bool actual_blow)
{
    Context *c=opaque;MwPhysicsTransmissionSpeedWheel w[4];memcpy(w,f->wheels,sizeof(w));
    MwPhysicsTransmissionInductionTiming timing=c->driver->profile->induction_timing;
    timing.tuning_present=f->induction_tuning_present;timing.tuning_18=f->induction_tuning_18;
    MwPhysicsTransmissionGearEvent event={0};bool blown=false;
    assert(f->input.external.seconds==0.01666666753590107f);
    assert(mw_physics_transmission_engine_step_complete(&c->driver->profile->powertrain,&f->input,&c->reference,w,&event,&c->story,c->clock,mw_player_source_sine,&blown,&timing));
    assert(!memcmp(&c->reference,&c->driver->engine,sizeof(c->reference)));
    assert(!memcmp(&c->story,&c->driver->story,sizeof(c->story)));
    assert(!memcmp(w,actual,sizeof(w))&&!memcmp(&event,actual_event,sizeof(event))&&blown==actual_blow);
    c->clock+=0.01666666753590107f;assert(c->clock==c->driver->source_clock);c->commits++;
}
int main(int argc,char **argv)
{
    assert(argc==2);unsigned char raw[1084];FILE *f=fopen(argv[1],"rb");assert(f&&fread(raw,1,sizeof(raw),f)==sizeof(raw)&&fgetc(f)==EOF&&!fclose(f));
    MwVehicleRuntimeParams p;assert(mw_vehicle_runtime_params_open(&p,raw,sizeof(raw)));
    MwEngineAudioDriver d={0};MwEngineAudioSample sample={0};assert(!mw_engine_audio_driver_sample(&d,&sample));
    assert(mw_engine_audio_driver_init(&d,&p,0));assert(d.engine.mechanical.gear_slot==2&&d.engine.mechanical.reported_rpm==p.powertrain.mechanical.torque.idle_rpm);assert(!mw_engine_audio_driver_sample(&d,&sample));
    Context c={.driver=&d,.reference=d.engine};
    for(unsigned i=0;i<600;i++){
        MwEngineAudioAdvance a=mw_engine_audio_driver_advance(&d,1.f/30,6,produce,commit,&c);
        assert(a.status==MW_ENGINE_AUDIO_OK&&a.ticks==2&&a.debt_seconds==0);
        assert(mw_engine_audio_driver_sample(&d,&sample)&&sample.rpm==c.reference.mechanical.reported_rpm&&sample.gear_slot==c.reference.mechanical.gear_slot&&sample.applied_throttle==c.reference.mechanical.applied_throttle);
    }
    assert(d.ticks==1200&&c.commits==1200);
    MwPhysicsTransmissionEngineStepState saved=d.engine;float clock=d.source_clock;uint64_t ticks=d.ticks;
    c.missing_at=c.calls+1;
    MwEngineAudioAdvance a=mw_engine_audio_driver_advance(&d,1.f/60,6,produce,commit,&c);
    assert(a.status==MW_ENGINE_AUDIO_SOURCE_REJECTED&&!a.ticks&&d.ticks==ticks&&d.source_clock==clock&&!memcmp(&saved,&d.engine,sizeof(saved))&&!mw_engine_audio_driver_sample(&d,&sample));
    c.missing_at=0;a=mw_engine_audio_driver_advance(&d,0,6,produce,commit,&c);assert(a.status==MW_ENGINE_AUDIO_OK&&a.ticks==1&&mw_engine_audio_driver_sample(&d,&sample));
    c.fail_at=c.calls+2;unsigned before=c.commits;
    a=mw_engine_audio_driver_advance(&d,1.f/15,6,produce,commit,&c);assert(a.status==MW_ENGINE_AUDIO_SOURCE_REJECTED&&a.ticks==1&&c.commits==before+1&&!mw_engine_audio_driver_sample(&d,&sample));
    c.fail_at=0;a=mw_engine_audio_driver_advance(&d,0,6,produce,commit,&c);assert(a.status==MW_ENGINE_AUDIO_OK&&a.ticks==3);
    assert(mw_engine_audio_driver_sabotage(&d,.1f));c.story=d.story;bool prior=false;
    for(unsigned i=0;i<20;i++){a=mw_engine_audio_driver_advance(&d,1.f/60,6,produce,commit,&c);assert(a.status==MW_ENGINE_AUDIO_OK);if(d.story.blown)prior=true;}assert(prior&&mw_engine_audio_driver_sample(&d,&sample)&&sample.engine_blown);
    assert(!mw_engine_audio_driver_sabotage(&d,5));
    saved=d.engine;clock=d.source_clock;assert(mw_engine_audio_driver_advance(&d,NAN,6,produce,commit,&c).status==MW_ENGINE_AUDIO_BAD_INPUT);assert(!memcmp(&saved,&d.engine,sizeof(saved))&&d.source_clock==clock);
    assert(mw_engine_audio_driver_advance(&d,.2f,6,produce,commit,&c).status==MW_ENGINE_AUDIO_BAD_INPUT);
    assert(mw_engine_audio_driver_advance(&d,1.f/60,6,NULL,commit,&c).status==MW_ENGINE_AUDIO_NOT_READY&&!mw_engine_audio_driver_sample(&d,&sample));
    /* Catch-up bound retains unconsumed time instead of creating extra ticks. */
    assert(mw_engine_audio_driver_init(&d,&p,0));memset(&c,0,sizeof(c));c.driver=&d;c.reference=d.engine;
    a=mw_engine_audio_driver_advance(&d,.1f,1,produce,commit,&c);assert(a.status==MW_ENGINE_AUDIO_OK&&a.ticks==1&&a.debt_seconds>.08);
    for(unsigned i=0;i<10;i++)assert(mw_engine_audio_driver_advance(&d,.1f,1,produce,commit,&c).status==MW_ENGINE_AUDIO_OK);
    assert(mw_engine_audio_driver_advance(&d,.1f,1,produce,commit,&c).status==MW_ENGINE_AUDIO_TIME_DEBT);
    mw_engine_audio_driver_stop(&d);assert(!d.initialized&&!d.profile&&!mw_engine_audio_driver_sample(&d,&sample));
    puts("Engine audio driver:1200source-core continuation ticks, real reported RPM, missing-provider refusal, transactional rejection, bounded60Hz debt, sabotage and reset pass");return 0;
}
