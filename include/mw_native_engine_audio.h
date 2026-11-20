#ifndef MW_NATIVE_ENGINE_AUDIO_H
#define MW_NATIVE_ENGINE_AUDIO_H
#include "mw_engine_audio_driver.h"
#include "wheel_motion.h"
/* Deliberately native bridge for the current planar prototype. Recovered source
 * EngineRacer still computes RPM; these wheel/contact/owner policies are NOT
 * claimed to be original chassis/input/material physics. */
typedef struct {
    const DriveState *previous,*current;
    const WheelMotion *previous_wheels,*current_wheels;
    float previous_height,height,car_ground_offset;
    DriveInput control;
    float seconds;
    bool nos_requested;
} MwNativeEngineObservation;
/* Coordinates are viewer/local-world metres, same origin as DriveState.
 * Query every wheel in an admitted NWC section. Return -1 unavailable/error,
 * 0 genuine no-ground result,1actual ground. On hit write finite height and
 * actual upward normal; do not substitute a constant flat plane on failure. */
typedef int (*MwNativeEngineGround)(void *,unsigned wheel,const float viewer_point[3],float *ground_height,float normal[3]);
typedef struct {
    MwEngineAudioDriver source;
    const WheelRig *rig;
    float extent,center[3];
    unsigned visual_wheel[4];
    float compression[4],velocity[4],slip[4],traction[4];
    unsigned contacts;
    bool initialized;
} MwNativeEngineAudio;
/* Stable borrowed profile and rig, actual renderer normalization origin/extent.
 * No allocation or fileIO. Model/profile correspondence is caller-owned. */
bool mw_native_engine_audio_init(MwNativeEngineAudio *,const MwVehicleRuntimeParams *,const WheelRig *,float art_extent,const float art_center[3],float source_clock);
void mw_native_engine_audio_stop(MwNativeEngineAudio *);
/* Admitted movement only. Queries all4actual visual tyre-bottom points once;
 * missing sections disable the sample instead of fabricating contacts.
 * Converts observed wheel angles (including handbrake locks/wraps) and measured
 * accepted motion to a native wheel provider, then runs bounded source60Hz.
 * Normal automatic/no optional effect interfaces/unlimited/tuning is explicit
 * native policy. Reverse requests use source gear-commit math with native policy.
 * Source tyre radius and suspension scalar law are preserved; native proxy
 * ground queries/traction admission are not original complete wheel physics. */
MwEngineAudioAdvance mw_native_engine_audio_advance(MwNativeEngineAudio *,const MwNativeEngineObservation *,MwNativeEngineGround,void *);
bool mw_native_engine_audio_sample(const MwNativeEngineAudio *,MwEngineAudioSample *);
#endif
