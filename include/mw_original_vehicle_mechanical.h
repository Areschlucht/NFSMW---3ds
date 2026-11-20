#ifndef MW_ORIGINAL_VEHICLE_MECHANICAL_H
#define MW_ORIGINAL_VEHICLE_MECHANICAL_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "mw_physics_contact_frame.h"
/* Original chassis required-layout values, not visual car bounds. */
typedef struct {
    float drag_coefficient,aero_coefficient,aero_cg_percent;
    /* Initialized mutable globals8041F280,284,278,27C respectively. */
    float off_throttle_drag_multiplier,off_throttle_drag_height,
          aero_direction_exponent,aero_direction_minimum;
} MwVehicleMechanicalParams;
typedef struct {uint32_t physical_key,chassis_key;MwVehicleMechanicalParams params;} MwVehicleMechanicalProfile;
typedef struct {
    float body_matrix[16];
    MwPhysicsContactVector world_velocity,local_cg;
    float speed,throttle,contact_fraction;
    float drag_scale,downforce_scale,front_mount_z,rear_mount_z;
    bool effect_present;
    float effect_value; /* Actual optional effect blob+10, not a guessed boost. */
} MwVehicleMechanicalInput;
typedef struct {
    MwPhysicsContactVector force,world_point;
    uint32_t kind; /* 1drag,2downforce; original call order retained. */
} MwVehicleMechanicalForce;
typedef struct {uint32_t count;MwVehicleMechanicalForce forces[2];} MwVehicleMechanicalOutput;
typedef struct {
    /* Original powf result is carried by an FPR (promoted float). NULL uses
       the verified native positive branches; unsupported exponents reject. */
    double (*power)(double,double,void *);
    void *context;
} MwVehicleMechanicalMath;
/* Only initialized global defaults; chassis attributes remain caller supplied. */
void mw_vehicle_mechanical_calibration(MwVehicleMechanicalParams *);
/* MMP1/source-bound156-byte immutable profile; copies values, borrows nothing. */
bool mw_vehicle_mechanical_profile_open(MwVehicleMechanicalProfile *,const void *,size_t);
/* Original802455E0 ordered body-force stage. No body integration, wheel-state
   mutation or implicit accumulated force. Failure leaves output unchanged. */
bool mw_vehicle_mechanical(const MwVehicleMechanicalParams *,const MwVehicleMechanicalInput *,
    MwVehicleMechanicalOutput *,const MwVehicleMechanicalMath *);
#endif
