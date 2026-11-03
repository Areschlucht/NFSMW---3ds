#ifndef MW_PHYSICS_LATERAL_H
#define MW_PHYSICS_LATERAL_H
/* Initialized original lateral-force curve family, indexed by two-degree
 * slip-angle steps and a six-point load domain0..10. Original802460B0.
 * This stage is upstream of combined-slip saturation and surface multipliers. */
typedef struct { float samples[7][6]; } MwPhysicsLateralCurves;
extern const MwPhysicsLateralCurves mw_physics_original_lateral_curves;
/* slip_angle_turns must be nonnegative, as in the original caller. The raw
 * force argument, grip_scale and wheel+0x128 scale retain original semantics;
 * this alone is not a complete tire force/contact solver. */
float mw_physics_lateral_curve_raw(const MwPhysicsLateralCurves *,float force_argument,float slip_angle_turns,float grip_scale,float wheel_scale);
#endif
