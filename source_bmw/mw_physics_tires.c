#include "mw_physics_tires.h"
#include <math.h>
static float f32(float value) { volatile float rounded = value; return rounded; }
float mw_physics_tire_diameter_m(const MwPhysicsTireDimensions *d, int front_axle)
{
    if (!d) return NAN;
    unsigned axle=front_axle ? 0u : 1u;
    float side=f32(d->section_width_mm[axle]*0.001f);
    side=f32(side+side);
    side=f32(side*0.01f);
    side=f32(side*d->aspect_ratio_percent[axle]);
    return fmaf(d->rim_size_inches[axle],0.0254f,side);
}
