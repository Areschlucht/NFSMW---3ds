#ifndef MW_DRIVING_BACKEND_H
#define MW_DRIVING_BACKEND_H
#include "mw_vehicle_runtime.h"
#include "mw_vehicle_world.h"
#include "driving_controller.h"

enum { MW_DRIVING_MAX_TICKS=8,MW_DRIVING_BND_MAX_BYTES=65536 };
typedef struct {const void *data;size_t bytes;} MwDrivingBytes;
typedef struct {
    MwDrivingBytes runtime,wheels,mechanical,bounds;
    uint32_t model_key;
    float collision_box_pad[3]; /* actual selected rigidbodyspecs value */
} MwDrivingAssets;
typedef struct {
    MwVehicleRuntimeParams params; /* stable address: do not copy an open backend */
    MwVehicleWorldActor actor;
    MwVehicleRuntimeState state;
    double debt_seconds;
    float source_clock;
    uint64_t ticks;
    void *owned_bounds;
    bool loaded,started;
} MwDrivingBackend;
typedef struct {
    MwVehicleRuntimeHooks runtime;
    /* All three are mandatory. begin stages world/contact/event state and
       exposes the trial actor to the caller's original after_body_tick hook.
       commit cannot fail; abort discards all staged changes. Same context as
       runtime.context. The supplied actor is valid only during this tick. */
    bool (*begin)(void *,MwVehicleWorldActor *,const MwVehicleRuntimeState *);
    void (*commit)(void *,const MwVehicleRuntimeState *,const MwVehicleRuntimeOutput *);
    void (*abort)(void *);
} MwDrivingCallbacks;
typedef enum {
    MW_DRIVING_OK=0,MW_DRIVING_NOT_READY=-1,MW_DRIVING_INVALID=-2,
    MW_DRIVING_SOURCE_REJECTED=-3,MW_DRIVING_TIME_DEBT=-4
} MwDrivingStatus;
typedef struct {
    MwDrivingStatus status;
    unsigned completed_ticks;
    double remaining_seconds;
    MwVehicleRuntimeOutput last;
} MwDrivingAdvance;
typedef struct {
    DriveState drive;
    float height,body_matrix_native[16];
} MwDrivingView;

/* Initialize backend to zero first. BND bytes remain borrowed until close;
   NVR/NDP/MMP bytes are copied/checked. No file IO occurs in simulation. */
bool mw_driving_backend_open(MwDrivingBackend *,const MwDrivingAssets *);
/* Loads <profile>.nvr/.ndp/.mmp and <bounds_name>.bnd from one directory.
   File names are bounded ASCII basenames. Owns BND storage until close. */
bool mw_driving_backend_open_files(MwDrivingBackend *,const char *directory,
    const char *profile,const char *bounds_name,uint32_t model_key,const float box_pad[3]);
void mw_driving_backend_close(MwDrivingBackend *);
/* Scalar state from source EngineRacer constructor + Reset802553CC. Attribute
   tables are already calculated by the source-bound NVR loader. Does not
   perform source owner/interface registration or select gameplay upgrades. */
bool mw_driving_backend_engine_construct(const MwDrivingBackend *,MwPhysicsTransmissionEngineStepState *);
/* A caller-supplied actual source spawn/body and engine state are mandatory.
   This does not invent constructor flags, pose, wheel ground or engine RPM. */
bool mw_driving_backend_start(MwDrivingBackend *,const MwOriginalRigidBody *,
    const MwPhysicsTransmissionEngineStepState *,float source_clock);
/* Source60Hz normal-speed scheduler, bounded <=8ticks per call. Successful
   ticks commit individually; on later rejection those prior ticks remain.
   Time debt is retained, never silently dropped, and rejects above1second.
   raw.seconds/source_time are overwritten by this scheduler. */
MwDrivingAdvance mw_driving_backend_advance(MwDrivingBackend *,
    const MwVehicleRuntimeInput *raw,float elapsed_seconds,unsigned maximum_ticks,
    const MwDrivingCallbacks *);
/* Viewer adapter only. Full native matrix accompanies the planar DriveState.
   drift has no source equivalent and is zero; never used for simulation. */
bool mw_driving_backend_view(const MwDrivingBackend *,const float viewer_origin[3],MwDrivingView *);
float mw_driving_backend_step_seconds(void);
#endif
