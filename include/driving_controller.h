#ifndef DRIVING_CONTROLLER_H
#define DRIVING_CONTROLLER_H
#include <stdbool.h>
/* New arcade handling controller, not recovered NFS physics. Coordinates are meters
   in a caller-provided map. This module creates no roads or terrain. */
typedef struct { float x,z,heading,speed,steering,lateral_speed,yaw_rate,drift; } DriveState;
typedef struct { float throttle,brake,steering; bool handbrake; } DriveInput;
void drive_reset(DriveState *state,float x,float z,float heading);
bool drive_step(DriveState *state,DriveInput input,float seconds);
#endif
