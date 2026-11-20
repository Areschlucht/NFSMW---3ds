#ifndef MW_RACE_AI_H
#define MW_RACE_AI_H
#include "driving_controller.h"
#include "mw_event_catalog.h"
#include "mw_traffic.h"
enum { MW_RACE_AI_ACTORS=3, MW_RACE_AI_POINTS=4096 };
typedef struct {const unsigned char *data;size_t bytes;uint32_t events_at,actors_at,strings_at,strings_bytes;} MwRaceAIPack;
typedef struct {uint32_t key,spawn_key,model_key;const char *model,*preset;float position[3],rotation;bool explicit_spawn;} MwRaceAISpec;
typedef struct {float position[3];} MwRaceAIWaypoint;
typedef struct {
    DriveState motion;float height;
    MwRaceProgress progress;
    MwRaceAISpec spec;
    uint32_t path_count,path_cursor;
    unsigned blocked;
    bool admitted,failed;
} MwRaceAIActor;
typedef struct {float cruise_speed,corner_speed,lookahead,steering_gain,arrival_radius,grid_spacing,grid_lateral;} MwRaceAITuning;
typedef struct {uint32_t planner_nodes,planner_edges,nearest_nodes,drive_calls,guide_checks,gate_tests,blocked_steps;} MwRaceAIWork;
typedef struct {
    const MwEventCatalog *catalog;
    uint32_t event,count;
    float origin[3];
    uint32_t checkpoints[1024];MwRaceRoute route;
    MwRaceAIActor actors[MW_RACE_AI_ACTORS];
    MwRaceAIWaypoint paths[MW_RACE_AI_ACTORS][MW_RACE_AI_POINTS];
    MwRaceAITuning tuning;
    bool running,paused,step_ready;
} MwRaceAI;
/* Physical callback mirrors streamed_drive_step. Negative fails this tick
   without publishing actor motion/progress and latches rank unavailable until
   a successful tick;0 blocks,1 admits. */
typedef int (*MwRaceAIDrive)(void *,DriveState *,float *,DriveInput,float);
bool mw_race_ai_pack_open(MwRaceAIPack *,const void *,size_t);
bool mw_race_ai_spec(const MwRaceAIPack *,uint32_t event,unsigned,MwRaceAISpec *);
MwRaceAITuning mw_race_ai_default_tuning(void);
/* Startup/event-load only: bounded Dijkstra planning on genuine source road
   curves. Allocates temporary planner scratch, never in step. Native route and
   speed/grid policy is NOT the recovered original racing AI. Null source spawn
   refs use a clearly marked native grid adapter rather than a guessed child.
   Initialize output to zero; this potentially large state must not live on a
   small3DS thread stack. Successful begin borrows catalog and pack bytes. */
bool mw_race_ai_begin(MwRaceAI *,const MwRaceAIPack *,const MwEventCatalog *,
    const MwTrafficWorld *,uint32_t event,const float viewer_origin[3],MwRaceAIWork *);
/* Authoritative post-NIS actor placement. Before start only; keeps source model
   identity. Parent owns renderer/collision admission and supplies current pose. */
bool mw_race_ai_place(MwRaceAI *,unsigned,const float source_position[3],float viewer_yaw);
bool mw_race_ai_admit(MwRaceAI *,unsigned,bool ready);
bool mw_race_ai_start(MwRaceAI *);
bool mw_race_ai_pause(MwRaceAI *,bool);
/* Intended30Hz, seconds<=.1:<=3 physical callbacks,<=96 guide and96 gate checks.
   No allocation, disk IO, nearest-node scan or path search. */
bool mw_race_ai_step(MwRaceAI *,float seconds,MwRaceAIDrive,void *,MwRaceAIWork *);
/* Ranking refuses missing/failed actor admissions and unrelated player routes.
   Finish time, lap, checkpoint ordinal and distance-to-next determine native
   rank; exact-time ties favor the player (explicit adapter, not original ties).
   No money/unlock/career outcome is awarded by this module. */
bool mw_race_ai_rank(const MwRaceAI *,const MwRaceProgress *player,
    const float player_source[3],unsigned *rank);
#endif
