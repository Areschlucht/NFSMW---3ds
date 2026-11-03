#ifndef MW_PHYSICS_TRANSMISSION_DISTRIBUTION_H
#define MW_PHYSICS_TRANSMISSION_DISTRIBUTION_H
#include "mw_physics_transmission.h"
typedef struct {
    float angular_speed,spring_compression,longitudinal_slip,last_lateral_velocity;
    float drive_torque,grip_factor;
    unsigned locked;
} MwPhysicsTransmissionWheel;
typedef struct {
    float engine_output_torque,torque_split,differential[3];
    float body_local_lateral_velocity,body_local_forward_velocity,steering;
    unsigned assist_flags;
    float assist_strength;
} MwPhysicsTransmissionDistribution;
/* Original SuspensionRacer8024A00C: center/axle differential, steering-sensitive
 * drive/grip redistribution and per-wheel torque accumulation. No allocations.
 * angle_turns should be mw_physics_contact_angle_turns (original80193BB4), not
 * atan2 radians. It is required only when the original steering-assist branch
 * reaches its angle test. Unproved/missing input rejects transactionally.
 * Caller runs wheel preparation first; this function changes drive_torque and
 * grip_factor only, not angular velocity or suspension state. */
bool mw_physics_transmission_distribute(const MwPhysicsTransmissionDistribution *,
    MwPhysicsTransmissionWheel wheels[4],float (*angle_turns)(float,float));
#endif
