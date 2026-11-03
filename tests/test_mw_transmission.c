#include "mw_physics_transmission_engine.h"
#include "mw_physics_transmission_nos.h"
#include "mw_physics_transmission.h"
#include "mw_physics_transmission_policy.h"
#include "mw_physics_transmission_distribution.h"
#include <string.h>
static float test_angle(float x,float z){(void)x;(void)z;return .125f;}
#include <assert.h>
#include <math.h>
int main(void)
{
    float values[]={100,200,300};MwPhysicsEngineCurve c={values,3,1000,9000,7000};
    assert(mw_physics_transmission_output_torque_nm(&c,1000,0,0,0)==0);
    assert(mw_physics_transmission_output_torque_nm(&c,1000,0,0,6)>135.57f);
    assert(mw_physics_transmission_output_torque_nm(&c,1000,-1,1,6)==0);
    float braking[]={-1,2};c=(MwPhysicsEngineCurve){braking,2,1000,9000,9000};
    assert(mw_physics_transmission_engine_braking(&c,100,1000)==0);
    assert(mw_physics_transmission_engine_braking(&c,100,9000)==-100);
    c.count=1;
    assert(mw_physics_transmission_engine_braking(&c,100,9000)==100);
    c.count=0;assert(isnan(mw_physics_transmission_engine_braking(&c,100,1000)));
    assert(mw_physics_transmission_reported_rpm(0,2,0,1000,2000,10)==1550);
    assert(mw_physics_transmission_reported_rpm(0,2,.1f,8500,0,10)>8400);
    assert(mw_physics_transmission_reported_rpm(1,3,.1f,8500,0,10)<8450);
    float ratios[]={3.2f,0,4.1f,2.53f};
    MwPhysicsTransmissionShiftState state={2,0,0};
    assert(mw_physics_transmission_commit_gear(&state,3,ratios,4,.25f));
    assert(state.gear_slot==3 && state.clutch_state==2 && state.shift_delay==.25f*2.53f);
    assert(mw_physics_transmission_commit_gear(&state,2,ratios,4,.25f));
    assert(state.shift_delay==(.25f*4.1f)*.25f);
    assert(!mw_physics_transmission_commit_gear(&state,-1,ratios,4,.25f));
    assert(state.gear_slot==2);
    assert(mw_physics_transmission_inertia(10,2)==.5f);
    assert(mw_physics_transmission_inertia(10,1)==.175f);
    MwPhysicsTransmissionClutchInput input={.gear_slot=2,.clutch_state=0,
        .engine_omega=100,.shaft_omega=100,.engine_inertia=.5f,
        .net_engine_torque=100,.driveline_ratio=3,.contact_fraction=1,
        .torque_split=0,.shift_coupling=1,.previous_slip_rpm=123};
    MwPhysicsTransmissionClutchResult result;
    assert(mw_physics_transmission_clutch_core(&input,300,20,&result));
    assert(result.wheel_torque==100 && result.engine_reaction_torque== -100 && result.slip_rpm==0);
    input.clutch_state=1;input.shaft_omega=0;
    assert(mw_physics_transmission_clutch_core(&input,300,20,&result));
    assert(result.wheel_torque==2000 && result.engine_reaction_torque== -2000);
    input.clutch_state=2;
    assert(mw_physics_transmission_clutch_core(&input,300,20,&result));
    assert(result.wheel_torque==0 && result.engine_reaction_torque==0 && result.slip_rpm==0);
    input.gear_slot=1;
    assert(mw_physics_transmission_clutch_core(&input,300,20,&result));
    assert(result.wheel_torque==0 && result.slip_rpm==123);
    input.engine_inertia=0;
    assert(!mw_physics_transmission_clutch_core(&input,300,20,&result));
    MwPhysicsTransmissionClutchState engagement={2,0,0};float blend;
    assert(mw_physics_transmission_clutch_update(&engagement,2,0,0,0,1,800,&blend));
    assert(engagement.mode==1 && engagement.remaining_seconds==.05f && blend==.25f);
    assert(mw_physics_transmission_clutch_update(&engagement,2,.025f,0,0,1,800,&blend));
    assert(engagement.mode==1 && blend==.625f);
    assert(mw_physics_transmission_clutch_update(&engagement,2,.025f,0,0,1,800,&blend));
    assert(engagement.mode==0 && blend==1);
    assert(mw_physics_transmission_clutch_update(&engagement,2,0,0,0,0,800,&blend));
    assert(engagement.mode==2);
    MwPhysicsTransmissionDifferentialInput diff={.angular_speed={10,30},.contacted={1,1},.base_ratio=.5,.locking=.8};float shares[2];
    assert(mw_physics_transmission_differential(&diff,false,shares));
    assert(fabsf(shares[0]-.7f)<.000001f && fabsf(shares[1]-.3f)<.000001f);
    diff.angular_speed[0]= -30;
    assert(mw_physics_transmission_differential(&diff,false,shares));assert(shares[0]==.5f && shares[1]==.5f);
    float flat[]={100,100};MwPhysicsEngineCurve engine={flat,2,1000,6000,5000};
    MwPhysicsTransmissionInduction induction={.low_boost=.2f,.high_boost=.4f,.vacuum=-.05f,.spool=.25f};
    assert(mw_physics_transmission_induction_raw(&engine,&induction,2000,1)==.2f);
    assert(mw_physics_transmission_induction_raw(&engine,&induction,5000,1)==.4f);
    float gears[]={3.2f,0,4,2};MwPhysicsTransmissionShiftTables tables;
    assert(mw_physics_transmission_shift_tables(&engine,&induction,gears,4,&tables));
    assert(tables.up[2]==4900 && tables.up[3]==5000 && tables.down[3]==2450);
    assert(mw_physics_transmission_shift_request(&tables,gears,4,2,5000,1,1000)==2);
    assert(mw_physics_transmission_shift_request(&tables,gears,4,3,1000,0,1000)==1);
    MwPhysicsTransmissionDistribution params={.engine_output_torque=1000,.torque_split=0,.differential={.8f,.8f,0},.assist_strength=1};
    MwPhysicsTransmissionWheel wheels[4]={0};
    for(unsigned i=0;i<4;++i){wheels[i].angular_speed=10;wheels[i].spring_compression=.1f;wheels[i].grip_factor=1;}
    assert(mw_physics_transmission_distribute(&params,wheels,NULL));
    assert(wheels[0].drive_torque==0 && wheels[1].drive_torque==0 && wheels[2].drive_torque==500 && wheels[3].drive_torque==500);
    for(unsigned i=0;i<4;++i){wheels[i].drive_torque=0;wheels[i].last_lateral_velocity=10;wheels[i].longitudinal_slip=40;}
    params.steering=1;MwPhysicsTransmissionWheel saved[4];memcpy(saved,wheels,sizeof saved);
    assert(!mw_physics_transmission_distribute(&params,wheels,NULL));assert(!memcmp(saved,wheels,sizeof saved));
    assert(mw_physics_transmission_distribute(&params,wheels,test_angle));
    assert(wheels[2].drive_torque==250 && wheels[3].drive_torque==0 && wheels[2].grip_factor==2);
    MwPhysicsTransmissionSpeedWheel effective={.angular_speed=100,.spring_compression=.1f,
        .traction_factor=1,.previous_longitudinal_velocity=10,.radius_m=.5f};
    assert(mw_physics_transmission_engine_wheel_omega(&effective)==20);
    effective.locked=1;assert(mw_physics_transmission_engine_wheel_omega(&effective)==0);
    effective.locked=0;effective.spring_compression=0;
    assert(mw_physics_transmission_engine_wheel_omega(&effective)==100);
    MwPhysicsTransmissionShaftInput shaft={.gear_slot=2,.clutch_state=2,.seconds=.1f,
        .engine_omega=100,.engine_rpm=1000,.net_engine_torque=100,.engine_inertia=.5f,
        .throttle=1,.clutch_slip=.8f,.idle_rpm=800,.optimal_rpm=5150,
        .minimum_omega=80,.maximum_omega=300};
    MwPhysicsTransmissionShaftResult shaft_out;
    assert(mw_physics_transmission_shaft_step(&shaft,&shaft_out));
    assert(shaft_out.angular_acceleration==200 && shaft_out.angular_speed==120);
    shaft.maximum_omega=110;assert(mw_physics_transmission_shaft_step(&shaft,&shaft_out));
    assert(shaft_out.angular_speed==110 && shaft_out.angular_acceleration==200);
    shaft.maximum_omega=300;shaft.clutch_state=0;shaft.engine_rpm=800;shaft.reaction_torque=-100;
    assert(mw_physics_transmission_shaft_step(&shaft,&shaft_out));
    assert(fabsf(shaft_out.reaction_torque+4)<.00001f);
    MwPhysicsTransmissionShaftResult untouched=shaft_out;shaft.engine_inertia=0;
    assert(!mw_physics_transmission_shaft_step(&shaft,&shaft_out));
    assert(!memcmp(&untouched,&shaft_out,sizeof untouched));
    MwPhysicsTransmissionInduction no_induction={0};float peak_torque,peak_rpm;
    assert(mw_physics_transmission_peak_torque(&engine,&no_induction,&peak_torque,&peak_rpm));
    assert(peak_torque==100 && peak_rpm==1000);
    MwPhysicsTransmissionSpeedWheel coupled[4]={0};
    for(unsigned i=0;i<4;++i){coupled[i].angular_speed=10+20*i;coupled[i].spring_compression=.1f;}
    assert(mw_physics_transmission_sync_wheels(coupled,0,2,100,30));
    assert(coupled[0].angular_speed==10 && coupled[1].angular_speed==30);
    assert(coupled[2].angular_speed==90 && coupled[3].angular_speed==110);
    assert(mw_physics_transmission_sync_wheels(coupled,0,2,100,0));
    assert(coupled[2].angular_speed==100 && coupled[3].angular_speed==100);
    coupled[2].spring_compression=coupled[3].spring_compression=0;
    coupled[3].angular_speed=-100;
    assert(mw_physics_transmission_cap_airborne_wheels(coupled,0,-50));
    assert(coupled[2].angular_speed==0 && coupled[3].angular_speed==-50);
    MwPhysicsTransmissionNosParams nos={2,.75f,2.5f,50,30,50,100};
    MwPhysicsTransmissionNosInput ni={.seconds=.1f,.applied_throttle=1,.vehicle_speed_128=30,
        .gear_slot=2,.requested=1};
    MwPhysicsTransmissionNosState ns={1,0};float scale;
    assert(mw_physics_transmission_nos_step(&nos,&ni,&ns,&scale));
    assert(scale==1.75f && ns.charge==.96f && ns.activity==1);
    ni.requested=0;assert(mw_physics_transmission_nos_step(&nos,&ni,&ns,&scale));
    assert(scale==1 && ns.charge==.96f && ns.activity==.95f);
    ns.activity=0;assert(mw_physics_transmission_nos_step(&nos,&ni,&ns,&scale));
    assert(ns.charge>.96f && ns.activity==0);
    ni.requested=1;ni.vehicle_speed_128=8/2.23699f;ns=(MwPhysicsTransmissionNosState){1,0};
    assert(mw_physics_transmission_nos_step(&nos,&ni,&ns,&scale));assert(ns.charge==1 && scale==1);
    ns.activity=1;assert(mw_physics_transmission_nos_step(&nos,&ni,&ns,&scale));
    assert(ns.charge<1 && scale==1.75f);
    float efficiency[]={1,1,1,1};float braking_samples[]={.1f,.1f};
    MwPhysicsTransmissionEngineParams ep={.torque=engine,
        .engine_braking={braking_samples,2,1000,6000,5000},.ratios=gears,
        .gear_efficiency=efficiency,.gear_count=4,.flywheel_mass=10,.final_gear=3.4f,
        .torque_split=0,.peak_raw_torque=100,.peak_torque_rpm=1000,.shift_tables=&tables};
    MwPhysicsTransmissionEngineInput ei={.seconds=1/60.0f,.applied_throttle=1,.scale_100=1};
    MwPhysicsTransmissionEngineState es={.gear_slot=1,.clutch={2,0,0},
        .engine_omega=104.719765f,.reported_rpm=1000};
    memset(coupled,0,sizeof coupled);
    assert(mw_physics_transmission_engine_mechanical_step(&ep,&ei,&es,coupled));
    assert(es.output_torque==0 && es.engine_omega>104.719765f && es.shift_request==0);
    es.rev_modulation_deadline=1;MwPhysicsTransmissionEngineState es_saved=es;
    MwPhysicsTransmissionSpeedWheel wheels_saved[4];memcpy(wheels_saved,coupled,sizeof coupled);
    assert(!mw_physics_transmission_engine_mechanical_step(&ep,&ei,&es,coupled));
    assert(!memcmp(&es_saved,&es,sizeof es) && !memcmp(wheels_saved,coupled,sizeof coupled));
    MwPhysicsTransmissionAutomaticParams automatic_params={&tables,gears,4,.25f,1000};
    MwPhysicsTransmissionAutomaticInput automatic_input={.seconds=.1f,.raw_throttle=1,
        .applied_throttle=1,.input_present=1,.automatic_enabled=1,
        .contacted={1,1,1,1},.longitudinal_slip={0,0,0,4}};
    MwPhysicsTransmissionAutomaticState automatic_state={{2,0,0},0,2,0};
    MwPhysicsTransmissionGearEvent gear_event;
    assert(mw_physics_transmission_automatic_step(&automatic_params,&automatic_input,&automatic_state,&gear_event));
    assert(automatic_state.shift.gear_slot==2 && !gear_event.accepted);
    automatic_input.longitudinal_slip[3]=-10;
    assert(mw_physics_transmission_automatic_step(&automatic_params,&automatic_input,&automatic_state,&gear_event));
    assert(automatic_state.shift.gear_slot==3 && gear_event.accepted && gear_event.previous_gear==2);
    assert(fabsf(automatic_state.shift.shift_delay-.4f)<.000001f && automatic_state.shift.clutch_state==2);
    automatic_state.cooldown=.5f;automatic_state.request=1;automatic_input.automatic_enabled=0;
    assert(mw_physics_transmission_automatic_step(&automatic_params,&automatic_input,&automatic_state,&gear_event));
    assert(automatic_state.cooldown==.4f);
    MwPhysicsTransmissionEngineStepParams step_params={.mechanical=ep,.nos=nos,.shift_speed=.25f};
    MwPhysicsTransmissionEngineStepInput step_input={.external=ei,.raw_throttle=1,
        .input_present=1,.automatic_enabled=1};
    MwPhysicsTransmissionEngineStepState step_state={.mechanical={.gear_slot=1,
        .clutch={2,0,0},.engine_omega=104.719765f,.reported_rpm=1000},.nos={1,0}};
    memset(coupled,0,sizeof coupled);
    assert(mw_physics_transmission_engine_step(&step_params,&step_input,&step_state,coupled,&gear_event));
    assert(step_state.mechanical.gear_slot==2 && step_state.mechanical.clutch.mode==1);
    assert(!gear_event.accepted && step_state.induction_boost==0 && step_state.scale_100==1);
    MwPhysicsTransmissionEngineStepState saved_step=step_state;
    step_params.induction.high_boost=.1f;
    assert(!mw_physics_transmission_engine_step(&step_params,&step_input,&step_state,coupled,&gear_event));
    assert(!memcmp(&saved_step,&step_state,sizeof saved_step));
    return 0;
}
