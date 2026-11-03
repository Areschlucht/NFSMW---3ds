#ifndef MW_ORIGINAL_CAMERA_DIRECTION_H
#define MW_ORIGINAL_CAMERA_DIRECTION_H
#include <stdbool.h>
/* Original80073028..80073100 direction-target numerical stage, before timer/
   vertical attenuation and persistent interpolation. Inputs must share the
   original camera-controller frame; this is not a complete chase update. */
bool mw_original_camera_direction_target(const float velocity[3],const float body_forward[3],
    float cached_speed,float target[3],float *velocity_weight);
#endif
