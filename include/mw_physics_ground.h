#ifndef MW_PHYSICS_GROUND_H
#define MW_PHYSICS_GROUND_H
#include "mw_physics_contact_frame.h"
#include "mw_physics_suspension.h"
/* Persistent subset of the original wheel state, in source-native metres,
 * seconds and Y-up world coordinates. These are not viewer coordinates. */
typedef struct {
    MwPhysicsContactWheel tire;
    float compression,air_seconds;
} MwPhysicsGroundWheel;
typedef struct {
    MwPhysicsContactVector normal,steered_direction,point_velocity,body_up;
    float query_relative_plane_w,vehicle_speed_mps,body_mass,seconds;
    float additional_ride_height_inches,antiroll_force;
} MwPhysicsGroundInput;
typedef struct {
    MwPhysicsSuspensionOutput suspension;
    MwPhysicsContactFrame frame;
    MwPhysicsContactVector world_force;
} MwPhysicsGroundOutput;
/* Composes original8024AA28..AECC in its recovered order. Before calling:
 * prepare ALL wheels, distribute engine torque using PREVIOUS wheel state,
 * then route brake/handbrake/assist inputs. Ground normal/w must come from
 * the actual world triangle query at this wheel's query point. Caller's
 * snapshot of all four previous compressions supplies antiroll_force.
 * No scheduler, steering law, material persistence, body impulses or guessed
 * per-step grip factors are hidden here. Power/math callbacks retain the
 * independent original-executable comparison boundaries. */
bool mw_physics_ground_wheel_step(MwPhysicsGroundWheel *,const MwPhysicsGroundInput *,const MwPhysicsSuspensionAxle *,const MwPhysicsContactParameters *,MwPhysicsGroundOutput *,const MwPhysicsSuspensionMath *,const MwPhysicsContactMath *);
/* Snapshot all previous compressions before changing any wheel. */
void mw_physics_ground_antiroll(const MwPhysicsGroundWheel wheels[4],const float raw_swaybar_stiffness[2],float output_forces[4]);
#endif
