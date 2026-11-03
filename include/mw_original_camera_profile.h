#ifndef MW_ORIGINAL_CAMERA_PROFILE_H
#define MW_ORIGINAL_CAMERA_PROFILE_H
#include <stdbool.h>
#include <stdint.h>
/* Original camerainfo two-entry arrays. Index selection is view-state based,
   NOT speed interpolation. Field units below are established only where a
   consumer proves them; these values alone are not a chase-camera simulator. */
typedef struct {
    float angle_degrees[2],lag[2],height[2],lateral_offset[2],fov_degrees[2],stiffness[2];
    uint32_t tilting[2];
} MwOriginalCameraProfile;
typedef struct {
    uint16_t angle_turns;
    float lag,height,lateral_offset;
    uint16_t fov_turns;
    float stiffness;
    uint16_t tilting;
    unsigned profile_index;
} MwOriginalCameraProfileCache;
/* Original800687C8 switch:0bumper,1hood,2close,3far,4superfar,5drift,6pursuit.
   Returns original ecar RefSpec field hash; unknown mode selects default profile
   via a different original branch and returns0 here. */
uint32_t mw_original_camera_profile_field(int mode);
/* Original800688DC..80068AF0 caches profile values. Positive camera_scale is
   camera+0xD4; nonpositive finite values select1. FOV scales, LAG divides.
   Its result is consumed as a vertical FOV after explicit viewport factors;
   this cache alone does not establish render aspect.
   Invalid/nonfinite data is rejected with output unchanged. */
bool mw_original_camera_profile_cache(const MwOriginalCameraProfile *,int original_view_state,
    float camera_scale,MwOriginalCameraProfileCache *);
typedef struct {
    float vertical_fov_degrees,aspect,viewport_y_factor;
} MwOriginalCameraProjection;
/* Original ordinary-view projection argument path801000EC..80100210.
   All viewport dimensions and three correction factors are explicit inputs.
   Do not blindly apply the GC .8/.86 aspect correction on a 3DS display.
   Returns arguments for a vertical-FOV perspective matrix, not a GX matrix.
   Platform adapter rejects singular/nonfinite perspective arguments. */
bool mw_original_camera_projection(uint16_t raw_fov_turns,unsigned viewport_width,
    unsigned viewport_height,unsigned full_height,float aspect_correction,
    float global_aspect_scale,float global_fov_scale,MwOriginalCameraProjection *);
#endif
