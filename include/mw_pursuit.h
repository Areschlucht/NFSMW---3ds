#ifndef MW_PURSUIT_H
#define MW_PURSUIT_H
#include "driving_controller.h"
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
enum { MW_PURSUIT_COPS=2,MW_PURSUIT_TRAIL=32 };
enum { MW_PURSUIT_SPAWN=1,MW_PURSUIT_BAIL=2,MW_PURSUIT_911=4 };
typedef struct {const unsigned char *data;size_t bytes;uint32_t events,events_at,spawns,spawns_at,triggers,triggers_at,model_key;float source_speed_multiplier,source_acceleration_multiplier;} MwPursuitPack;
typedef struct {uint32_t key,action;float position[3],rotation,width;} MwPursuitTrigger;
typedef struct {DriveState motion;float height;uint32_t model_key,spawn_key,trail_serial;bool active,released;} MwPursuitCar;
typedef struct {float top_speed,closing_speed,follow_distance,trail_spacing,steering_gain;} MwPursuitTuning;
typedef struct {uint32_t controllers,drive_calls,trigger_tests,navigation_checks,blocked_steps;} MwPursuitWork;
typedef struct {
 const MwPursuitPack *pack;uint32_t event,event_index,fired,trail_total;uintptr_t player_actor;
 float origin[3],previous_source[3],trail[MW_PURSUIT_TRAIL][3];
 MwPursuitCar actors[MW_PURSUIT_COPS];MwPursuitTuning tuning;
 bool cops_enabled,pursuit_active,no_new_pursuits,called_911,has_event;
} MwPursuit;
/* Mirrors streamed_drive_step:negative load/query failure,0 blocked,1 admitted.
   Callback owns physical collision/ground. The controller calls it<=2 per tick. */
typedef int (*MwPursuitDrive)(void *,DriveState *,float *height,DriveInput,float seconds);
bool mw_pursuit_pack_open(MwPursuitPack *,const void *,size_t);
/* Native driving policy, not original tactics/tuning. Stored source AI values
   are retained separately and are not misrepresented as this controller. */
MwPursuitTuning mw_pursuit_default_tuning(void);
bool mw_pursuit_begin(MwPursuit *,const MwPursuitPack *,uint32_t event,const float viewer_origin[3],uintptr_t player_actor,const float source_position[3]);
bool mw_pursuit_trigger_get(const MwPursuit *,unsigned,MwPursuitTrigger *);
/* Authoritative controlled-player entry only. Unknown/duplicate/other actors
   produce no signals. Spawn uses both exact source SpawnCop poses/model. */
bool mw_pursuit_enter(MwPursuit *,uintptr_t actor,uint32_t trigger,unsigned *signals);
/* Sweeps the actual source Width boxes through the shared native race helper,
   ordered by entry fraction. Still an actor-proxy adaptation, not original OBB. */
bool mw_pursuit_motion(MwPursuit *,uintptr_t actor,const float source_position[3],float actor_radius,unsigned *signals,MwPursuitWork *);
/* Call after an admitted teleport/reset to discard its sweep and old trail. */
bool mw_pursuit_relocate(MwPursuit *,uintptr_t actor,const float source_position[3]);
/* Intended30Hz, seconds<=.1. Two-cop chase follows the controlled player's
   bounded32-point motion trail, with no graph scans/allocations/IO. Failed drive
   callback leaves pursuit state unchanged. Bail releases visible actors into
   coasting/braking and forbids new pursuit/spawns for the event. */
bool mw_pursuit_step(MwPursuit *,const DriveState *player,float player_height,float seconds,MwPursuitDrive,void *,MwPursuitWork *);
#endif
