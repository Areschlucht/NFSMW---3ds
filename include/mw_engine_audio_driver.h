#ifndef MW_ENGINE_AUDIO_DRIVER_H
#define MW_ENGINE_AUDIO_DRIVER_H
#include "mw_vehicle_runtime.h"
/* Engine-only source simulation for sound consumers. This does not replace
 * chassis/wheel physics, generate contacts, or infer RPM from vehicle speed.
 * The profile must remain at a stable address until this driver is stopped. */
enum {
    MW_ENGINE_AUDIO_WHEELS=1, MW_ENGINE_AUDIO_OWNER=2,
    MW_ENGINE_AUDIO_SETTINGS=4, MW_ENGINE_AUDIO_NOS=8,
    MW_ENGINE_AUDIO_CONTACTS=16, MW_ENGINE_AUDIO_REQUIRED=31,
    MW_ENGINE_AUDIO_MAX_TICKS=6
};
typedef struct {
    uint32_t present;
    MwPhysicsTransmissionEngineStepInput input;
    MwPhysicsTransmissionSpeedWheel wheels[4]; /* original axle-first order */
    bool induction_tuning_present;
    float induction_tuning_18;
} MwEngineAudioFrame;
typedef struct {
    const MwVehicleRuntimeParams *profile;
    MwPhysicsTransmissionEngineStepState engine;
    MwStoryEngine story;
    double debt_seconds;
    float source_clock;
    uint64_t ticks;
    bool initialized,has_sample;
} MwEngineAudioDriver;
typedef struct {
    float rpm,applied_throttle,output_torque;
    unsigned gear_slot;
    bool engine_blown;
} MwEngineAudioSample;
typedef bool (*MwEngineAudioProduce)(void *,const MwEngineAudioDriver *,MwEngineAudioFrame *);
typedef void (*MwEngineAudioCommit)(void *,const MwEngineAudioFrame *,
    const MwPhysicsTransmissionSpeedWheel [4],const MwPhysicsTransmissionGearEvent *,bool engine_blown_event);
typedef enum {
    MW_ENGINE_AUDIO_OK=0,MW_ENGINE_AUDIO_NOT_READY=-1,
    MW_ENGINE_AUDIO_BAD_INPUT=-2,MW_ENGINE_AUDIO_SOURCE_REJECTED=-3,
    MW_ENGINE_AUDIO_TIME_DEBT=-4
} MwEngineAudioStatus;
typedef struct {MwEngineAudioStatus status;unsigned ticks;double debt_seconds;} MwEngineAudioAdvance;
/* Original EngineRacer constructor/reset scalar state, stock profile binding.
 * Success does not publish an audio sample: at least one admitted source tick
 * is required. Rejects unsupported nonempty original RPM limiter arrays. */
bool mw_engine_audio_driver_init(MwEngineAudioDriver *,const MwVehicleRuntimeParams *,float source_clock);
void mw_engine_audio_driver_stop(MwEngineAudioDriver *);
/* Source 60Hz scheduler, <=6 ticks/100ms call. Per-tick producer is mandatory:
 * it supplies actual wheel spring compression/traction/slip/history/radius,
 * previous contact count, owner/mode/gate/boost interfaces, automatic/rev flags,
 * NOS/tuning/global state. Presence bits attest these are intentionally supplied,
 * not that a zero-filled struct has magically recovered the source providers.
 * The caller must label any kinematic/bicycle producer as a native adapter.
 * Producer must not mutate external state; commit runs only after success.
 * On failure prior successful ticks remain; the rejecting tick rolls back.
 * Elapsed debt is retained, never silently dropped. Pause by not calling. */
MwEngineAudioAdvance mw_engine_audio_driver_advance(MwEngineAudioDriver *,float elapsed,
    unsigned maximum_ticks,MwEngineAudioProduce,MwEngineAudioCommit,void *);
bool mw_engine_audio_driver_sample(const MwEngineAudioDriver *,MwEngineAudioSample *);
/* Source SabotageEngine timing uses this driver's paused simulation clock. */
bool mw_engine_audio_driver_sabotage(MwEngineAudioDriver *,float delay_seconds);
#endif
