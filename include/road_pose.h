#ifndef ROAD_POSE_H
#define ROAD_POSE_H
#include "road_contact.h"
#include "wheel_motion.h"
typedef struct { float height,pitch,roll,normal[3];unsigned contacts; } RoadPose;
/* Visual chassis alignment from original road heights; not suspension physics. */
bool road_pose_sample(const RoadWorld *world,const WheelRig *rig,const DriveState *car,float reference,RoadPose *out);
typedef bool (*RoadSurfaceQuery)(const void *context,float x,float z,float reference,float *height,float normal[3]);
/* Reuses the same visual wheel-plane fit with an explicitly supplied surface. */
bool road_pose_sample_with_surface(const RoadWorld *,const WheelRig *,const DriveState *,float,RoadPose *,RoadSurfaceQuery,const void *);
#endif
