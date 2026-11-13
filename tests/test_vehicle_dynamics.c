#include "mw_vehicle_dynamics.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef struct { unsigned phase,queries;int fail_query;bool hand,air,expect_drive; } Fixture;
/* Synthetic source-phase fixtures. They do NOT claim to implement original
   mechanical/aero or player input-assist producers. */
static bool mechanical(void *context,const MwVehicleDynamicsInput *in,MwPhysicsGroundWheel wheels[4]){
    Fixture *f=context;assert(!f->phase++&&in->seconds>0);
    for(unsigned i=0;i<4;i++)assert(wheels[i].tire.brake.drive_torque==0&&wheels[i].tire.brake.accumulated_brake_torque==0&&isfinite(wheels[i].tire.grip_factor));
    return true;
}
static bool route(void *context,const MwVehicleDynamicsInput *in,MwPhysicsGroundWheel wheels[4]){
    Fixture *f=context;(void)in;assert(f->phase++==1);
    for(unsigned i=0;i<4;i++){
        assert(i>=2||wheels[i].tire.brake.drive_torque==0);
        if(!f->expect_drive)assert(wheels[i].tire.brake.drive_torque==0);
        else if(i>=2)assert(wheels[i].tire.brake.drive_torque>0);
        wheels[i].tire.brake.normal_input=0;wheels[i].tire.brake.handbrake_input=i>=2&&f->hand?1:0;
    }
    return true;
}
static bool query(void *context,unsigned wheel,const MwPhysicsContactVector *point,const MwPhysicsContactVector *velocity,MwVehicleDynamicsQuery *out){
    Fixture *f=context;assert(f->phase==2&&wheel==f->queries++&&isfinite(point->x)&&isfinite(point->y)&&isfinite(point->z)&&isfinite(velocity->z));
    if((int)wheel==f->fail_query)return false;
    /* Actual asphalt scalar values, with an explicitly synthetic flat plane. */
    *out=(MwVehicleDynamicsQuery){.present=!f->air,.normal={0,1,0},.relative_plane_w=-.13f,.surface_lateral_grip=1,.surface_drive_grip=1,.surface_rolling_resistance=1};return true;
}
static void reset_fixture(Fixture *f){f->phase=f->queries=0;}
static void checksum(unsigned char *p,size_t n){unsigned c=~0u;for(size_t i=16;i<n;i++){c^=p[i];for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}c=~c;for(unsigned j=0;j<4;j++)p[12+j]=(unsigned char)(c>>(8*j));}
int main(int argc,char **argv){
    assert(argc==2);FILE *file=fopen(argv[1],"rb");assert(file);unsigned char data[336],bad[336];assert(fread(data,1,sizeof(data),file)==sizeof(data)&&fgetc(file)==EOF&&!fclose(file));
    MwVehicleDynamicsParams p;assert(mw_vehicle_dynamics_params_open(&p,data,sizeof(data))&&p.physical_key==0x39dae0f8u&&p.mass==1300&&p.torque_split==0);
    assert(p.front_axle==1.5f&&p.wheel_base==2.7249999046325684f&&p.steering==1.1100000143051147f);
    MwVehicleDynamicsState state;assert(mw_vehicle_dynamics_init(&state,&p));assert(state.wheels[0].tire.brake.radius_m>.34f&&state.wheels[0].tire.brake.radius_m<.35f);
    MwVehicleDynamicsInput in={.body_matrix={1,0,0,0,0,1,0,0,0,0,1,0,8192,4096,-16384,1},.world_cg_offset={0,-.2f,0},.linear_velocity={0,0,20},.body_half_extent_y=.6f,.seconds=1.f/60,.speed_mps=20,.scales={.gear_slot=2},.distribution={.engine_output_torque=1000,.body_local_forward_velocity=20}};
    for(unsigned i=0;i<4;i++)in.wheel_direction[i]=(MwPhysicsContactVector){0,0,1};
    Fixture f={.fail_query=-1};MwVehicleDynamicsHooks hooks={.mechanical=mechanical,.route_inputs=route,.query=query,.context=&f};MwVehicleDynamicsOutput out;
    assert(mw_vehicle_dynamics_step(&p,&in,&state,&out,&hooks)&&f.queries==4);
    for(unsigned i=0;i<4;i++)assert(state.wheels[i].compression>0&&out.ground[i].suspension.has_contact&&out.ground[i].world_force.y>=0);
    f.expect_drive=true;reset_fixture(&f);assert(mw_vehicle_dynamics_step(&p,&in,&state,&out,&hooks));
    MwVehicleDynamicsState without_hand=state;MwVehicleDynamicsOutput no_hand_out;
    in.distribution.engine_output_torque=0;f.expect_drive=false;
    /* Explicit lateral point velocity exercises the contacted locked-tire
       branch; a perfectly straight zero-slip wheel is a different source path. */
    in.linear_velocity.x=1;in.distribution.body_local_lateral_velocity=1;
    for(unsigned step=0;step<3;step++){reset_fixture(&f);assert(mw_vehicle_dynamics_step(&p,&in,&without_hand,&no_hand_out,&hooks));}
    f.hand=true;
    for(unsigned step=0;step<3;step++){reset_fixture(&f);assert(mw_vehicle_dynamics_step(&p,&in,&state,&out,&hooks));}
    assert(!state.wheels[0].tire.brake.handbrake_input&&!state.wheels[1].tire.brake.handbrake_input);
    for(unsigned i=0;i<2;i++)assert(!memcmp(state.wheels+i,without_hand.wheels+i,sizeof(state.wheels[i])));
    for(unsigned i=2;i<4;i++)assert(state.wheels[i].tire.brake.handbrake_input==1&&state.wheels[i].tire.brake.angular_speed<without_hand.wheels[i].tire.brake.angular_speed);
    MwVehicleDynamicsState before=state;MwVehicleDynamicsOutput previous=out;f.fail_query=3;reset_fixture(&f);
    assert(!mw_vehicle_dynamics_step(&p,&in,&state,&out,&hooks)&&f.queries==4);assert(!memcmp(&state,&before,sizeof(state))&&!memcmp(&out,&previous,sizeof(out)));
    f.fail_query=-1;f.air=true;reset_fixture(&f);assert(mw_vehicle_dynamics_step(&p,&in,&state,&out,&hooks));
    assert(state.wheels[2].tire.brake.locked&&state.wheels[3].tire.brake.locked);
    for(unsigned i=0;i<4;i++)assert(state.wheels[i].compression==0&&state.wheels[i].air_seconds==in.seconds&&out.ground[i].world_force.x==0&&out.ground[i].world_force.y==0&&out.ground[i].world_force.z==0);
    hooks.mechanical=NULL;before=state;previous=out;assert(!mw_vehicle_dynamics_step(&p,&in,&state,&out,&hooks)&&!memcmp(&state,&before,sizeof(state))&&!memcmp(&out,&previous,sizeof(out)));
    MwVehicleDynamicsParams unchanged=p;memcpy(bad,data,sizeof(bad));bad[64]^=1;checksum(bad,sizeof(bad));assert(!mw_vehicle_dynamics_params_open(&p,bad,sizeof(bad))&&!memcmp(&p,&unchanged,sizeof(p)));
    memcpy(bad,data,sizeof(bad));float nan=NAN;memcpy(bad+128,&nan,4);checksum(bad,sizeof(bad));assert(!mw_vehicle_dynamics_params_open(&p,bad,sizeof(bad))&&!memcmp(&p,&unchanged,sizeof(p)));
    assert(!mw_vehicle_dynamics_params_open(&p,data,sizeof(data)-1));float angle=99,angles[2]={88,77};assert(!mw_vehicle_dynamics_steer_fallback(NAN,0,1,&angle)&&angle==99);assert(!mw_vehicle_dynamics_ackermann(0,0,2,angles)&&angles[0]==88&&angles[1]==77);
    puts("Source-profile wheel stage: ordered preparation/distribution/query, prior-contact torque, rear lock, airborne state, late rollback and corruption guards pass. This is not a chassis/whole-car handling test.");return 0;
}
