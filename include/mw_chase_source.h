#ifndef MW_CHASE_SOURCE_H
#define MW_CHASE_SOURCE_H
#include "mw_original_camera_cubic.h"
#include "mw_original_camera_profile.h"
#include "mw_original_camera_tuning.h"
#include <stddef.h>
#include <stdint.h>
typedef struct { const unsigned char *data;size_t bytes;uint32_t vehicles,profiles_at,tuning_at; } MwChaseAsset;
typedef struct {
    MwOriginalCameraProfile profile;
    MwOriginalCameraProfileCache cache;
    MwOriginalCameraTuning lower,upper;
    uint32_t ecar_key;
    unsigned mode;
} MwChaseSourceConfig;
typedef struct { MwOriginalCameraCubic channel[3];float direction[3];bool initialized; } MwChaseSourceMotion;
/* Source-only profile/tuning data. Mutable camera state never points into media
   or source archives. Views borrow the immutable sidecar until shutdown. */
bool mw_chase_asset_open(MwChaseAsset *,const void *,size_t);
bool mw_chase_asset_vehicle(const MwChaseAsset *,uint32_t ecar,unsigned mode,
    int original_view_state,float camera_scale,MwChaseSourceConfig *);
/* Planar 3DS controller adapter around verified original numerical components.
   It preserves update-before-new-target order. Original timer attenuation,
   controller duration biases and complete placement/collision remain separate. */
bool mw_chase_source_reset(MwChaseSourceMotion *,const MwChaseSourceConfig *,
    const float velocity[3],const float body_forward[3],float cached_speed);
bool mw_chase_source_step(MwChaseSourceMotion *,const MwChaseSourceConfig *,
    const float velocity[3],const float body_forward[3],float cached_speed,float delta);
#endif
