#ifndef MW_VEHICLE_DYNAMICS_H
#define MW_VEHICLE_DYNAMICS_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "mw_physics_ground.h"
#include "mw_physics_contact_geometry.h"
#include "mw_physics_contact_scale.h"
#include "mw_physics_transmission_distribution.h"
/* Original component values selected through one explicit pvehicle RefSpec.
   This is a wheel-force stage, not an alternate tuned positional controller. */
typedef struct {
    uint32_t physical_key,tires_key,brakes_key,chassis_key,transmission_key;
    float mass;
    MwPhysicsTireDimensions dimensions;
    MwPhysicsSuspensionAxle axles[2];
    MwPhysicsContactParameters contact;
    float track_width[2],front_axle,wheel_base,swaybar[2],steering;
    float torque_split,differential[3];
} MwVehicleDynamicsParams;
typedef struct { uint32_t physical_key;MwPhysicsGroundWheel wheels[4]; } MwVehicleDynamicsState;
typedef struct {
    float body_matrix[16];
    MwPhysicsContactVector world_cg_offset,linear_velocity,angular_velocity;
    float body_half_extent_y,seconds,speed_mps,additional_ride_height_inches;
    /* Actual producer outputs: mode/gear/effect/assist values are explicit. */
    MwPhysicsContactScaleInput scales;
    MwPhysicsTransmissionDistribution distribution;
    MwPhysicsContactVector wheel_direction[4];
} MwVehicleDynamicsInput;
typedef struct {
    bool present;
    MwPhysicsContactVector normal;
    float relative_plane_w,surface_lateral_grip,surface_drive_grip,surface_rolling_resistance;
} MwVehicleDynamicsQuery;
typedef struct {
    MwPhysicsGroundOutput ground[4];
    MwPhysicsContactVector mounts[4],query_point[4],point_velocity[4];
    MwPhysicsContactVector application_point[4],world_moment[4];
} MwVehicleDynamicsOutput;
typedef struct {
    /* Required original phases. NULL is rejected; no hidden no-op substitutes.
       Mechanical/aero body forces remain caller-owned in their original order. */
    bool (*mechanical)(void *,const MwVehicleDynamicsInput *,MwPhysicsGroundWheel [4]);
    bool (*route_inputs)(void *,const MwVehicleDynamicsInput *,MwPhysicsGroundWheel [4]);
    bool (*query)(void *,unsigned,const MwPhysicsContactVector *,const MwPhysicsContactVector *,MwVehicleDynamicsQuery *);
    void *context;
    const MwPhysicsSuspensionMath *suspension_math;
    const MwPhysicsContactMath *contact_math;
} MwVehicleDynamicsHooks;
/* NDP1 profile sidecar; copies scalars, no borrowed bytes or allocation. */
bool mw_vehicle_dynamics_params_open(MwVehicleDynamicsParams *,const void *,size_t);
bool mw_vehicle_dynamics_init(MwVehicleDynamicsState *,const MwVehicleDynamicsParams *);
/* Prepare ALL -> caller mechanical -> original distribution using PREVIOUS
   wheel state -> caller original input routing -> prior-compression antiroll
   -> original wheel query kinematics/contact/application-point/moment.
   Failure leaves state/output unchanged. Callbacks must not mutate gameplay.
   Returned forces must still pass through original chassis accumulation,
   bottomout correction and integration; this function does not invent them. */
bool mw_vehicle_dynamics_step(const MwVehicleDynamicsParams *,const MwVehicleDynamicsInput *,MwVehicleDynamicsState *,MwVehicleDynamicsOutput *,const MwVehicleDynamicsHooks *);
/* Original80248A34 no-assist fallback only; NOT the normal player assist path. */
bool mw_vehicle_dynamics_steer_fallback(float tire_steering,int vehicle_mode,float raw_steering,float *turns);
/* Original80244C4C..CCD0 Ackermann angles: left then right, in radians.
   Input turns comes from actual original steering producer, not raw pad. */
bool mw_vehicle_dynamics_ackermann(float turns,float front_track,float wheel_base,float angles[2]);
#endif
