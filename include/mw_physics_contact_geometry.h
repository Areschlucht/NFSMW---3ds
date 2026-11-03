#ifndef MW_PHYSICS_CONTACT_GEOMETRY_H
#define MW_PHYSICS_CONTACT_GEOMETRY_H
#include "mw_physics_contact_frame.h"
#include "mw_physics_tires.h"
/* Physical suspension mounts from80247724..47834. These are not visual ecar
 * TireOffsets. Native body-localX is across, Y up, Z forward. */
void mw_physics_contact_mounts(const MwPhysicsTireDimensions *,const float track_width_m[2],float front_axle_m,float wheel_base_m,float body_half_extent_y,MwPhysicsContactVector mounts[4]);
#endif
