#ifndef MW_ORIGINAL_PLAYER_INPUT_H
#define MW_ORIGINAL_PLAYER_INPUT_H
#include <stdbool.h>
#include <stdint.h>
#include "mw_physics_ground.h"
enum { MW_PLAYER_INPUT_HISTORY=33 };
/* Original ISteeringWheel::SteeringType from matching DWARF1. */
enum { MW_PLAYER_GAMEPAD=0, MW_PLAYER_WHEEL_SPEED_SENSITIVE=1,
       MW_PLAYER_WHEEL_SPEED_INSENSITIVE=2 };
typedef struct {
    float values[MW_PLAYER_INPUT_HISTORY],times[MW_PLAYER_INPUT_HISTORY];
    float sum,average,seconds;
    uint32_t capacity,count,cursor,oldest;
} MwPlayerInputAverage;
typedef struct {
    float angle_degrees,previous_input,gain_history;
    MwPlayerInputAverage input_average,rate_average;
} MwPlayerSteeringState;
typedef struct {
    float raw_steering,forward_speed,throttle,brake,handbrake,seconds,time;
    float tire_steering,rear_slip_angle_turns[2],blend_100,fade_1ac;
    /* Exact external ISteeringWheel::SteeringType result (0,1,2).
       Effect0 is actual GetTunings().Value[STEERING], when non-null. */
    uint32_t interface_mode;
    bool effect_present;
    float effect_0;
} MwPlayerSteeringInput;
/* Source constructors802473FC..47448:0.55s×60 and0.15s×60 sample windows.
   The caller supplies actual game-time float and common state; no clock/input
   producer or rigid-body controller is fabricated by this arithmetic module. */
bool mw_player_steering_init(MwPlayerSteeringState *);
/* Complete802484F8/802486EC/80248984 arithmetic including source uniform and
   paired-point curves, update order and both time-window averages. Failure
   leaves state/output unchanged. Output is source steering TURNS. */
bool mw_player_steering_step(MwPlayerSteeringState *,const MwPlayerSteeringInput *,float *turns);
/* Original802490B0 array getter. Borrow the actual tires.YAW_CONTROL samples;
   source interface presence/max-speed are explicit. Empty/default attribute
   fallback is rejected until its actual default provider is supplied. */
bool mw_player_yaw_control(const float *samples,uint32_t count,float speed,
    bool interface_present,float max_speed,float *out);

typedef struct {
    float handbrake_history_1b8;
} MwPlayerRouteState;
typedef struct {
    float forward_speed,slip_angle_9c,handbrake,brake,throttle,seconds;
    float blend_100,disable_110,steering,body_24,source_speed_bc;
    float grip_d0,grip_d4,source_e4_70,yaw_control;
    uint32_t wheel_disable_mask,flags_c4,mode_c8,mode_cc;
    /* effect=Physics::Tunings; controller=IPlayer; byte2A=Handling. */
    bool effect_present,controller_present,controller_byte_2a,settings_present;
    float effect_4,effect_8;
} MwPlayerRouteInput;
typedef struct { float maximum_positive_slip;unsigned maximum_slip_wheel; } MwPlayerRouteResult;
/* Exact scalar wheel-routing prefix80249910..80249D80. source_e4_70 is
   transmission.TORQUE_SPLIT; common24/9C/D0/D4 are bodyforwardY, local slip
   turns, NOS boost and shift boost respectively.
   yaw_control must come from original tires.YAW_CONTROL speed getter802490B0.
   Original later traction-state update80248B5C, flagC4 multiplier and yaw/body
   forces802492A0 are NOT silently replaced with no-ops by this prefix API. */
bool mw_player_route_wheels(MwPlayerRouteState *,const MwPlayerRouteInput *,
    MwPhysicsGroundWheel wheels[4],MwPlayerRouteResult *);
typedef struct {uint32_t stage;float timer,scale,quiet_time;} MwPlayerTractionState;
typedef struct {uint32_t stage;float ramp;} MwPlayerYawState;
typedef struct {
    MwPlayerRouteState route;
    MwPlayerTractionState traction;
    MwPlayerYawState yaw;
} MwPlayerAssistState;
typedef struct {
    MwPlayerRouteInput routing;
    const float *yaw_samples;uint32_t yaw_count;
    /* SuspensionRacer::mTransmission, supplied by the engine implementation. */
    bool engine_interface_present;
    /* source_a4 is proved RigidBody::GetInertiaTensor().y (common+A4). */
    float engine_max_speed,averaged_steering,local_angular_y,body_up[3],source_a4;
    uint32_t contact_count;
} MwPlayerAssistInput;
typedef struct {
    MwPlayerRouteResult route;
    bool torque_present,controller_a4_present;
    float torque_world[3],controller_a4_argument;
} MwPlayerAssistOutput;
/* Complete802498B4 arithmetic: prefix -> source traction80248B5C or reset ->
   C4 flag grip suffix -> source yaw state/torque802492A0. Outputs represent
   original external AddTorqueWorld and controller+A4 calls in that order's
   actual placement (controller command first when both present). The caller
   must apply them, not silently omit them. No rigid-body integration here. */
bool mw_player_input_route(MwPlayerAssistState *,const MwPlayerAssistInput *,
    MwPhysicsGroundWheel wheels[4],MwPlayerAssistOutput *);
/* Original LocalPlayer::ChargeGameBreaker80289384; no body mutation. */
bool mw_player_charge_gamebreaker(float *charge,float amount);
/* Original sinf/cosf kernels/reduction, validated through abs(x)<=400.
   Covers original wheel angles and career sabotage max377rad. */
bool mw_player_source_sincos(float x,float *sine,float *cosine);
/* Callback forms return NaN outside the documented verified domain. */
float mw_player_source_sine(float x);
float mw_player_source_cosine(float x);
bool mw_player_steer_directions(const float matrix[16],float turns,float track,
    float wheel_base,MwPhysicsContactVector out[4]);
typedef struct {float collision_timer,wall_nose_turn,wall_side_turn,last_ground_time;} MwPlayerCollisionState;
typedef struct {
    uint32_t flags;
    bool owner_is_object_b,collision_body_present;
    float position[3],normal[3],closing_velocity[3],object_a_velocity[3];
    float impulse_a,impulse_b;
    float body_position[3],body_forward[3],body_right[3],body_dimension[3];
    float signed_speed,source_time;
} MwPlayerCollisionInput;
typedef struct {
    float body_matrix[16],angular_velocity_world[3],steering,throttle;
    uint32_t gear,contact_count;
} MwPlayerWallSteeringInput;
typedef struct {uint32_t count;float angular_velocity_world[2][3];} MwPlayerWallSteeringOutput;
/* Actual OnCollision8024812C and DoWallSteer80248E48. Input flags are the
   original Collision::Info1C word; no generated collision is assumed here. */
bool mw_player_collision_event(MwPlayerCollisionState *,const MwPlayerCollisionInput *);
bool mw_player_wall_steering(const MwPlayerCollisionState *,const MwPlayerWallSteeringInput *,MwPlayerWallSteeringOutput *);
/* Source tick-start timer decay and tick-END wall-term reset. */
bool mw_player_collision_begin(MwPlayerCollisionState *,float seconds);
void mw_player_collision_end(MwPlayerCollisionState *);
#endif
