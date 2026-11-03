#ifndef STREAMED_DRIVE_H
#define STREAMED_DRIVE_H
#include "road_pose.h"
#include "world_collision_runtime.h"
/* Adapter from the provisional controller to original streamed collision.
   Full recovered suspension/body dynamics are not implemented by this bridge. */
typedef struct { const WorldCollisionRuntime *collision;const RoadWorld *road; } StreamedDriveSurface;
bool streamed_drive_surface(const void *,float x,float z,float reference,float *height,float normal[3]);
/* 1 advanced, 0 blocked/no ground, negative original collision IO/data error.
   A centreline wall sweep is a guard, not original compound-body response. */
int streamed_drive_step(const StreamedDriveSurface *,DriveState *,float *height,DriveInput,float seconds);
#endif
