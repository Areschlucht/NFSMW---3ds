#ifndef MW_PHYSICS_GRIP_H
#define MW_PHYSICS_GRIP_H
/* Rear-wheel assist multiplier from80249004. Raw argument names deliberately
 * retain original ABI registers: input-state axes/units are not all proven.
 * Called only for rear wheels, then blended with a time-dependent state before
 * multiplying a tire grip factor. This is not a complete tire force model. */
float mw_physics_rear_grip_assist_raw(float input_f1,float handbrake,float input_f3,float yaw_control,float input_f5);
#endif
