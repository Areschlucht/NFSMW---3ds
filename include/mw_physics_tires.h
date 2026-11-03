#ifndef MW_PHYSICS_TIRES_H
#define MW_PHYSICS_TIRES_H
/* Original tires AxlePair order is front[0], rear[1]. Dimensions are proven
 * by original 0x80224268 constants: millimetres, percent and inches. */
typedef struct {
    float section_width_mm[2];
    float aspect_ratio_percent[2];
    float rim_size_inches[2];
} MwPhysicsTireDimensions;
/* Mirrors original nonzero-front/zero-rear selector and float operations. */
float mw_physics_tire_diameter_m(const MwPhysicsTireDimensions *dimensions, int front_axle);
#endif
