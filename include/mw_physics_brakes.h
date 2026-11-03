#ifndef MW_PHYSICS_BRAKES_H
#define MW_PHYSICS_BRAKES_H
#include <stdint.h>
/* Direct original stages; input routing/assists and contact solver remain
 * separate. Values are not an independent complete vehicle physics model. */
typedef struct {
    float normal_raw[2], handbrake_raw, lock_multiplier[2];
} MwPhysicsBrakeAttributes;
typedef struct {
    float normal_scale, handbrake_scale, lock_scale, angular_resistance, inertia;
} MwPhysicsBrakeCalibration;
typedef struct {
    float radius_m, normal_input, handbrake_input, angular_speed;
    float drive_torque, accumulated_brake_torque, angular_acceleration;
    uint32_t axle, locked, direction;
} MwPhysicsWheelBrakeState;
/* Original initialized tuning globals at8041F350..8041F364:4,10,1.2,100,2,10.
 * The unused +16 value belongs to a later tire-spin damping stage. */
extern const MwPhysicsBrakeCalibration mw_physics_original_brake_calibration;
/* Mirrors 802462D0; contact_force_argument is the original f1 argument.
 * Lock threshold includes torque+angular-resistance and zeros wheel speed. */
void mw_physics_brake_lock_raw(const MwPhysicsBrakeAttributes *,const MwPhysicsBrakeCalibration *,MwPhysicsWheelBrakeState *,float contact_force_argument);
/* Mirrors802463B0: direction0/1/2 prevents a spin step crossing through zero. */
void mw_physics_wheel_spin_transition(MwPhysicsWheelBrakeState *);
/* Mirrors relevant state of8024644C (original no-contact/free-spin branch).
 * This is not the contact tire solver or whole-vehicle brake deceleration. */
void mw_physics_free_wheel_brake_step(const MwPhysicsBrakeAttributes *,const MwPhysicsBrakeCalibration *,MwPhysicsWheelBrakeState *,float dt);
#endif
