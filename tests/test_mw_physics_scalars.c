#include "mw_physics_engine.h"
#include "mw_physics_tires.h"
#include "mw_physics_brakes.h"
#include "mw_physics_drivetrain.h"
#include "mw_physics_grip.h"
#include "mw_physics_lateral.h"
#include "mw_physics_friction.h"
#include "mw_physics_contact.h"
#include "mw_physics_contact_scale.h"
#include "mw_physics_contact_frame.h"
#include "mw_physics_ground.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <string.h>
static uint32_t bits(float value){uint32_t result;memcpy(&result,&value,sizeof result);return result;}
int main(void)
{
    /* Compact scalar reference points, independently checked against the
     * supplied original PPC. These expose clamp/FMA/rounding differences. */
    const float torque[]={170,251,340,428,467,452,411,375,350};
    MwPhysicsEngineCurve curve={torque,9,800,9500,8500};
    assert(bits(mw_physics_engine_curve_raw(&curve,801))==0x432a1311);
    assert(bits(mw_physics_engine_curve_raw(&curve,8500))==0x43ba7e88);
    assert(bits(mw_physics_engine_curve_raw(&curve,10000))==0x43ba7e88);
    curve.count=1;assert(mw_physics_engine_curve_raw(&curve,1000)==0);
    MwPhysicsTireDimensions tires={{255,255},{40,40},{19,19}};
    assert(bits(mw_physics_tire_diameter_m(&tires,1))==0x3f2fc505);
    const float ratios[]={3.2f,0,4.1f,2.53f,1.67f,1.23f,1,.83f};
    assert(bits(mw_physics_requested_rpm(&tires,ratios,8,1,3.4f,800,8500,20))==0x44480001);
    assert(bits(mw_physics_requested_rpm(&tires,ratios,8,2,3.4f,800,8500,20))==0x45f48a0d);
    assert(bits(mw_physics_requested_rpm(&tires,ratios,8,2,3.4f,800,8500,-20))==0x45f48a0d);
    assert(isnan(mw_physics_requested_rpm(&tires,ratios,8,8,3.4f,800,8500,20)));
    MwPhysicsBrakeAttributes brakes={{475,600},925,{1,3}};
    MwPhysicsWheelBrakeState wheel={.radius_m=.3433f,.handbrake_input=1,.angular_speed=20,.axle=1,.direction=0};
    mw_physics_brake_lock_raw(&brakes,&mw_physics_original_brake_calibration,&wheel,0);
    assert(wheel.locked==1 && wheel.angular_speed==0);
    wheel.normal_input=0;wheel.handbrake_input=0;wheel.angular_speed=20;wheel.locked=1;
    mw_physics_brake_lock_raw(&brakes,&mw_physics_original_brake_calibration,&wheel,0);
    assert(wheel.locked==0 && wheel.angular_speed==20);
    wheel.angular_speed=-.01f;wheel.direction=0;mw_physics_wheel_spin_transition(&wheel);
    assert(wheel.angular_speed==0 && wheel.direction==1);
    /* Handbrake branch suppresses the original assist addition; this isolated
     * scalar does not establish all input-state axes or the complete solver. */
    assert(bits(mw_physics_rear_grip_assist_raw(.1f,1,30,1,0))==0x3f800000);
    assert(bits(mw_physics_rear_grip_assist_raw(.1f,0,30,1,0))==0x3f8ccccd);
    assert(mw_physics_lateral_curve_raw(&mw_physics_original_lateral_curves,4000,12.0f/360,1.225f,1)==9310.0f);
    assert(mw_physics_lateral_curve_raw(&mw_physics_original_lateral_curves,4000,14.0f/360,1.225f,1)==9310.0f);
    MwPhysicsFrictionState friction={.longitudinal_force=80,.lateral_force=60,.normal_load=40,.static_grip=1,.grip_factor=1,.combined_factor=1,.speed_factor=1,.slip_budget=1000,.slip_speed=0};
    mw_physics_friction_limit_given_magnitude(&friction,100);
    assert(friction.longitudinal_force==32 && friction.lateral_force==24);
    assert(bits(friction.traction_factor)==0x3ecccccd);
    MwPhysicsFrictionState tiny={.longitudinal_force=.0008f,.lateral_force=.0006f,.normal_load=0,.static_grip=1,.grip_factor=1,.combined_factor=1,.speed_factor=1,.slip_budget=1};
    mw_physics_friction_limit_given_magnitude(&tiny,.001f);
    assert(tiny.longitudinal_force==.0008f && tiny.lateral_force==.0006f);
    MwPhysicsContactParameters contact={.static_grip={2.2f,2.3f},.dynamic_grip={2,2},.grip_scale={1.175f,1.225f},.brakes={{475,600},925,{1,3}},.calibration={4,10,1.2f,100,10},.surface_lateral_grip=1,.surface_drive_grip=1,.surface_rolling_resistance=0};
    MwPhysicsContactWheel rolling;mw_physics_contact_wheel_init(&rolling,2,.3433f);
    rolling.normal_load=4000;rolling.previous_longitudinal_velocity=20;rolling.brake.angular_speed=20/.3433f;
    MwPhysicsContactInput input={1,20,20,4000,1.0f/120};
    mw_physics_contact_prepare(&rolling,.5f,1,1,0);rolling.brake.drive_torque=100;
    assert(mw_physics_contact_step(&rolling,&input,&contact,0));
    assert(bits(rolling.lateral_force)==0xc5d055ae && bits(rolling.longitudinal_force)==0x4391a52c);
    for(unsigned frame=0;frame<2;frame++){
        mw_physics_contact_prepare(&rolling,.5f,1,1,0);rolling.brake.drive_torque=100;rolling.brake.handbrake_input=1;
        assert(mw_physics_contact_step(&rolling,&input,&contact,0));
    }
    assert(rolling.brake.locked && rolling.brake.angular_speed==0);
    assert(fabsf(rolling.lateral_force-(-399.5009460449219f))<.001f);
    assert(fabsf(rolling.longitudinal_force-(-7990.01904296875f))<.002f);
    MwPhysicsContactScaleInput scale_input={20,0,0,0,0,0};MwPhysicsContactScales scales;
    mw_physics_contact_scales(&scale_input,&scales);assert(scales.slip_budget==71 && scales.grip_factor==2);
    /* Original8024AF4C..AFD0 golden point/torque at large world coordinates.
     * Simplifying the world subtraction to a local lever loses these bits. */
    const float matrix[16]={1,0,0,0,0,1,0,0,0,0,1,0,8192,4096,-16384,1};
    MwPhysicsContactVector mount={.67f,-.621f,1.43f},cg={0,-.2f,0},force={100,2000,-4000},point,moment;
    mw_physics_contact_force_moment(matrix,&mount,.05f,.2f,&cg,&force,&point,&moment);
    assert(bits(point.x)==0x460002ae && bits(point.y)==0x457ff3aa && bits(point.z)==0xc67ffa48);
    assert(bits(moment.x)==0xc40fcc80 && bits(moment.y)==0x45306a80 && bits(moment.z)==0x44ae9e58);
    /* Original compressed/steep free-spin branch resets airtime, whereas
     * zero compression accumulates it and preserves previous contact speed. */
    MwPhysicsGroundWheel ground={0};mw_physics_contact_wheel_init(&ground.tire,0,.3433f);
    ground.tire.previous_longitudinal_velocity=17;ground.air_seconds=2;
    MwPhysicsGroundInput ground_input={.normal={.995f,.1f,0},.steered_direction={0,0,1},.body_up={0,1,0},.seconds=1.0f/60,.body_mass=1300};
    MwPhysicsSuspensionAxle spring={.travel_inches=10,.ride_height_inches=10};MwPhysicsGroundOutput ground_output;
    assert(mw_physics_ground_wheel_step(&ground,&ground_input,&spring,&contact,&ground_output,0,0));
    assert(!ground_output.suspension.has_contact && ground.compression>0 && ground.air_seconds==0);
    assert(ground.tire.previous_longitudinal_velocity==17);
    ground_input.query_relative_plane_w=-1;
    assert(mw_physics_ground_wheel_step(&ground,&ground_input,&spring,&contact,&ground_output,0,0));
    assert(ground.compression==0 && ground.air_seconds==ground_input.seconds);
    return 0;
}
