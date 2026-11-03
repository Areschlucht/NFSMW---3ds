#ifndef CHASE_CAMERA_H
#define CHASE_CAMERA_H
#include "driving_controller.h"
typedef struct { float eye[3],target[3],velocity[3],target_velocity[3],heading,fov;bool initialized; } ChaseCamera;
bool chase_reset(ChaseCamera *camera,const DriveState *car,float height);
bool chase_step(ChaseCamera *camera,const DriveState *car,float height,float seconds);
#endif
