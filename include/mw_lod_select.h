#ifndef MW_LOD_SELECT_H
#define MW_LOD_SELECT_H
#include <stdbool.h>
#include <stdint.h>
/* Original ordered bound slots, not invented near/far distance bands. */
typedef struct {
    int32_t projected_score;
    uint32_t instance_flags,context_flags;
    int32_t original_view_state;
    uint32_t bound_slot_mask;
    bool slot0_has_mesh;
    int16_t slot0_header_triangle_statistic;
    float slot0_header_metric_9c;
} MwLodSelectInput;
/* Exact bounded802BEC38..802BED60 decision after visibility/score generation.
   Returns original bound slot0,2,3 or -1 if none. Does not activate sections,
   invent model fallbacks or establish the upstream projected-score producer. */
int mw_lod_select(const MwLodSelectInput *input);
/* Original802BEB24..802BEC38 producer uses instance TRANSLATION, not AABB
   center. All positions/radius must retain the same original source units.
   sqrt callback supplies the original sqrt stage if available. NULL uses
   target sqrtf, whose score boundary equivalence is not globally established. */
typedef float (*MwLodSqrt)(float squared,void *context);
bool mw_lod_projected_score(const float translation[3],const float camera[3],
                           const float forward[3],float object_radius_38,
                           float view_projection_0c,MwLodSqrt sqrt_stage,
                           void *context,int32_t *score);
/* Original800FFF14 fixed256 projection coefficient, using original uint16
   whole-turn FOV units and polynomial sine. No viewport-resolution rescale. */
float mw_lod_projection_raw(uint16_t fov_turn);
#endif
