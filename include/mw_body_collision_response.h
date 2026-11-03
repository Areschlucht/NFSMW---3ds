#ifndef MW_BODY_COLLISION_RESPONSE_H
#define MW_BODY_COLLISION_RESPONSE_H
/* Explicit producer inputs for original static-contact core 80083C74.
 * All vectors share the ORIGINAL body/world basis; orientation is the original
 * row-major 4x4 matrix (vector transform uses its upper-left 3x3). Inertia is
 * the source diagonal, NOT inverse inertia. No BMW mass/tensor inference here.
 * This stage consumes an actual original shape contact; it does not generate
 * contacts, resolve penetration, advance positions, or implement dynamic cars.
 */
typedef struct {
    float mass, inertia[3], local_cg[3], position[3], orientation[16];
    float velocity[3], angular_velocity[3], moment_scale[3];
    /* State+10C: original constructor sets zero; physical label unresolved. */
    float extra_normal_accumulation;
} MwBodyCollisionState;
typedef struct {
    float point[3], normal[3], friction[2]; /* friction: sliding, sticking */
    unsigned passes; /* original static-world caller uses 16 */
} MwBodyCollisionInput;
typedef struct {
    float velocity[3], angular_velocity[3];
    float initial_normal_velocity[3], initial_tangent_velocity[3];
    float normal_impulse[3], initial_friction_impulse[3];
    unsigned friction_branch, iterations;
} MwBodyCollisionResponse;
/* Return original hit flag 0/1, -1 for unsupported/nonfinite inputs. Output
 * remains unchanged on error. Preserves original first observation-only pass.
 * Default original sqrt estimate/Newton helper; FPSCR and PS underflow modes
 * are outside this portable functional model. */
int mw_body_collision_response(const MwBodyCollisionState *state,
    const MwBodyCollisionInput *contact,MwBodyCollisionResponse *out);
#endif
