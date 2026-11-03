#ifndef MW_ORIGINAL_CAMERA_TUNING_H
#define MW_ORIGINAL_CAMERA_TUNING_H
#include <stdbool.h>
/* Original 0xB0-byte tuning sample: four scalar fields and ten padded vectors.
   Field names intentionally remain offsets until each consumer is proved. */
typedef struct { float scalar[4]; float vector[10][4]; } MwOriginalCameraTuning;
/* Original80071BB8: updates only active fields, preserving vector padding.
   Requires explicit source samples and interpolation parameter. */
bool mw_original_camera_tuning_blend(const MwOriginalCameraTuning *lower,
    const MwOriginalCameraTuning *upper,float parameter,MwOriginalCameraTuning *out);
/* Original80073EF8..80073F24; finite nonnegative controller speed only. */
bool mw_original_camera_tuning_parameter(float controller_speed,float *parameter);
#endif
