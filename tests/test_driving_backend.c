#include "mw_driving_backend.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* Contract tests with explicit synthetic body fixture. The producer refuses
   before any wheel query; these callbacks are NOT an app world implementation. */
typedef struct {MwVehicleWorldActor *trial;unsigned begin,before,after,produce,commit,abort;} Context;
static bool begin(void *p,MwVehicleWorldActor *actor,const MwVehicleRuntimeState *s){Context *c=p;assert(s->body.position[2]==200);c->trial=actor;c->begin++;return true;}
static void commit(void *p,const MwVehicleRuntimeState *s,const MwVehicleRuntimeOutput *o){Context *c=p;(void)s;(void)o;c->commit++;assert(0);}
static void abort_tick(void *p){Context *c=p;c->abort++;c->trial=NULL;}
static bool before(void *p,MwOriginalRigidBody *s,float dt){Context *c=p;assert(dt==mw_driving_backend_step_seconds());c->before++;s->flags|=0x400;return true;}
static bool after(void *p,const MwOriginalRigidBody *old,MwOriginalRigidBody *s,float dt){Context *c=p;(void)dt;assert(c->trial&&c->trial->prepared);assert(old->position[2]==200&&s->position[2]>200);c->after++;return true;}
static bool produce(void *p,const MwVehicleRuntimeParams *params,const MwVehicleRuntimeState *s,const MwVehicleRuntimeInput *in,MwVehicleRuntimeProduced *out){Context *c=p;(void)params;(void)out;assert(s->body.position[2]>200&&in->source_time==4);c->produce++;return false;}
static bool query(void *p,unsigned w,const MwPhysicsContactVector *v,const MwPhysicsContactVector *d,MwVehicleDynamicsQuery *out){(void)p;(void)w;(void)v;(void)d;(void)out;assert(0);return false;}
static MwDrivingBytes read_file(const char *path){FILE *f=fopen(path,"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0);rewind(f);void *p=malloc((size_t)n);assert(p&&fread(p,1,(size_t)n,f)==(size_t)n&&fgetc(f)==EOF);assert(!fclose(f));return (MwDrivingBytes){p,(size_t)n};}
int main(int argc,char **argv){
    assert(argc==5);MwDrivingAssets a={.runtime=read_file(argv[1]),.wheels=read_file(argv[2]),.mechanical=read_file(argv[3]),.bounds=read_file(argv[4]),.model_key=0xcae3e635};
    MwDrivingBackend b={0};assert(mw_driving_backend_open(&b,&a));assert(b.loaded&&!b.started);assert(b.params.powertrain.mechanical.torque.torque==b.params.torque);
    MwDrivingBackend bad={0};unsigned char mismatch[336];assert(a.wheels.bytes==sizeof(mismatch));memcpy(mismatch,a.wheels.data,sizeof(mismatch));mismatch[128]^=1;MwDrivingAssets wrong=a;wrong.wheels.data=mismatch;assert(!mw_driving_backend_open(&bad,&wrong)&&!bad.loaded);
    wrong=a;wrong.model_key^=1;assert(!mw_driving_backend_open(&bad,&wrong)&&!bad.loaded);
    assert(!mw_driving_backend_open_files(&bad,"/no-such-directory","../profile","bmwm3gtre46",a.model_key,a.collision_box_pad));
    MwOriginalRigidBody body={.position={100,30,200},.velocity={2,0,3},.angular_velocity={0,.5f,0},.inverse_mass=b.params.body.inverse_mass};
    memcpy(body.inertia,b.params.body.inertia,sizeof(body.inertia));memcpy(body.local_cg,b.params.local_cg,sizeof(body.local_cg));float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};assert(mw_original_rigid_body_set_orientation(&body,identity));
    MwPhysicsTransmissionEngineStepState engine;assert(mw_driving_backend_engine_construct(&b,&engine));assert(engine.mechanical.gear_slot==2&&engine.mechanical.reported_rpm==b.params.powertrain.mechanical.torque.idle_rpm&&engine.mechanical.engine_omega>0&&engine.scale_100==1);assert(mw_driving_backend_start(&b,&body,&engine,4));
    MwDrivingView view;float origin[3]={10,20,40};assert(mw_driving_backend_view(&b,origin,&view));assert(view.drive.x==190&&view.drive.z==60&&view.height==10);assert(fabsf(view.drive.heading-1.5707963267948966f)<1e-6f);assert(view.drive.speed==3&&view.drive.lateral_speed==-2&&view.drive.yaw_rate==-.5f&&view.drive.drift==0);assert(view.body_matrix_native[12]==100&&view.body_matrix_native[14]==200);
    Context c={0};MwDrivingCallbacks cb={.runtime={.produce=produce,.before_body_tick=before,.after_body_tick=after,.query=query,.context=&c},.begin=begin,.commit=commit,.abort=abort_tick};MwVehicleRuntimeInput raw={0};
    MwVehicleRuntimeState saved=b.state;MwVehicleWorldActor actor=b.actor;
    MwDrivingCallbacks missing=cb;missing.runtime.after_body_tick=NULL;
    MwDrivingAdvance result=mw_driving_backend_advance(&b,&raw,.1f,8,&missing);assert(result.status==MW_DRIVING_NOT_READY&&result.completed_ticks==0&&b.debt_seconds==0);
    result=mw_driving_backend_advance(&b,&raw,.001f,8,&cb);assert(result.status==MW_DRIVING_OK&&result.completed_ticks==0&&c.begin==0);
    result=mw_driving_backend_advance(&b,&raw,.1f,8,&cb);assert(result.status==MW_DRIVING_SOURCE_REJECTED&&result.completed_ticks==0);assert(c.begin==1&&c.before==1&&c.after==1&&c.produce==1&&c.abort==1&&!c.commit&&!c.trial);assert(!memcmp(&saved,&b.state,sizeof(saved))&&!memcmp(&actor,&b.actor,sizeof(actor))&&b.ticks==0&&b.source_clock==4);
    double debt=b.debt_seconds;result=mw_driving_backend_advance(&b,&raw,1,8,&cb);assert(result.status==MW_DRIVING_TIME_DEBT&&b.debt_seconds==debt&&c.begin==1);
    result=mw_driving_backend_advance(&b,&raw,0,9,&cb);assert(result.status==MW_DRIVING_INVALID&&b.debt_seconds==debt);
    mw_driving_backend_close(&b);assert(!b.loaded&&!b.started&&!b.owned_bounds);
    free((void *)a.runtime.data);free((void *)a.wheels.data);free((void *)a.mechanical.data);free((void *)a.bounds.data);
    puts("driving backend source assets + actor/body transaction + scheduler gates: PASS");return 0;
}
