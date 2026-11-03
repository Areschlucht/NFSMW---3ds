#ifndef MW_PHYSICS_CONTACT_FRAME_H
#define MW_PHYSICS_CONTACT_FRAME_H
#include "mw_physics_contact.h"
/* Original wheel frame/projection stages8024AA28..88 and8024ACFC..AD64.
 * Vectors use one common source-native world frame (Y-up in original collision
 * data). Reference direction is the original steered wheel direction, supplied
 * by its producer; this module does not invent steering geometry. */
typedef struct { float x,y,z; } MwPhysicsContactVector;
typedef struct {
    MwPhysicsContactVector lateral_axis,longitudinal_force_axis;
    float lateral_velocity,longitudinal_velocity;
    float normal_load_factor;
} MwPhysicsContactFrame;
void mw_physics_contact_frame(const MwPhysicsContactVector *normal,const MwPhysicsContactVector *reference_direction,const MwPhysicsContactVector *contact_velocity,MwPhysicsContactFrame *,const MwPhysicsContactMath *);
/* Original8024AD74..AE44: clamps lateral force to the one-step body-mass
 * limit and composes world force in original add order. Spring force acts
 * along body-up, not automatically along the road normal. */
void mw_physics_contact_world_force(const MwPhysicsContactFrame *,const MwPhysicsContactVector *body_up,float raw_spring_force,float body_mass,float seconds,float lateral_force,float longitudinal_force,MwPhysicsContactVector *);
/* Original wheel query kinematics8021C750..7D4. Matrix rows are body
 * right/up/forward/position, each with a fourth padding element. CG argument
 * is already rotated into a WORLD OFFSET, not a world position. */
float mw_physics_contact_normal_dot_up(const MwPhysicsContactVector *,const MwPhysicsContactVector *);
void mw_physics_contact_rotate_vector(const float body_matrix[16],const MwPhysicsContactVector *,MwPhysicsContactVector *);
void mw_physics_contact_point_velocity(const float body_matrix[16],const MwPhysicsContactVector *local_mount,const MwPhysicsContactVector *world_cg_offset,const MwPhysicsContactVector *world_linear_velocity,const MwPhysicsContactVector *world_angular_velocity,MwPhysicsContactVector *query_point,MwPhysicsContactVector *point_velocity);
/* Original8024AF4C..AFD0 applies force at the suspension-adjusted mount.
 * Ride height is the already converted metres value from the axle producer.
 * Preserve world-point subtraction order for native float cancellation. */
void mw_physics_contact_force_moment(const float body_matrix[16],const MwPhysicsContactVector *local_mount,float compression_m,float converted_ride_height_m,const MwPhysicsContactVector *world_cg_offset,const MwPhysicsContactVector *world_force,MwPhysicsContactVector *application_point,MwPhysicsContactVector *world_moment);
#endif
