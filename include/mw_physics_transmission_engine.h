#ifndef MW_PHYSICS_TRANSMISSION_ENGINE_H
#define MW_PHYSICS_TRANSMISSION_ENGINE_H
#include "mw_physics_transmission_policy.h"
#include "mw_physics_transmission_auto.h"
#include "mw_physics_transmission_nos.h"
/* Mechanical continuation of EngineRacer8025762C, after original input/timed
 * virtual stages. All persistent fields correspond to actual source state.
 * Gear requests/events and the input/timed stages remain caller-owned. */
typedef struct {
    unsigned gear_slot;
    MwPhysicsTransmissionClutchState clutch;
    float shift_delay,engine_omega,angular_acceleration,shaft_omega,slip_rpm;
    float reported_rpm,output_torque,applied_throttle,rev_modulation_deadline;
    unsigned negative_engine_torque,shift_request;
} MwPhysicsTransmissionEngineState;
typedef struct {
    MwPhysicsEngineCurve torque,engine_braking;
    const float *ratios,*gear_efficiency;
    size_t gear_count;
    float flywheel_mass,final_gear,torque_split,torque_converter,clutch_slip;
    float peak_raw_torque,peak_torque_rpm;
    const MwPhysicsTransmissionShiftTables *shift_tables;
} MwPhysicsTransmissionEngineParams;
typedef struct {
    float seconds,applied_throttle,boost_9c,scale_100;
    unsigned vehicle_mode_b8,vehicle_gate_48;
    float vehicle_scalar_58,vehicle_speed_128;
    unsigned contact_count,boost_interface_present;
    float boost_interface_scalar;
    /* Original wheel+F0 values, used by80256484; signed m/s, no abs. */
    float longitudinal_slip[4];
} MwPhysicsTransmissionEngineInput;
/* Executes the source mechanical/state chain802577A8..8025845C. Writes wheel
 * raw angular speeds in the original sync/cap positions. Requires positive dt.
 * Explicit gate: active rev modulation (state deadline>0) is not yet ported;
 * rejects transactionally rather than silently omitting that original branch.
 * Inputs are outputs of the preceding original input/timed stages, not raw pad
 * throttle. Caller must not claim this phase alone is the complete engine. */
bool mw_physics_transmission_engine_mechanical_step(
    const MwPhysicsTransmissionEngineParams *,const MwPhysicsTransmissionEngineInput *,
    MwPhysicsTransmissionEngineState *,MwPhysicsTransmissionSpeedWheel [4]);
typedef struct {
    MwPhysicsTransmissionEngineParams mechanical;
    MwPhysicsTransmissionNosParams nos;
    MwPhysicsTransmissionInduction induction;
    float shift_speed;
    size_t speed_limiter_count;
} MwPhysicsTransmissionEngineStepParams;
typedef struct {
    MwPhysicsTransmissionEngineState mechanical;
    MwPhysicsTransmissionNosState nos;
    float cooldown,induction_amount,induction_display,induction_boost,scale_100;
    unsigned committed;
} MwPhysicsTransmissionEngineStepState;
typedef struct {
    MwPhysicsTransmissionEngineInput external;
    MwPhysicsTransmissionNosInput nos;
    float raw_throttle;
    unsigned input_present,automatic_enabled,rev_block;
} MwPhysicsTransmissionEngineStepInput;
/* Coherent source order: raw throttle/rev gate ->timed NOS ->disabled induction
 * reset ->automatic policy/timers ->mechanical continuation. This supported
 * subset matches canonical careerstart/default induction and empty SPEED_LIMITER.
 * Positive induction boost, nonempty RPM limiter, or active rev modulation reject
 * transactionally until their original producers are ported. Source-derived
 * RefSpec/upgrade selection and scheduler remain mandatory caller gates.
 * NOS nested input supplies request/recharge/tuning/unlimited/boost controls;
 * dt/throttle/gear/mode/speed are overwritten from the shared step context. */
bool mw_physics_transmission_engine_step(const MwPhysicsTransmissionEngineStepParams *,
    const MwPhysicsTransmissionEngineStepInput *,MwPhysicsTransmissionEngineStepState *,
    MwPhysicsTransmissionSpeedWheel [4],MwPhysicsTransmissionGearEvent *);
#endif
