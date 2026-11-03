#ifndef MW_PHYSICS_CONTACT_H
#define MW_PHYSICS_CONTACT_H
#include <stdbool.h>
#include "mw_physics_brakes.h"
#include "mw_physics_lateral.h"
/* Complete scalar contacted-wheel routine recovered from original80246580.
 * Inputs are wheel-local components; this API never assumes a world/viewer axis.
 * Whole-car suspension, input assists, drivetrain and state producers remain
 * caller responsibilities. Native original dimensions are metres/seconds. */
typedef struct {
    MwPhysicsWheelBrakeState brake;
    unsigned wheel_index;
    float normal_load,lateral_force,longitudinal_force;
    float lateral_grip_factor,grip_factor,residual_torque;
    float previous_longitudinal_velocity,longitudinal_slip,traction_factor;
    float slip_angle_turns,last_lateral_velocity;
    float lateral_scale,longitudinal_scale,slip_budget,curve_scale,combined_factor;
    float coupling_13c; /* Original producer not yet identified. */
} MwPhysicsContactWheel;
typedef struct {
    float lateral_velocity,longitudinal_velocity;
    float vehicle_speed_mps; /* Original state+0xBC: length of body velocity vector. */
    float normal_force,seconds;
} MwPhysicsContactInput;
typedef struct {
    float static_grip[2],dynamic_grip[2],grip_scale[2];
    MwPhysicsBrakeAttributes brakes;
    MwPhysicsBrakeCalibration calibration;
    const MwPhysicsLateralCurves *lateral_curves;
    float surface_lateral_grip,surface_drive_grip,surface_rolling_resistance;
} MwPhysicsContactParameters;
/* Math boundary supports original-executable offline comparison. Runtime
 * defaults use original turn quantization and independent Gekko80193420
 * square-root stage; sine uses target libm.
 * Any callback may be NULL to select its runtime default. */
typedef struct {
    float (*sqrt_raw)(float,void *);
    float (*angle_turns)(float lateral,float longitudinal,void *);
    float (*sine)(float radians,void *);
    void *context;
} MwPhysicsContactMath;
void mw_physics_contact_wheel_init(MwPhysicsContactWheel *,unsigned wheel_index,float radius_m);
/* Mirrors the observable per-step resets of80246030. Supply proven per-step
 * scale producers; these arguments are deliberately not guessed internally. */
void mw_physics_contact_prepare(MwPhysicsContactWheel *,float slip_budget,float curve_scale,float grip_factor,float coupling_13c);
bool mw_physics_contact_step(MwPhysicsContactWheel *,const MwPhysicsContactInput *,const MwPhysicsContactParameters *,const MwPhysicsContactMath *);
/* Original8024644C no-contact path; preserves previous contact velocity and
 * residual torque, clears contact/load/slip outputs, integrates free spin. */
bool mw_physics_contact_free_step(MwPhysicsContactWheel *,const MwPhysicsContactParameters *,float seconds);
/* Original quantized atan2 wrapper80193BB4, output in turns, not radians. */
float mw_physics_contact_angle_turns(float lateral,float longitudinal);
#endif
