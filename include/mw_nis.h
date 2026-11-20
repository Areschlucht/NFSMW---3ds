#ifndef MW_NIS_H
#define MW_NIS_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
/* Original camera bank only. This is not a decoded ELF actor-animation bank. */
typedef struct {const unsigned char *data;size_t bytes;uint32_t scenes,tracks,keys,scene_at,track_at,key_at;} MwNisPack;
typedef struct {const char *name;uint32_t hash,first_track,track_count;} MwNisScene;
typedef struct {const char *name;uint32_t first_key,key_count;float duration;} MwNisTrack;
typedef struct {
    float eye[3],target[3],roll_source,fov_turn; /* roll_source is turns. */
    uint32_t key_index;
    uint8_t eye_mode,target_mode,flags[4],reference_flags[4]; /* source bytes8..11 */
    bool finished;
} MwNisCamera;
/* Parent supplies ORIGINAL mode bindings/scene matrices. Mode1 values are
   absolute sourceXYZ in these scenes; mode0/3 are not silently anchored here.
   The resolver runs AFTER Hermite interpolation and must output original
   sourceXYZ world coordinates (not viewer axes). A failed resolver or
   incomplete binding leaves camera output unchanged. See mw_nis_director.h
   for source CDActionIce IPlayer/mode0 and CAnimScene/mode3 providers. */
typedef bool (*MwNisResolve)(void *,uint8_t mode,bool target,const float input[3],float output[3]);
/* Original getter mode3 adjusts LOCAL source Z using terrain before tangent
   construction, then applies scene matrix after interpolation. This callback
   performs that pre-stage only, before both endpoints and neighbor tangents.
   Keep source units/local basis intact. Mode0/1 normally copy the input here. */
typedef bool (*MwNisPrepare)(void *,uint8_t mode,bool target,const float input[3],float output[3]);
typedef struct {MwNisPrepare prepare;MwNisResolve resolve;void *context;} MwNisProviders;
bool mw_nis_open(MwNisPack *,const void *,size_t);
bool mw_nis_scene(const MwNisPack *,uint32_t,MwNisScene *);
bool mw_nis_find(const MwNisPack *,const char *,MwNisScene *);
bool mw_nis_track(const MwNisPack *,const MwNisScene *,uint32_t,MwNisTrack *);
/* Samples recovered source cubic paths, not a generated camera orbit.
   FOV is source fixed-turn units, derived by original focal conversion.
   Roll keeps its source scalar units. Coordinate resolution is caller-owned.
   This basic sampler uses identity pre-ground export. Use _provided for an
   original terrain/actor provider; it must not be sold as full mode3 otherwise. */
bool mw_nis_camera_sample(const MwNisPack *,const MwNisTrack *,float seconds,
    MwNisResolve,void *,MwNisCamera *);
bool mw_nis_camera_sample_provided(const MwNisPack *,const MwNisTrack *,float seconds,
    const MwNisProviders *,MwNisCamera *);
/* Original scene-clock parameter directly, avoiding a multiply/divide through
 * authored track duration. Values clamp to0..1; all providers stay explicit. */
bool mw_nis_camera_parameter_provided(const MwNisPack *,const MwNisTrack *,float parameter,
    const MwNisProviders *,MwNisCamera *);
#endif
