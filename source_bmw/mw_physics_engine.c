#include "mw_physics_engine.h"
#include <math.h>
#include <stdint.h>

/* Volatile stores enforce the original fsubs/fmuls/fdivs float boundaries
 * even on hosts with extended intermediates. Compile without fast-math. */
static float f32(float value) { volatile float rounded = value; return rounded; }

float mw_physics_engine_curve_raw(const MwPhysicsEngineCurve *c, float rpm)
{
    if (!c) return NAN;
    if (c->count <= 1) return 0.0f;
    if (!c->torque || c->count > UINT16_MAX || !isfinite(rpm) ||
        !isfinite(c->idle_rpm) || !isfinite(c->max_rpm) ||
        !isfinite(c->red_line_rpm) || !(c->max_rpm > c->idle_rpm) ||
        c->red_line_rpm < c->idle_rpm || c->red_line_rpm > c->max_rpm)
        return NAN;
    float bounded = rpm < c->red_line_rpm ? rpm : c->red_line_rpm;
    if (bounded < c->idle_rpm) bounded = c->idle_rpm;
    float numerator = f32(f32((float)(c->count - 1)) * f32(bounded - c->idle_rpm));
    float position = f32(numerator / f32(c->max_rpm - c->idle_rpm));
    uint32_t index = (uint32_t)position;
    float fraction = f32(position - f32((float)index));
    if (index >= c->count) return NAN;
    uint32_t next = index + 1 < c->count ? index + 1 : index;
    float difference = f32(c->torque[next] - c->torque[index]);
    return fmaf(difference, fraction, c->torque[index]);
}
