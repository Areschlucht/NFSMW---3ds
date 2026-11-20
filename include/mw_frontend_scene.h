#ifndef MW_FRONTEND_SCENE_H
#define MW_FRONTEND_SCENE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
/* Immutable source-bound static frontend camera/placement records. These are
 * original metre/sourceXYZ outputs, not a native camera animation policy. */
typedef struct { const unsigned char *data;size_t bytes; } MwFrontendScenePack;
typedef struct {
    float eye[3],target[3],up[3],fov_degrees;
    uint32_t collection_key;
} MwFrontendSceneCamera;
typedef struct {
    uint32_t garage_type;
    float geometry_position[3],geometry_z_degrees,car_rotation_degrees[3],car_height_bias;
} MwFrontendScenePlacement;
/* All validation is bounded, with no allocation or I/O. Failure preserves out.
 * Caller keeps the bytes alive. No executable code or debug data is stored. */
bool mw_frontend_scene_open(MwFrontendScenePack *out,const void *,size_t);
bool mw_frontend_scene_camera(const MwFrontendScenePack *,const char *name,MwFrontendSceneCamera *);
bool mw_frontend_scene_placement(const MwFrontendScenePack *,uint32_t garage_type,MwFrontendScenePlacement *);
#endif
