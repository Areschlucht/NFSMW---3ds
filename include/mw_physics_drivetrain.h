#ifndef MW_PHYSICS_DRIVETRAIN_H
#define MW_PHYSICS_DRIVETRAIN_H
#include <stddef.h>
#include "mw_physics_tires.h"
/* Recovered speed/gear -> requested engine RPM stage0x802555CC. This includes
 * its original idle offset/range scaling and is not a rigid RPM constraint,
 * complete clutch model or automatic-shift state machine. Gear slots use
 * original database ordering:0 reverse,1 neutral,2 first forward gear. */
float mw_physics_requested_rpm(const MwPhysicsTireDimensions *,const float *gear_ratios,size_t gear_count,unsigned gear_slot,float final_gear,float idle_rpm,float red_line_rpm,float speed_mps);
#endif
