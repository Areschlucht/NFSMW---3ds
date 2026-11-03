#ifndef MW_PHYSICS_SUSPENSION_H
#define MW_PHYSICS_SUSPENSION_H
#include <stdbool.h>
/* Original chassis raw attributes. Consumer8024A730..7B0 proves conversion of
 * spring/shock rates by175.1268 and ride/travel/valving by0.0254. */
typedef struct {
    float spring_stiffness,spring_progression,shock_stiffness,shock_ext_stiffness;
    float shock_valving,shock_digression,travel_inches,ride_height_inches;
    float shock_blowout;
} MwPhysicsSuspensionAxle;
typedef struct {
    float query_relative_plane_w,normal_dot_body_up,previous_compression;
    float seconds,additional_ride_height_inches,antiroll_force,body_mass;
} MwPhysicsSuspensionInput;
typedef struct {
    float compression,compression_velocity,spring_force,damper_force,normal_force,penetration_excess;
    bool has_contact,bottomed_out;
} MwPhysicsSuspensionOutput;
typedef struct {float (*power)(float,float,void *);void *context;} MwPhysicsSuspensionMath;
/* Original8024AACC..AC88 scalar spring/damper/load law. Plane w comes from
 * world_collision_ground_contact_plane, not an absolute worldplaneconstant. */
void mw_physics_suspension_load(const MwPhysicsSuspensionAxle *,const MwPhysicsSuspensionInput *,MwPhysicsSuspensionOutput *,const MwPhysicsSuspensionMath *);
/* Exact per-axle load transfer term8024A7B4..A858, applied before currentframe
 * compressions update. Sign follows original; not replaced by idealized math. */
void mw_physics_suspension_antiroll(const float previous_compressions[4],const float raw_swaybar_stiffness[2],float output_forces[4]);
#endif
