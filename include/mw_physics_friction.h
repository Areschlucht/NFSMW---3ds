#ifndef MW_PHYSICS_FRICTION_H
#define MW_PHYSICS_FRICTION_H
/* Original contacted-wheel friction limit stage80246A38..80246B10.
 * Caller supplies magnitude from the original math stage for separately scaled
 * longitudinal/lateral forces. Keeping that boundary explicit avoids pretending
 * a host sqrt matches Gekko's reciprocal-estimate-based implementation. */
typedef struct {
    float longitudinal_force,lateral_force,normal_load,static_grip;
    float grip_factor,combined_factor,speed_factor,slip_budget,slip_speed;
    float traction_factor;
    int undo_torque_boost;
} MwPhysicsFrictionState;
void mw_physics_friction_limit_given_magnitude(MwPhysicsFrictionState *,float magnitude);
#endif
