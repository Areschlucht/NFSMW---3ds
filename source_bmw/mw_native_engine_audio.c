#include "mw_native_engine_audio.h"
#include "mw_original_power.h"
#include <math.h>
#include <string.h>
static bool finite3(const float *p){return p&&isfinite(p[0])&&isfinite(p[1])&&isfinite(p[2]);}
static bool motion(const DriveState *p){return p&&isfinite(p->x)&&isfinite(p->z)&&isfinite(p->heading)&&isfinite(p->steering);}
bool mw_native_engine_audio_init(MwNativeEngineAudio *out,const MwVehicleRuntimeParams *p,const WheelRig *rig,float extent,const float center[3],float clock)
{
    if(!out||!p||!rig||!finite3(center)||!isfinite(extent)||extent<=0||extent>16)return false;
    MwNativeEngineAudio a={.rig=rig,.extent=extent,.initialized=true};memcpy(a.center,center,sizeof(a.center));
    unsigned seen=0;
    for(unsigned i=0;i<4;i++){
        const Wheel *w=rig->wheels+i;
        if(!finite3(w->pivot)||!isfinite(w->radius)||w->radius<=.1f||w->radius>=1)return false;
        /* Existing rigs may iterate side then axle. Source wheel0/1front,
           wheel2/3rear; sourcepositiveY/negativeviewerZ is left. */
        unsigned slot=(w->front?0:2)+((w->pivot[2]*extent+center[2])>=0?1:0);
        if(seen&(1u<<slot))return false;
        seen|=1u<<slot;a.visual_wheel[slot]=i;
    }
    if(seen!=15||!mw_engine_audio_driver_init(&a.source,p,clock))return false;
    *out=a;return true;
}
void mw_native_engine_audio_stop(MwNativeEngineAudio *a){if(a)memset(a,0,sizeof(*a));}
static void wheel_point(const MwNativeEngineAudio *a,const DriveState *car,float height,float ground_offset,unsigned visual,float p[3])
{
    const float *local=a->rig->wheels[visual].pivot;
    float angle=car->heading-1.5707963267948966f,co=cosf(angle),si=sinf(angle);
    float x=local[0]*a->extent,z=local[2]*a->extent;
    p[0]=car->x+co*x+si*z;p[1]=height+ground_offset+local[1]*a->extent;
    p[2]=car->z-si*x+co*z;
}
typedef struct {
    MwNativeEngineAudio *a;
    float omega[4],compression[4],velocity[4],slip[4],traction[4],radius[4];
    unsigned locked[4],contacts;
    float throttle,speed;
    bool nos;
} Observation;
static bool produce(void *opaque,const MwEngineAudioDriver *driver,MwEngineAudioFrame *frame)
{
    Observation *o=opaque;MwNativeEngineAudio *a=o->a;(void)driver;
    frame->present=MW_ENGINE_AUDIO_REQUIRED;
    frame->input.raw_throttle=o->throttle;frame->input.input_present=1;frame->input.automatic_enabled=1;
    frame->input.external.vehicle_speed_128=o->speed;frame->input.external.contact_count=a->contacts;
    /* All optional boost/tuning/unlimited/game-effect interfaces are actually
       absent from this native audio world; normal mode0/gate0 is native policy. */
    frame->input.nos.requested=o->nos;
    for(unsigned i=0;i<4;i++){
        frame->wheels[i]=(MwPhysicsTransmissionSpeedWheel){o->omega[i],a->compression[i],a->traction[i],a->velocity[i],o->radius[i],o->locked[i]};
        frame->input.external.longitudinal_slip[i]=a->slip[i];
    }
    return true;
}
static void commit(void *opaque,const MwEngineAudioFrame *frame,const MwPhysicsTransmissionSpeedWheel wheels[4],const MwPhysicsTransmissionGearEvent *event,bool blew)
{
    Observation *o=opaque;MwNativeEngineAudio *a=o->a;(void)frame;(void)wheels;(void)event;(void)blew;
    memcpy(a->compression,o->compression,sizeof(a->compression));memcpy(a->velocity,o->velocity,sizeof(a->velocity));
    memcpy(a->slip,o->slip,sizeof(a->slip));memcpy(a->traction,o->traction,sizeof(a->traction));a->contacts=o->contacts;
}
MwEngineAudioAdvance mw_native_engine_audio_advance(MwNativeEngineAudio *a,const MwNativeEngineObservation *in,MwNativeEngineGround ground,void *context)
{
    MwEngineAudioAdvance result={.status=MW_ENGINE_AUDIO_NOT_READY,.debt_seconds=a?a->source.debt_seconds:0};
    if(!a||!a->initialized||!a->source.initialized)return result;
    if(!in||!ground||!motion(in->previous)||!motion(in->current)||!in->previous_wheels||!in->current_wheels||
       !isfinite(in->seconds)||in->seconds<=0||in->seconds>.1f||!isfinite(in->previous_height)||!isfinite(in->height)||
       !isfinite(in->car_ground_offset)||!isfinite(in->control.throttle)||in->control.throttle< -1||in->control.throttle>1){
        a->source.has_sample=false;result.status=MW_ENGINE_AUDIO_BAD_INPUT;return result;
    }
    Observation o={.a=a,.throttle=fabsf(in->control.throttle),.nos=in->nos_requested};
    const MwVehicleRuntimeParams *p=a->source.profile;
    float dx=in->current->x-in->previous->x,dz=in->current->z-in->previous->z;
    float distance=dx*sinf(in->current->heading)+dz*cosf(in->current->heading);
    o.speed=hypotf(dx,dz)/in->seconds;
    for(unsigned i=0;i<4;i++){
        unsigned visual=a->visual_wheel[i];const Wheel *wheel=a->rig->wheels+visual;
        float old=in->previous_wheels->angle[visual],now=in->current_wheels->angle[visual];
        if(!isfinite(old)||!isfinite(now)){a->source.has_sample=false;result.status=MW_ENGINE_AUDIO_BAD_INPUT;return result;}
        o.locked[i]=in->control.handbrake&&!wheel->front;
        float expected=o.locked[i]?0:-distance/wheel->radius;
        float delta=now-old;
        /* WheelMotion uses fmod after accepted displacement. Unwrap by that
           measured displacement, not by inventing an engine RPM calibration. */
        delta+=roundf((expected-delta)/6.283185307179586f)*6.283185307179586f;
        o.omega[i]=-delta/in->seconds;
        o.radius[i]=mw_physics_tire_diameter_m(&p->wheels.dimensions,i<2)*.5f;
        if(!isfinite(o.omega[i])||!isfinite(o.radius[i])||o.radius[i]<=0){a->source.has_sample=false;result.status=MW_ENGINE_AUDIO_BAD_INPUT;return result;}
        float point[3],previous[3],normal[3],height;
        wheel_point(a,in->current,in->height,in->car_ground_offset,visual,point);
        wheel_point(a,in->previous,in->previous_height,in->car_ground_offset,visual,previous);
        float direction=in->current->heading+(wheel->front?in->current->steering:0);
        o.velocity[i]=((point[0]-previous[0])*sinf(direction)+(point[2]-previous[2])*cosf(direction))/in->seconds;
        o.slip[i]=fmaf(o.omega[i],o.radius[i],-o.velocity[i]);
        point[1]-=wheel->radius;
        int found=ground(context,i,point,&height,normal);
        if(found<0||found>1||(found&&(!isfinite(height)||!finite3(normal)))){
            a->source.has_sample=false;result.status=MW_ENGINE_AUDIO_SOURCE_REJECTED;return result;
        }
        if(found){
            float length=sqrtf(normal[0]*normal[0]+normal[1]*normal[1]+normal[2]*normal[2]);
            if(!(length>0)||!isfinite(length)){a->source.has_sample=false;result.status=MW_ENGINE_AUDIO_SOURCE_REJECTED;return result;}
            float ny=normal[1]/length;
            /* Native visual tyre-bottom proxy, original scalar suspension law.
               This is not the original bodymount/rigid-body contact pipeline. */
            MwPhysicsSuspensionInput query={.query_relative_plane_w=(height-point[1])*ny,.normal_dot_body_up=ny,
                .previous_compression=a->compression[i],.seconds=in->seconds,.body_mass=p->wheels.mass};
            MwPhysicsSuspensionOutput output;MwPhysicsSuspensionMath math={mw_original_power_callback_float,NULL};
            mw_physics_suspension_load(&p->wheels.axles[i>>1],&query,&output,&math);
            if(!isfinite(output.compression)){a->source.has_sample=false;result.status=MW_ENGINE_AUDIO_SOURCE_REJECTED;return result;}
            o.compression[i]=output.compression;
            if(output.has_contact){o.contacts++;o.traction[i]=1;}
        }
    }
    /* Native reverse selection is caller's existing signed throttle convention.
       The recovered commit handles ratios/clutch/delay; original reverse input
       authorization itself is not claimed to have been ported. */
    MwPhysicsTransmissionEngineStepState before_selection=a->source.engine;
    unsigned requested=in->control.throttle<0?0:2;
    if((requested==0&&a->source.engine.mechanical.gear_slot!=0)||
       (requested==2&&a->source.engine.mechanical.gear_slot==0)){
        MwPhysicsTransmissionEngineState *e=&a->source.engine.mechanical;
        MwPhysicsTransmissionShiftState shift={e->gear_slot,e->clutch.mode,e->shift_delay};
        if(!mw_physics_transmission_commit_gear(&shift,(int)requested,p->powertrain.mechanical.ratios,p->powertrain.mechanical.gear_count,p->powertrain.shift_speed)){
            a->source.has_sample=false;result.status=MW_ENGINE_AUDIO_SOURCE_REJECTED;return result;
        }
        e->gear_slot=shift.gear_slot;e->clutch.mode=shift.clutch_state;e->shift_delay=shift.shift_delay;
    }
    result=mw_engine_audio_driver_advance(&a->source,in->seconds,MW_ENGINE_AUDIO_MAX_TICKS,produce,commit,&o);
    if(!result.ticks)a->source.engine=before_selection;
    return result;
}
bool mw_native_engine_audio_sample(const MwNativeEngineAudio *a,MwEngineAudioSample *out)
{return a&&a->initialized&&mw_engine_audio_driver_sample(&a->source,out);}
