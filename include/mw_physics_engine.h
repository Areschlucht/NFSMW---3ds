#ifndef MW_PHYSICS_ENGINE_H
#define MW_PHYSICS_ENGINE_H
#include <stddef.h>
/* Exact scalar torque-curve stage recovered from Speed.dol 0x802240AC.
 * Values remain in original database units. This is not a complete engine,
 * tire, drivetrain or handling model. No runtime driver integration yet. */
typedef struct {
    const float *torque;
    size_t count;
    float idle_rpm;
    float max_rpm;
    float red_line_rpm;
} MwPhysicsEngineCurve;
/* Returns 0 for count <=1, as the original does. Returns NaN on unsupported
 * invalid inputs instead of imitating original out-of-range memory access. */
float mw_physics_engine_curve_raw(const MwPhysicsEngineCurve *curve, float rpm);
#endif
