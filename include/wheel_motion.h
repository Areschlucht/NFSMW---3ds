#ifndef WHEEL_MOTION_H
#define WHEEL_MOTION_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "driving_controller.h"
typedef struct { float pivot[3],radius;bool front; } Wheel;
typedef struct { Wheel wheels[4];uint32_t batches;uint8_t *groups; } WheelRig;
typedef struct { float angle[4]; } WheelMotion;
bool wheel_rig_decode(const uint8_t *data,size_t size,uint32_t batches,uint32_t body_crc,WheelRig *out);
void wheel_rig_free(WheelRig *rig);
void wheel_motion_reset(WheelMotion *motion);
/* Accepted position changes drive rolling; blocked motion does not spin. */
bool wheel_motion_update(const WheelRig *rig,WheelMotion *motion,const DriveState *previous,const DriveState *next);
bool wheel_motion_lock_rear(const WheelRig *rig,const WheelMotion *previous,WheelMotion *next);
#endif
