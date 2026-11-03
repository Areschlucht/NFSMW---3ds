#ifndef MW_PHYSICS_TRANSMISSION_NOS_H
#define MW_PHYSICS_TRANSMISSION_NOS_H
#include <stdbool.h>
/* Original EngineRacer80256D9C timed NOS producer. Field names follow the
 * source schema, including NOS_CAPACITY used as the drain-time denominator. */
typedef struct {
    float disengage,torque_boost,capacity,recharge_min,recharge_max;
    float recharge_min_speed,recharge_max_speed;
} MwPhysicsTransmissionNosParams;
typedef struct {float charge,activity;} MwPhysicsTransmissionNosState;
typedef struct {
    float seconds,applied_throttle,vehicle_speed_128;
    unsigned gear_slot,requested,rev_block,recharge_inhibited,vehicle_mode_b8;
    unsigned unlimited_global,boost_interface_present;
    float boost_interface_scalar;
    unsigned tuning_present;
    float tuning_14;
} MwPhysicsTransmissionNosInput;
/* Returns the original torque multiplier. Does not consume a guessed refill
 * rate: original recharge time is interpolated in converted vehicle speed.
 * recharge_inhibited is the explicit preceding optional vehicle-object callback
 * result; its broader producer remains separate. Original callback/tuning data
 * must be selected from the actual physical RefSpecs and upgrade indices. */
bool mw_physics_transmission_nos_step(const MwPhysicsTransmissionNosParams *,
    const MwPhysicsTransmissionNosInput *,MwPhysicsTransmissionNosState *,float *scale);
#endif
