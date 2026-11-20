#include "mw_vehicle_runtime.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
/* Integration-contract tests, not evidence of whole-game parity. These
   deliberately reject providers, checking that trial body ticks never commit. */
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void put(unsigned char *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
static unsigned stage;
static bool before(void *c,MwOriginalRigidBody *b,float dt){(void)c;(void)dt;assert(stage++==0);b->flags|=0x400;return true;}
static bool after(void *c,const MwOriginalRigidBody *old,MwOriginalRigidBody *b,float dt){(void)c;(void)dt;assert(stage++==1);assert(old->velocity[2]==3);assert(b->position[2]>old->position[2]);memset(b->force,0,sizeof(b->force));return true;}
static bool produce(void *c,const MwVehicleRuntimeParams *p,const MwVehicleRuntimeState *s,const MwVehicleRuntimeInput *i,MwVehicleRuntimeProduced *v){(void)c;(void)p;(void)i;(void)v;assert(stage++==2);assert(s->body.position[2]>0);return false;}
static bool directions(void *c,const float m[16],float t,float w,float b,MwPhysicsContactVector o[4]){(void)c;(void)m;(void)t;(void)w;(void)b;(void)o;assert(0);return false;}
static bool query(void *c,unsigned i,const MwPhysicsContactVector *p,const MwPhysicsContactVector *v,MwVehicleDynamicsQuery *q){(void)c;(void)i;(void)p;(void)v;(void)q;assert(0);return false;}
static float power(float a,float b,void *c){(void)a;(void)b;(void)c;assert(0);return 0;}
static float sine(float a,void *c){(void)a;(void)c;assert(0);return 0;}
int main(int argc,char **argv){
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);unsigned char bytes[1084];assert(fread(bytes,1,sizeof(bytes),f)==sizeof(bytes));assert(fgetc(f)==EOF);fclose(f);
    MwVehicleRuntimeParams p;assert(mw_vehicle_runtime_params_open(&p,bytes,sizeof(bytes)));assert(p.powertrain.mechanical.torque.torque==p.torque);assert(p.powertrain.mechanical.shift_tables==&p.shifts);assert(p.body.mass==p.wheels.mass);assert(p.body.halfextent[1]>0);
    MwVehicleRuntimeParams sentinel;memset(&sentinel,0xa5,sizeof(sentinel));MwVehicleRuntimeParams original=sentinel;bytes[620]^=1;assert(!mw_vehicle_runtime_params_open(&sentinel,bytes,sizeof(bytes)));assert(!memcmp(&sentinel,&original,sizeof(original)));bytes[620]^=1;
    /* CRC-valid format changes still reject missing/invalid induction metadata. */
    unsigned char changed[sizeof(bytes)];memcpy(changed,bytes,sizeof(bytes));put(changed+4,3);assert(!mw_vehicle_runtime_params_open(&sentinel,changed,sizeof(changed)));
    if(bytes[4]==2){
        memcpy(changed,bytes,sizeof(bytes));put(changed+804,0x7fc00000);put(changed+12,crc(changed+16,sizeof(changed)-16));assert(!mw_vehicle_runtime_params_open(&sentinel,changed,sizeof(changed)));
        memcpy(changed,bytes,sizeof(bytes));put(changed+4,1);put(changed+720,0);put(changed+804,0);put(changed+808,0);put(changed+12,crc(changed+16,sizeof(changed)-16));
        bool active=p.powertrain.induction.low_boost>0||p.powertrain.induction.high_boost>0;
        assert(mw_vehicle_runtime_params_open(&sentinel,changed,sizeof(changed))==!active);
    }
    MwOriginalRigidBody b={.inverse_mass=p.body.inverse_mass};memcpy(b.inertia,p.body.inertia,sizeof(b.inertia));memcpy(b.local_cg,p.local_cg,sizeof(b.local_cg));float identity[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};assert(mw_original_rigid_body_set_orientation(&b,identity));b.velocity[2]=3;
    MwPhysicsTransmissionEngineStepState engine={0};MwVehicleRuntimeState state;assert(mw_vehicle_runtime_init(&state,&p,&b,&engine));MwVehicleRuntimeState saved=state;
    MwVehicleRuntimeOutput out,unchanged;memset(&out,0x5a,sizeof(out));unchanged=out;
    MwVehicleRuntimeInput in={.seconds=1.f/60,.source_time=1};MwPhysicsSuspensionMath sm={power,0};MwPhysicsContactMath cm={.sine=sine};MwVehicleRuntimeHooks h={.produce=produce,.steer_directions=directions,.before_body_tick=before,.after_body_tick=after,.query=query,.suspension_math=&sm,.contact_math=&cm};
    assert(!mw_vehicle_runtime_step(&p,&in,&state,&out,&h));assert(stage==3);assert(!memcmp(&state,&saved,sizeof(state)));assert(!memcmp(&out,&unchanged,sizeof(out)));
    stage=0;h.query=0;assert(!mw_vehicle_runtime_step(&p,&in,&state,&out,&h));assert(stage==0);assert(!memcmp(&state,&saved,sizeof(state)));
    MwStoryEngine story={5,0};float omega=100;bool blew;
    assert(mw_physics_transmission_sabotage_stage(&omega,&story,5,mw_player_source_sine,&blew)&&blew&&story.blown&&story.deadline==0&&omega==100);
    assert(mw_physics_transmission_sabotage_stage(&omega,&story,6,mw_player_source_sine,&blew)&&!blew);
    story=(MwStoryEngine){5,0};MwStoryEngine saved_story=story;
    assert(!mw_physics_transmission_sabotage_stage(&omega,&story,1,NULL,&blew)&&omega==100&&!memcmp(&story,&saved_story,sizeof(story)));
    puts("vehicle runtime source profile + transactional provider gates: PASS");return 0;
}
