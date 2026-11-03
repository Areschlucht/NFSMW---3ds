#ifndef MW_PHYSICS_TRANSMISSION_AUTO_H
#define MW_PHYSICS_TRANSMISSION_AUTO_H
#include "mw_physics_transmission_policy.h"
typedef struct {
    MwPhysicsTransmissionShiftState shift;
    float cooldown;
    unsigned request,committed;
} MwPhysicsTransmissionAutomaticState;
typedef struct {
    const MwPhysicsTransmissionShiftTables *tables;
    const float *ratios;
    size_t count;
    float shift_speed,idle_rpm;
} MwPhysicsTransmissionAutomaticParams;
typedef struct {
    float seconds,raw_throttle,applied_throttle,shaft_omega;
    unsigned input_present,automatic_enabled,vehicle_gate_48;
    unsigned contacted[4];
    float longitudinal_slip[4];
} MwPhysicsTransmissionAutomaticInput;
typedef struct {unsigned accepted,previous_gear,new_gear,automatic;} MwPhysicsTransmissionGearEvent;
/* Original auto policy80255AD4 and post-input timer update8025750C. Accepted
 * gear-commit state writes from8025617C are included; the optional game event
 * allocation/dispatch is represented by the returned record, not emulated.
 * Neutral1 ->first2 is the original direct assignment and emits no event. */
bool mw_physics_transmission_automatic_step(const MwPhysicsTransmissionAutomaticParams *,
    const MwPhysicsTransmissionAutomaticInput *,MwPhysicsTransmissionAutomaticState *,
    MwPhysicsTransmissionGearEvent *);
#endif
