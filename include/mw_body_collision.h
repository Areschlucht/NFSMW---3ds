#ifndef MW_BODY_COLLISION_H
#define MW_BODY_COLLISION_H
/* Narrow original80083680 tangent-momentum correction stage used by static
 * body contact core80083C74. Coefficients are original solver order:
 * [0]=sliding scale,[1]=sticking threshold. Caller supplies signed normal
 * component and the original normalized contact normal; separating contacts
 * return0. Returns original branch0/1/2, or−1 invalid input.
 * This is NOT an impulse/chassis solver: do not apply it as a car velocity
 * bounce. Original inertia iteration is exposed by mw_body_collision_response.h; actual
 * shape/contact producers remain separate integration requirements.
 */
int mw_body_collision_tangent_response(const float coefficients[2],
    const float contact_momentum[3],const float contact_normal[3],
    float signed_normal_component,float correction[3]);
typedef struct {
    float (*sqrt_raw)(float squared,void *context);
    void *context;
} MwBodyCollisionMath;
/* Original80237D00..80237E24 world-contact coefficient producer:
 * source WALL_FRICTION[0] is the sticking coefficient; second (if present)
 * is limited by the first for sliding, then both multiply actual surface
 * WORLD_FRICTION. Return0 success,−1 unsupported/malformed input.
 */
int mw_body_collision_world_friction(const float *source_wall_friction,
    unsigned count,float surface_world_friction,float solver_coefficients[2]);
/* Explicit math boundary for original-model comparisons. Runtime default uses
 * the independent original80193420 functional estimate/Newton stage. FPSCR
 * exceptions/control flags and full body integration are outside this helper.
 */
int mw_body_collision_tangent_response_with_math(const float coefficients[2],
    const float contact_momentum[3],const float contact_normal[3],
    float signed_normal_component,float correction[3],const MwBodyCollisionMath *math);
#endif
