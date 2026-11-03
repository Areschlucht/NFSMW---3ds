#ifndef MW_ORIGINAL_CAMERA_CUBIC_H
#define MW_ORIGINAL_CAMERA_CUBIC_H
#include <stdbool.h>
#include <stdint.h>
/* Original44-byte interpolation channel used in the camera's3-channel state.
   Derivatives are original normalized-parameter fields, not guessed m/s. */
typedef struct {
    float value,derivative,target,target_derivative;
    float cubic[4]; /* t^3,t^2,t,constant */
    float progress,duration;
    int16_t state,mode;
} MwOriginalCameraCubic;
/* Mirrors target-value setter8020836C for one axis. */
bool mw_original_camera_cubic_target(MwOriginalCameraCubic *,float target);
/* Original80208128, including coefficient rebuild, optional speed/accel limits,
   progress and endpoint/state order. Nonpositive limits disable each limit.
   Caller must supply source durations/modes/cadence; no preset tuning invented.
   Invalid input rejects transactionally. */
bool mw_original_camera_cubic_step(MwOriginalCameraCubic *,float delta,
    float derivative_limit,float second_derivative_limit);
#endif
