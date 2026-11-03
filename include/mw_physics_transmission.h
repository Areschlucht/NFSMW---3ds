#ifndef MW_PHYSICS_TRANSMISSION_H
#define MW_PHYSICS_TRANSMISSION_H
#include "mw_physics_engine.h"
#include <stdbool.h>
/* Original EngineRacer 0x8025546C. The curve uses original engine database
 * torque units; this wrapper applies original 1.3558 pound-foot -> Nm factor.
 * boost_9c and scale_100 remain explicit original state values, not guessed
 * nitrous/traction controls. Vehicle callback mode6 bypasses scale_100. */
float mw_physics_transmission_output_torque_nm(const MwPhysicsEngineCurve *,
    float rpm,float boost_9c,float scale_100,unsigned vehicle_mode);
/* Original 0x802557E8. Pass ENGINE_BRAKING samples in curve.torque and its
 * original IDLE/MAX_RPM/RED_LINE. torque_argument unit is preserved; the
 * surrounding clutch/torque-to-wheel application is separate.
 * Count1 returns its unbounded sample; count>1 clamps interpolation to[0,1].
 * Empty/invalid curves return NaN rather than calling original default memory. */
float mw_physics_transmission_engine_braking(const MwPhysicsEngineCurve *,
    float torque_argument,float rpm);
/* Original reported-RPM stage0x80256B8C. This is a bounded falling-RPM
 * rate followed by original45/55 smoothing, not actual shaft-RPM integration.
 * damping_mode is the original caller predicate; gear1 is neutral. Inertia
 * comes from original engine accessor80223AFC, not an arbitrary tuning gain. */
float mw_physics_transmission_reported_rpm(unsigned damping_mode,unsigned gear_slot,
    float seconds,float previous_rpm,float shaft_rpm,float inertia);
typedef struct {
    unsigned gear_slot;
    unsigned clutch_state;
    float shift_delay;
} MwPhysicsTransmissionShiftState;
/* Original gear commit0x8025607C. This accepts an already authorized gear
 * request, not the original automatic/manual request policy or event system.
 * Downshifts use SHIFT_SPEED*new_ratio*0.25; upshifts use SHIFT_SPEED*new_ratio.
 * Clutch state0 changes to2; other state values are retained. */
bool mw_physics_transmission_commit_gear(MwPhysicsTransmissionShiftState *,
    int requested_slot,const float *ratios,size_t count,float shift_speed);
/* Original80223AFC: FLYWHEEL_MASS schema field maps to effective engine inertia.
 * This is distinct from the original per-wheel inertia10. Neutral is gear1. */
float mw_physics_transmission_inertia(float flywheel_mass,unsigned gear_slot);
typedef struct {
    unsigned gear_slot,clutch_state;
    float engine_omega,shaft_omega,shaft_acceleration;
    float engine_inertia,net_engine_torque,driveline_ratio;
    float torque_split,contact_fraction,shift_coupling;
    float previous_slip_rpm;
} MwPhysicsTransmissionClutchInput;
typedef struct {
    float wheel_torque,engine_reaction_torque,slip_rpm;
    unsigned negative_engine_torque;
} MwPhysicsTransmissionClutchResult;
/* Numerical clutch core80257CC8..80257EF8, NOT the surrounding whole-engine
 * state machine. Clutch0 locked,1 slipping,2 disengaged as observed in this core.
 * Initialized globals max omega difference300 and coupling20 are explicit args.
 * Caller must supply actual source-derived gear/shaft/contact/input producers. */
bool mw_physics_transmission_clutch_core(const MwPhysicsTransmissionClutchInput *,
    float maximum_omega_difference,float coupling,MwPhysicsTransmissionClutchResult *);
typedef struct {
    unsigned mode;
    float remaining_seconds,duration_seconds;
} MwPhysicsTransmissionClutchState;
/* Original countdown/coupling then engagement transitions, in that order.
 * Inputs engine/shaft angular speeds are radians/sec; neutral gear1.
 * Returns the coupling computed before this frame's mode transition. */
bool mw_physics_transmission_clutch_update(MwPhysicsTransmissionClutchState *,
    unsigned gear_slot,float seconds,float engine_omega,float shaft_omega,
    float throttle,float idle_rpm,float *coupling);
typedef struct {
    float angular_speed[2];
    unsigned contacted[2];
    float base_ratio,locking;
} MwPhysicsTransmissionDifferentialInput;
/* Original80249EA4 torque-ratio leaf, used for center and axle differential.
 * Override/noncontact/nonpositive locking uses original base split unchanged;
 * the active branch clamps its two outputs independently, not renormalized. */
bool mw_physics_transmission_differential(const MwPhysicsTransmissionDifferentialInput *,
    bool override_open,float output_ratios[2]);
typedef struct {
    float angular_speed,spring_compression,traction_factor;
    float previous_longitudinal_velocity,radius_m;
    unsigned locked;
} MwPhysicsTransmissionSpeedWheel;
/* Original Racer802479A0 effective wheel speed for engine coupling. A loaded,
 * nonslipping wheel uses prior contact forward velocity/radius, not raw spin. */
float mw_physics_transmission_engine_wheel_omega(const MwPhysicsTransmissionSpeedWheel *);
/* Original8025625C selects a driven-axle average. direction_filtered=false
 * selects the largest absolute average; true selects the forward max/reverse
 * min, constrained to the commanded gear direction. */
float mw_physics_transmission_driven_omega(const MwPhysicsTransmissionSpeedWheel [4],
    float torque_split,unsigned gear_slot,bool direction_filtered);
typedef struct {
    unsigned gear_slot,clutch_state;
    float seconds,engine_omega,engine_rpm,net_engine_torque,reaction_torque;
    float engine_inertia,throttle,clutch_slip,idle_rpm,optimal_rpm;
    float minimum_omega,maximum_omega;
} MwPhysicsTransmissionShaftInput;
typedef struct {
    float angular_speed,angular_acceleration,reaction_torque;
} MwPhysicsTransmissionShaftResult;
/* Original shaft integration8025817C..80258298, with launch-clutch reaction
 * attenuation and explicit original speed limits. engine_rpm is the earlier
 * frame sample at80257A24; do not substitute requested/reported RPM. The
 * caller must supply the original upper-limit selector and peak-torque RPM.
 * This is the actual angular update, not the complete EngineRacer pipeline. */
bool mw_physics_transmission_shaft_step(const MwPhysicsTransmissionShaftInput *,
    MwPhysicsTransmissionShaftResult *);
/* Original802565C0: synchronize powered wheel speeds to a target while
 * preserving axle differences above40mph unless both axle wheels are airborne.
 * vehicle_speed_128 is Vehicle getter8022E1D0's source scalar (m/s conversion
 * factor2.23699 is applied by the original function). Writes raw angular_speed;
 * reads effective engine-coupling speed through the original wheel accessor. */
bool mw_physics_transmission_sync_wheels(MwPhysicsTransmissionSpeedWheel [4],
    float torque_split,unsigned gear_slot,float target_omega,float vehicle_speed_128);
/* Original80256A08: cap only airborne powered-wheel effective speeds to the
 * signed engine limit. A wheel rotating against the limit is set to zero. */
bool mw_physics_transmission_cap_airborne_wheels(MwPhysicsTransmissionSpeedWheel [4],
    float torque_split,float signed_limit_omega);
#endif
