#ifndef MW_NIS_DIRECTOR_H
#define MW_NIS_DIRECTOR_H
#include "mw_nis.h"
/* Matrices below use ORIGINAL bMatrix4 layout/source XYZ, translation12..14.
 * mode0 subject is CDActionIce's IPlayer car ICEAnchor. mode3 is CAnimScene's
 * GetSceneTransformMatrix, NOT a Car1 animation curve or current player pose.
 */
typedef bool (*MwNisGround)(void *context,const float source_world[3],float *height);
typedef struct {
    float subject[16],scene[16],fixed_subject[16];
    bool has_subject,has_scene,has_fixed_subject;
    /* Original CAnimScene::IsCameraFixingElevation returns true. Ground's miss
     * must be reported false, matching original endpoint-Z fallback. */
    bool fix_elevation,world_queries_enabled;
    float scene_ground_height;
    MwNisGround ground;
    void *ground_context;
    uint8_t key_reference_flags[4];
    const unsigned char *active_data;
    uint32_t active_first_key,active_key;
    bool has_active_key;
    /* Original SetDesired prepares terrain-dependent endpoints on a key
     * transition. Cache those static points, not per-frame map queries. */
    struct {float input[3],output[3];} prepared[16];
    float prepared_scene[16],prepared_height;
    unsigned prepared_count;
} MwNisDirector;
/* Direct original eMulVector operation order, transactional on invalid input. */
bool mw_nis_director_transform(const float matrix[16],const float in[3],float out[3]);
/* Build CAnimLocator's rotation/translation root after caller obtains the
 * ORIGINAL origin ground correction. scene_type0/2/3 use supplied origin and
 * heading; other types use identity. No renderer/physics axis conversion. */
bool mw_nis_director_scene_frame(float out[16],const float corrected_origin[3],
    uint16_t heading,uint32_t scene_type);
/* Samples source camera using correct mode0/1/2/3 matrices and mode3 pre-ground
 * adjustment. Caller supplies verified source subject/scene matrices above.
 * Original opening keys never enter smoothing-only branch (byte8=0,byte9=1);
 * that unsupported branch is refused explicitly. Fixed byte8 uses source
 * subject orientation captured on original KeysShared reset transitions and
 * CURRENT subject position. Preserve this context between samples; clear
 * has_active_key when starting a new source camera controller. */
bool mw_nis_director_camera(MwNisDirector *,const MwNisPack *,const MwNisTrack *,
    float seconds,MwNisCamera *);
/* Original NIS ICETrack::GetParameter uses scene clock, not authored camera
 * duration: (elapsed-start)/(total-start). FOV then truncates to source uint16.
 * Use scene header/runtime time bounds, never stretch actors to track duration. */
bool mw_nis_director_scene_camera(MwNisDirector *,const MwNisPack *,const MwNisTrack *,
    float scene_elapsed,float scene_start,float scene_total,MwNisCamera *);
/* Source ChooseGoodSceneCameraTrackIndex: choose maximum horizontal camera-to-
 * look dot product against original player transform row0. Single track=>0.
 * Requires mw_gekko_math.c for original bNormalize estimate/refinements. */
bool mw_nis_director_choose_track(MwNisDirector *,const MwNisPack *,const MwNisScene *,uint32_t *index);
/* Call when changing the ground provider/world query generation within a key. */
void mw_nis_director_invalidate_ground(MwNisDirector *);
#endif
