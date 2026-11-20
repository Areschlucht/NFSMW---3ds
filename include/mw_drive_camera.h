#ifndef MW_DRIVE_CAMERA_H
#define MW_DRIVE_CAMERA_H
#include "mw_chase_source.h"
#include <stddef.h>
/* Original camera frame: X forward, Y lateral, Z up. Matrices store basis rows
 * followed by translation in row3. This is distinct from the graphics view.
 * Numeric core fields retain source CameraAnchor offsets for oracle tests. */
typedef struct {
 float velocity[4],speed,top_speed,position[4],dimensions[4],acceleration[4],matrix[16];
} MwDriveCameraAnchor;
typedef struct {
 MwOriginalCameraCubic fov,eye[3],look[3],forward[3],up[3];
 uint32_t last_grounded,last_under_vehicle,last_gear_change;
 float ignore_snap_seconds,impact[2],impact_seconds[2];
 float acceleration_samples[5][4],acceleration_sum[3],average_acceleration[3];
 unsigned acceleration_count,acceleration_cursor;
 bool initialized,accel_lag,look_back,snap_next,first_time,perfect_focus;
} MwDriveCamera;
/* Actual CameraAnchor::Update800685D8. Fourth source argument is not consumed;
 * acceleration is computed from speed change and basis, with teleport guard. */
bool mw_drive_camera_anchor_update(MwDriveCameraAnchor*,const float matrix[16],const float velocity[3],float delta);
/* Full source SetForward80072FCC including post-grounding/vertical attenuation
 * and target/snap semantics. Original WorldTimer ticks at4000Hz, independent of
 * update cadence. Output unchanged on invalid finite/provider input. */
bool mw_drive_camera_forward(MwDriveCamera*,const MwDriveCameraAnchor*,int pov_type,uint32_t world_timer,bool snap);
/* Full source MakeSpace80073218. outside=(pov types2..6); basis follows the
 * current interpolation values. No body-yaw or spring approximation. */
bool mw_drive_camera_space(const MwDriveCamera*,const MwDriveCameraAnchor*,bool outside,float matrix[16]);
typedef struct { float speed_hug[5][2];uint16_t nos_fov_turns; } MwDriveCameraSourceData;
typedef struct {
 int pov_type;uint32_t world_timer;
 bool touching_ground,under_vehicle,nos_engaged,snap;
 /* Actual DutchAroundCar query result, in the original camera frame. Required
  * even when zero; production caller must perform the real query at speed>5. */
 float dutch[3];
} MwDriveCameraDesiredInput;
/* Complete ordinary-driving SetDesired target stage. Debug custom/highlight
 * camera globals are outside this API; HighliteMode is literally false in USA.
 * Explicit source query results do not replace their world-query producers. */
bool mw_drive_camera_desired(MwDriveCamera*,const MwDriveCameraAnchor*,
 const MwOriginalCameraProfileCache*,const MwOriginalCameraTuning*,
 const MwDriveCameraSourceData*,const MwDriveCameraDesiredInput*,float space[16]);
float mw_drive_camera_sine_turns(uint16_t);
#endif
