#include "mw_engine_audio_driver.h"
#include <math.h>
#include <string.h>
static const float tick_seconds=0.01666666753590107f;
bool mw_engine_audio_driver_init(MwEngineAudioDriver *out,const MwVehicleRuntimeParams *p,float clock)
{
    if(!out||!p||!p->body_bound||!isfinite(clock)||p->powertrain.speed_limiter_count||
       p->powertrain.mechanical.gear_count<3||p->powertrain.mechanical.gear_count>10||
       p->powertrain.mechanical.torque.torque!=p->torque||
       p->powertrain.mechanical.ratios!=p->ratios||
       p->powertrain.mechanical.gear_efficiency!=p->efficiency||
       p->powertrain.mechanical.shift_tables!=&p->shifts||
       !isfinite(p->powertrain.mechanical.torque.idle_rpm)||p->powertrain.mechanical.torque.idle_rpm<=0||
       !isfinite(p->powertrain.nos.capacity))return false;
    MwEngineAudioDriver d={.profile=p,.source_clock=clock,.initialized=true};
    /* EngineRacer constructor802545F4/Reset802553CC scalar subset. */
    d.engine.mechanical.gear_slot=2;
    d.engine.mechanical.engine_omega=p->powertrain.mechanical.torque.idle_rpm*0.10471976548433304f;
    d.engine.mechanical.reported_rpm=p->powertrain.mechanical.torque.idle_rpm;
    d.engine.scale_100=1;d.engine.nos.charge=p->powertrain.nos.capacity>0?1:0;
    if(!isfinite(d.engine.mechanical.engine_omega))return false;
    *out=d;return true;
}
void mw_engine_audio_driver_stop(MwEngineAudioDriver *d){if(d)memset(d,0,sizeof(*d));}
static bool frame_valid(const MwEngineAudioFrame *f)
{
    if((f->present&MW_ENGINE_AUDIO_REQUIRED)!=MW_ENGINE_AUDIO_REQUIRED||
       !isfinite(f->input.raw_throttle)||f->input.raw_throttle<0||f->input.raw_throttle>1||
       f->input.external.contact_count>4||!isfinite(f->induction_tuning_18))return false;
    for(unsigned i=0;i<4;i++){
        const MwPhysicsTransmissionSpeedWheel *w=f->wheels+i;
        const float values[]={w->angular_speed,w->spring_compression,w->traction_factor,
            w->previous_longitudinal_velocity,w->radius_m,f->input.external.longitudinal_slip[i]};
        for(unsigned j=0;j<sizeof(values)/sizeof(*values);j++)if(!isfinite(values[j]))return false;
        if(w->radius_m<=0)return false;
    }
    return true;
}
MwEngineAudioAdvance mw_engine_audio_driver_advance(MwEngineAudioDriver *d,float elapsed,
    unsigned maximum,MwEngineAudioProduce produce,MwEngineAudioCommit commit,void *context)
{
    MwEngineAudioAdvance out={.status=MW_ENGINE_AUDIO_NOT_READY,.debt_seconds=d?d->debt_seconds:0};
    if(!d||!d->initialized||!d->profile)return out;
    if(!produce){d->has_sample=false;return out;}
    out.status=MW_ENGINE_AUDIO_BAD_INPUT;
    if(!isfinite(elapsed)||elapsed<0||elapsed>.1f||!maximum||maximum>MW_ENGINE_AUDIO_MAX_TICKS)return out;
    double debt=d->debt_seconds+(double)elapsed;
    if(!isfinite(debt)||debt>1){out.status=MW_ENGINE_AUDIO_TIME_DEBT;return out;}
    d->debt_seconds=debt;out.status=MW_ENGINE_AUDIO_OK;
    while(d->debt_seconds>=(double)tick_seconds&&out.ticks<maximum){
        MwEngineAudioFrame frame={0};
        if(!produce(context,d,&frame)||!frame_valid(&frame)){d->has_sample=false;out.status=MW_ENGINE_AUDIO_SOURCE_REJECTED;break;}
        frame.input.external.seconds=tick_seconds;
        MwPhysicsTransmissionEngineStepState engine=d->engine;
        MwStoryEngine story=d->story;MwPhysicsTransmissionSpeedWheel wheels[4];memcpy(wheels,frame.wheels,sizeof(wheels));
        MwPhysicsTransmissionInductionTiming induction=d->profile->induction_timing;
        induction.tuning_present=frame.induction_tuning_present;induction.tuning_18=frame.induction_tuning_18;
        MwPhysicsTransmissionGearEvent event={0};bool blown=false;
        if(!mw_physics_transmission_engine_step_complete(&d->profile->powertrain,&frame.input,&engine,wheels,&event,
            &story,d->source_clock,mw_player_source_sine,&blown,&induction)){
            d->has_sample=false;out.status=MW_ENGINE_AUDIO_SOURCE_REJECTED;break;
        }
        float clock=d->source_clock+tick_seconds;
        if(!isfinite(clock)||d->ticks==UINT64_MAX){out.status=MW_ENGINE_AUDIO_BAD_INPUT;break;}
        d->engine=engine;d->story=story;d->source_clock=clock;d->ticks++;d->has_sample=true;
        d->debt_seconds-=(double)tick_seconds;out.ticks++;
        if(commit)commit(context,&frame,wheels,&event,blown);
    }
    out.debt_seconds=d->debt_seconds;return out;
}
bool mw_engine_audio_driver_sample(const MwEngineAudioDriver *d,MwEngineAudioSample *out)
{
    if(!d||!d->initialized||!d->has_sample||!out)return false;
    const MwPhysicsTransmissionEngineState *e=&d->engine.mechanical;
    if(!isfinite(e->reported_rpm)||!isfinite(e->applied_throttle)||!isfinite(e->output_torque))return false;
    *out=(MwEngineAudioSample){e->reported_rpm,e->applied_throttle,e->output_torque,e->gear_slot,d->story.blown!=0};return true;
}
bool mw_engine_audio_driver_sabotage(MwEngineAudioDriver *d,float delay)
{return d&&d->initialized&&mw_story_engine_sabotage(&d->story,d->source_clock,delay);}
