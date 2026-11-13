#ifndef CHASE_CAMERA_H
#define CHASE_CAMERA_H
#include "driving_controller.h"
#include "mw_chase_source.h"
typedef struct {
    float eye[3],target[3],velocity[3],target_velocity[3],heading,fov;
    bool initialized,source_bound;
    MwChaseSourceConfig source;
    MwChaseSourceMotion source_motion;
} ChaseCamera;
bool chase_reset(ChaseCamera *camera,const DriveState *car,float height);
bool chase_step(ChaseCamera *camera,const DriveState *car,float height,float seconds);
/* Call after reset and after changing active car. Reset deliberately clears
   bindings, preserving safety for existing callers with uninitialized storage.
   This activates source direction/tuning/cubic stages; final placement, FOV
   and native pose providers remain the documented prototype adapter. */
bool chase_bind_source(ChaseCamera *,const MwChaseAsset *,uint32_t ecar,unsigned mode,int original_view_state);
#endif
