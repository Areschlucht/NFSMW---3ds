#ifndef MW_VEHICLE_RUNTIME_H
#define MW_VEHICLE_RUNTIME_H
#include "mw_vehicle_dynamics.h"
#include "mw_original_vehicle_mechanical.h"
#include "mw_original_player_input.h"
#include "mw_original_rigid_body.h"
#include "mw_physics_transmission_engine.h"
enum { MW_VEHICLE_RUNTIME_CURVE_CAPACITY=16 };
typedef struct {
    MwVehicleDynamicsParams wheels;
    MwVehicleMechanicalProfile mechanical;
    MwOriginalRigidBodyParameters body;
    float gravity,yaw_speed,local_cg[3],yaw_samples[16];
    uint32_t yaw_count;
    bool body_bound;
    uint32_t engine_key,transmission_key,induction_key,nos_key;
    float torque[16],braking[16],ratios[10],efficiency[10];
    MwPhysicsTransmissionShiftTables shifts;
    MwPhysicsTransmissionEngineStepParams powertrain;
} MwVehicleRuntimeParams;
typedef struct {
    uint32_t physical_key;
    uint32_t previous_contact_count;
    MwOriginalRigidBody body;
    MwVehicleDynamicsState wheels;
    MwPhysicsTransmissionEngineStepState engine;
    MwStoryEngine story_engine;
    MwPlayerSteeringState steering;
    MwPlayerAssistState assists;
    MwPlayerCollisionState collision;
    float seconds_elapsed;
} MwVehicleRuntimeState;
typedef struct {float throttle,brake,handbrake,steering,seconds,source_time;bool nos_requested,gear_requested;unsigned requested_gear_slot;} MwVehicleRuntimeInput;
enum {
    MW_RUNTIME_ENGINE_PRODUCERS=1,MW_RUNTIME_PLAYER_PRODUCERS=2,
    MW_RUNTIME_ROUTE_PRODUCERS=4,MW_RUNTIME_MECHANICAL_PRODUCERS=8,
    MW_RUNTIME_DISTRIBUTION_PRODUCERS=16,MW_RUNTIME_SCHEDULER=32,
    MW_RUNTIME_REQUIRED_PRODUCERS=63
};
typedef struct {
    uint32_t present;
    /* These original interface/timer/effect outputs are not raw input gains.
       Runtime overwrites only independently recovered body/wheel/raw fields. */
    MwPhysicsTransmissionEngineStepInput engine;
    MwPlayerSteeringInput steering;
    MwPlayerAssistInput assists;
    MwVehicleDynamicsInput wheels;
    MwVehicleMechanicalInput mechanical;
    bool engine_before_suspension,body_before_engine,gear_request_authorized;
    const MwPlayerCollisionInput *collision_events;
    size_t collision_event_count;
} MwVehicleRuntimeProduced;
typedef struct {
    /* Producer and body/world/query callbacks are required. Until source producers/
       constraints+collisions are implemented, the full backend stays gated.
       Caller contexts must not commit external gameplay during a trial step. */
    bool (*produce)(void *,const MwVehicleRuntimeParams *,const MwVehicleRuntimeState *,
        const MwVehicleRuntimeInput *,MwVehicleRuntimeProduced *);
    /* Optional override; NULL uses compared original Ackermann/trigonometry. */
    bool (*steer_directions)(void *,const float body_matrix[16],float turns,
        float front_track,float wheel_base,MwPhysicsContactVector out[4]);
    bool (*before_body_tick)(void *,MwOriginalRigidBody *,float seconds);
    bool (*after_body_tick)(void *,const MwOriginalRigidBody *,MwOriginalRigidBody *,float seconds);
    bool (*query)(void *,unsigned,const MwPhysicsContactVector *,const MwPhysicsContactVector *,MwVehicleDynamicsQuery *);
    void *context;
    const MwPhysicsSuspensionMath *suspension_math;
    const MwPhysicsContactMath *contact_math;
    const MwVehicleMechanicalMath *mechanical_math;
} MwVehicleRuntimeHooks;
typedef struct {
    MwVehicleDynamicsOutput contacts;
    MwVehicleMechanicalOutput mechanical;
    MwPlayerAssistOutput assists; /* ChargeGameBreaker command commits after success. */
    MwPhysicsTransmissionGearEvent gear_event;
    float steering_turns;
    unsigned body_force_calls;
    bool wake_event,engine_blown_event;
} MwVehicleRuntimeOutput;
/* Original DoWheelForces8024AED8..8024B168 late scalar/vector commands.
   Original contact-stage outputs are required; commands are not applied here. */
typedef struct {
    float body_matrix[16],local_angular_velocity[3],yaw_speed;
    uint32_t driver_style,previous_contact_count;
} MwVehicleRuntimeChassisInput;
typedef struct {
    bool wrench_present,raise_present,angular_velocity_present;
    float force[3],torque[3],raise_y,angular_velocity[3];
    uint32_t contact_count;
} MwVehicleRuntimeChassisOutput;
bool mw_vehicle_runtime_chassis_commands(const MwVehicleRuntimeChassisInput *,
    const MwVehicleDynamicsOutput *,MwVehicleRuntimeChassisOutput *);
/* NVR1 own-source parameter reader; copied data includes bounded curve arrays.
   Params must stay at one address while state uses its self-bound curve pointers. */
bool mw_vehicle_runtime_params_open(MwVehicleRuntimeParams *,const void *,size_t);
/* Body initialization is caller-supplied original physical state. No invented
   inertia, art-bounds mass proxy, default quaternion, gear or engine RPM. */
bool mw_vehicle_runtime_init(MwVehicleRuntimeState *,const MwVehicleRuntimeParams *,
    const MwOriginalRigidBody *,const MwPhysicsTransmissionEngineStepState *);
/* Entire call commits atomically. No bicycle/direct yaw/position edits. */
bool mw_vehicle_runtime_step(const MwVehicleRuntimeParams *,const MwVehicleRuntimeInput *,
    MwVehicleRuntimeState *,MwVehicleRuntimeOutput *,const MwVehicleRuntimeHooks *);
#endif
