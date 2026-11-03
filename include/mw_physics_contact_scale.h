#ifndef MW_PHYSICS_CONTACT_SCALE_H
#define MW_PHYSICS_CONTACT_SCALE_H
/* Original preparation producers442B8/44590/44630 and47C30..80.
 * gear_slot is proven EngineRacer+0x88 (0 reverse,1 neutral,2 first).
 * vehicle_mode_c8 and effect_100 retain original raw state names until their
 * actor-interface producers are fully identified. */
typedef struct {
    float speed_mps;
    unsigned gear_slot;
    int vehicle_mode_c8;
    float effect_100;
    float additional_grip_argument;
    int include_additional_grip;
} MwPhysicsContactScaleInput;
typedef struct { float slip_budget,curve_scale,grip_factor,coupling_13c; } MwPhysicsContactScales;
void mw_physics_contact_scales(const MwPhysicsContactScaleInput *,MwPhysicsContactScales *);
#endif
