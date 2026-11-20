#include "mw_driving_backend.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static bool finite_vector(const float *v,size_t n){for(size_t i=0;i<n;i++)if(!isfinite(v[i]))return false;return true;}
float mw_driving_backend_step_seconds(void){return 0.01666666753590107f;}
static bool callbacks_ready(const MwDrivingCallbacks *c){
    return c&&c->begin&&c->commit&&c->abort&&c->runtime.produce&&
        c->runtime.before_body_tick&&c->runtime.after_body_tick&&c->runtime.query;
}
bool mw_driving_backend_open(MwDrivingBackend *out,const MwDrivingAssets *a){
    if(!out||out->loaded||!a||!a->runtime.data||a->runtime.bytes!=1084||
       !a->wheels.data||a->wheels.bytes!=336||!a->mechanical.data||a->mechanical.bytes!=156||
       !a->bounds.data||!a->bounds.bytes||a->bounds.bytes>MW_DRIVING_BND_MAX_BYTES||
       !a->model_key||!finite_vector(a->collision_box_pad,3))return false;
    unsigned char runtime[1084];memcpy(runtime,a->runtime.data,sizeof(runtime));
    const unsigned char *p=runtime;
    if(memcmp(p+128,a->wheels.data,336)||memcmp(p+464,a->mechanical.data,156))return false;
    MwDrivingBackend b={0};
    if(!mw_vehicle_runtime_params_open(&b.params,runtime,sizeof(runtime))||
       mw_vehicle_world_actor_open(a->bounds.data,a->bounds.bytes,a->model_key,a->collision_box_pad,&b.actor)<0)return false;
    MwBodyCollisionBound root;
    if(mw_body_collision_bound(&b.actor.compound,0,&root)<0)return false;
    for(unsigned i=0;i<3;i++)if(root.half_extents[i]!=b.params.body.halfextent[i])return false;
    b.loaded=true;
    *out=b;
    /* The loader binds curve pointers into its output object. Repair them only
       after all failure-prone validation has succeeded at the final address. */
    if(!mw_vehicle_runtime_params_open(&out->params,runtime,sizeof(runtime))){
        memset(out,0,sizeof(*out));return false;
    }
    return true;
}
static bool basename_valid(const char *p){
    if(!p||!*p)return false;
    unsigned n=0;
    while(*p){unsigned char c=(unsigned char)*p++;if(++n>63||!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'))return false;}
    return true;
}
static bool read_exact(const char *directory,const char *name,const char *extension,void *data,size_t bytes){
    char path[512];int n=snprintf(path,sizeof(path),"%s/%s.%s",directory,name,extension);if(n<0||(size_t)n>=sizeof(path))return false;
    FILE *f=fopen(path,"rb");if(!f)return false;
    bool ok=fread(data,1,bytes,f)==bytes&&fgetc(f)==EOF&&!ferror(f);if(fclose(f))ok=false;return ok;
}
bool mw_driving_backend_open_files(MwDrivingBackend *out,const char *directory,
    const char *profile,const char *bounds,uint32_t model,const float pad[3]){
    if(!out||out->loaded||!directory||!*directory||!basename_valid(profile)||!basename_valid(bounds)||!pad)return false;
    unsigned char nvr[1084],ndp[336],mmp[156];
    if(!read_exact(directory,profile,"nvr",nvr,sizeof(nvr))||!read_exact(directory,profile,"ndp",ndp,sizeof(ndp))||!read_exact(directory,profile,"mmp",mmp,sizeof(mmp)))return false;
    char path[512];int n=snprintf(path,sizeof(path),"%s/%s.bnd",directory,bounds);if(n<0||(size_t)n>=sizeof(path))return false;
    FILE *f=fopen(path,"rb");if(!f)return false;
    if(fseek(f,0,SEEK_END)){fclose(f);return false;}long size=ftell(f);
    if(size<=0||(unsigned long)size>MW_DRIVING_BND_MAX_BYTES||fseek(f,0,SEEK_SET)){fclose(f);return false;}
    void *data=malloc((size_t)size);if(!data){fclose(f);return false;}
    bool ok=fread(data,1,(size_t)size,f)==(size_t)size&&fgetc(f)==EOF&&!ferror(f);if(fclose(f))ok=false;
    MwDrivingAssets a={{nvr,sizeof(nvr)},{ndp,sizeof(ndp)},{mmp,sizeof(mmp)},{data,(size_t)size},model,{pad[0],pad[1],pad[2]}};
    if(!ok||!mw_driving_backend_open(out,&a)){free(data);return false;}
    out->owned_bounds=data;return true;
}
void mw_driving_backend_close(MwDrivingBackend *b){if(!b)return;free(b->owned_bounds);memset(b,0,sizeof(*b));}
bool mw_driving_backend_engine_construct(const MwDrivingBackend *b,MwPhysicsTransmissionEngineStepState *out){
    if(!b||!b->loaded||!out)return false;
    const MwPhysicsTransmissionEngineStepParams *p=&b->params.powertrain;
    if(p->mechanical.gear_count<3||!isfinite(p->mechanical.torque.idle_rpm)||
       p->mechanical.torque.idle_rpm<=0||!isfinite(p->nos.capacity))return false;
    MwPhysicsTransmissionEngineStepState s={0};
    s.mechanical.gear_slot=2;
    s.mechanical.engine_omega=p->mechanical.torque.idle_rpm*0.10471976548433304f;
    s.mechanical.reported_rpm=p->mechanical.torque.idle_rpm;
    s.scale_100=1;s.nos.charge=p->nos.capacity>0?1:0;
    if(!isfinite(s.mechanical.engine_omega))return false;
    *out=s;return true;
}
bool mw_driving_backend_start(MwDrivingBackend *b,const MwOriginalRigidBody *body,
    const MwPhysicsTransmissionEngineStepState *engine,float clock){
    if(!b||!b->loaded||!body||!engine||!isfinite(clock))return false;
    const MwPhysicsTransmissionEngineState *e=&engine->mechanical;
    const float scalars[]={e->clutch.remaining_seconds,e->clutch.duration_seconds,e->shift_delay,
        e->engine_omega,e->angular_acceleration,e->shaft_omega,e->slip_rpm,e->reported_rpm,
        e->output_torque,e->applied_throttle,e->rev_modulation_deadline,engine->nos.charge,
        engine->nos.activity,engine->cooldown,engine->induction_amount,
        engine->induction_display,engine->induction_boost,engine->scale_100};
    if(!finite_vector(scalars,sizeof(scalars)/sizeof(*scalars))||
       e->gear_slot>=b->params.powertrain.mechanical.gear_count||e->clutch.mode>2)return false;
    MwVehicleRuntimeState s;
    if(!mw_vehicle_runtime_init(&s,&b->params,body,engine))return false;
    /* Validate the complete numerical body without advancing spawn state. */
    MwOriginalRigidBody check=*body;
    if(!mw_original_rigid_body_integrate(&check,0)||!mw_vehicle_world_prepare(&b->actor,body))return false;
    b->state=s;b->source_clock=clock;b->debt_seconds=0;b->ticks=0;b->started=true;return true;
}
typedef struct {const MwDrivingCallbacks *c;MwVehicleWorldActor *actor;} Bridge;
static bool before(void *context,MwOriginalRigidBody *body,float dt){
    Bridge *b=context;
    return b->c->runtime.before_body_tick(b->c->runtime.context,body,dt)&&mw_vehicle_world_prepare(b->actor,body);
}
static bool after(void *context,const MwOriginalRigidBody *old,MwOriginalRigidBody *body,float dt){Bridge *b=context;return b->c->runtime.after_body_tick(b->c->runtime.context,old,body,dt);}
static bool produce(void *context,const MwVehicleRuntimeParams *p,const MwVehicleRuntimeState *s,const MwVehicleRuntimeInput *in,MwVehicleRuntimeProduced *out){Bridge *b=context;return b->c->runtime.produce(b->c->runtime.context,p,s,in,out);}
static bool query(void *context,unsigned wheel,const MwPhysicsContactVector *p,const MwPhysicsContactVector *v,MwVehicleDynamicsQuery *out){Bridge *b=context;return b->c->runtime.query(b->c->runtime.context,wheel,p,v,out);}
static bool directions(void *context,const float m[16],float turns,float track,float base,MwPhysicsContactVector out[4]){Bridge *b=context;return b->c->runtime.steer_directions(b->c->runtime.context,m,turns,track,base,out);}
MwDrivingAdvance mw_driving_backend_advance(MwDrivingBackend *b,const MwVehicleRuntimeInput *raw,
    float elapsed,unsigned maximum,const MwDrivingCallbacks *c){
    MwDrivingAdvance result={.status=MW_DRIVING_NOT_READY,.remaining_seconds=b?b->debt_seconds:0};
    if(!b||!b->loaded||!b->started||!callbacks_ready(c))return result;
    result.status=MW_DRIVING_INVALID;
    if(!raw||!isfinite(elapsed)||elapsed<0||elapsed>1||!maximum||maximum>MW_DRIVING_MAX_TICKS||
       !isfinite(raw->throttle)||!isfinite(raw->brake)||!isfinite(raw->handbrake)||!isfinite(raw->steering))return result;
    double debt=b->debt_seconds+(double)elapsed;
    if(!isfinite(debt)||debt>1){result.status=MW_DRIVING_TIME_DEBT;return result;}
    b->debt_seconds=debt;result.status=MW_DRIVING_OK;
    const float dt=mw_driving_backend_step_seconds();
    while(b->debt_seconds>=(double)dt&&result.completed_ticks<maximum){
        MwVehicleRuntimeState state=b->state;MwVehicleWorldActor actor=b->actor;MwVehicleRuntimeOutput output;
        MwVehicleRuntimeInput input=*raw;input.seconds=dt;input.source_time=b->source_clock;
        Bridge bridge={c,&actor};MwVehicleRuntimeHooks h=c->runtime;
        h.context=&bridge;h.before_body_tick=before;h.after_body_tick=after;h.produce=produce;h.query=query;h.steer_directions=c->runtime.steer_directions?directions:NULL;
        if(!c->begin(c->runtime.context,&actor,&state)||!mw_vehicle_runtime_step(&b->params,&input,&state,&output,&h)){
            c->abort(c->runtime.context);result.status=MW_DRIVING_SOURCE_REJECTED;break;
        }
        float clock=b->source_clock+dt;
        if(!isfinite(clock)||b->ticks==UINT64_MAX){c->abort(c->runtime.context);result.status=MW_DRIVING_INVALID;break;}
        b->state=state;b->actor=actor;b->source_clock=clock;b->ticks++;b->debt_seconds-=(double)dt;
        result.completed_ticks++;result.last=output;
        c->commit(c->runtime.context,&b->state,&output);
    }
    result.remaining_seconds=b->debt_seconds;return result;
}
bool mw_driving_backend_view(const MwDrivingBackend *b,const float origin[3],MwDrivingView *out){
    if(!b||!b->started||!origin||!out||!finite_vector(origin,3))return false;
    const MwOriginalRigidBody *s=&b->state.body;const float *m=s->orientation;
    if(!finite_vector(s->position,3)||!finite_vector(s->velocity,3)||!finite_vector(s->angular_velocity,3)||!finite_vector(m,16))return false;
    MwDrivingView view={0};
    view.drive.x=s->position[2]-origin[0];view.height=s->position[1]-origin[1];view.drive.z=s->position[0]-origin[2];
    view.drive.heading=atan2f(m[10],m[8]);
    view.drive.speed=s->velocity[0]*m[8]+s->velocity[1]*m[9]+s->velocity[2]*m[10];
    view.drive.lateral_speed=-(s->velocity[0]*m[0]+s->velocity[1]*m[1]+s->velocity[2]*m[2]);
    view.drive.yaw_rate=-s->angular_velocity[1];view.drive.steering=-(b->state.steering.angle_degrees*0.01745329238474369f);
    memcpy(view.body_matrix_native,m,sizeof(view.body_matrix_native));for(unsigned i=0;i<3;i++)view.body_matrix_native[12+i]=s->position[i];
    const float values[]={view.drive.x,view.drive.z,view.drive.heading,view.drive.speed,
        view.drive.steering,view.drive.lateral_speed,view.drive.yaw_rate,view.height};
    if(!finite_vector(values,sizeof(values)/sizeof(*values)))return false;
    *out=view;return true;
}
