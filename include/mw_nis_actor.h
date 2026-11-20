#ifndef MW_NIS_ACTOR_H
#define MW_NIS_ACTOR_H
#include <stdint.h>
#include <stdio.h>
/* Original source coordinates/quaternion components. No renderer conversion.
 * Source actor tokens (Car1, Cop1...) are names, NOT bound gameplay identities.
 * conversion_context=1 reproduces the source metadata time multiplier (30).
 * Input clock offsets/scales remain the scene director caller's responsibility.
 */
typedef struct { FILE *file; unsigned char *data; uint32_t file_size,banks,curves,bank_offset,curve_offset; } MwNisActorBank;
typedef struct { uint32_t first_curve,curve_count; char name[48]; } MwNisActorScene;
typedef enum { MW_NIS_ACTOR_UNKNOWN=0, MW_NIS_ACTOR_TRANSLATION=1, MW_NIS_ACTOR_QUATERNION=2, MW_NIS_ACTOR_SCALE=3 } MwNisActorKind;
typedef struct {
    char name[64],actor_token[32]; uint32_t frames,channels,data_offset;
    uint16_t destination[4]; float context_rate; MwNisActorKind kind;
} MwNisActorCurve;
/* A single bounded allocation caches the whole ~752 KiB source asset.
 * sample performs no file I/O or allocation. */
int mw_nis_actor_open(MwNisActorBank *bank,const char *path);
void mw_nis_actor_close(MwNisActorBank *bank);
int mw_nis_actor_find_scene(MwNisActorBank *bank,const char *name,MwNisActorScene *scene);
int mw_nis_actor_find_curve(MwNisActorBank *bank,const MwNisActorScene *scene,const char *exact_name,MwNisActorCurve *curve);
/* Clamps to available samples. Quaternion components use source fractional deltas linearly;
 * normalization/slerp is deliberately NOT applied without original consumer proof.
 * out_count must accommodate curve.channels (up to 4).
 */
int mw_nis_actor_sample(MwNisActorBank *bank,const MwNisActorCurve *curve,float input_time,int conversion_context,float *out,uint32_t out_count);
#endif
