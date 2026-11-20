#ifndef MW_OPENING_ACTORS_H
#define MW_OPENING_ACTORS_H
#include "mw_race_ai.h"
#include "mw_pursuit.h"

/* Opening-event integration, not recovered original AI. Public actor states
 * are the renderer's admitted models/poses. Keep this large object static or
 * on the heap; its paths must not occupy a small 3DS thread stack. */
typedef struct {
    MwRaceAI race;
    MwPursuit pursuit;
    uint32_t tick_phase;
    bool prepared,police_admitted,running,paused,simulation_ready,faulted;
} MwOpeningActors;
typedef struct {
    MwRaceAIWork race;
    MwPursuitWork pursuit;
    unsigned ticks,signals;
} MwOpeningActorsWork;

/* Startup only: borrows opened packs/catalog/road bytes; temporary planning
 * allocation is confined here. On failure leaves the existing state intact. */
bool mw_opening_actors_begin(MwOpeningActors *,const MwRaceAIPack *,
    const MwPursuitPack *,const MwEventCatalog *,const MwTrafficWorld *,
    uint32_t event,const float viewer_origin[3],uintptr_t player_actor,
    const float player_source[3]);
bool mw_opening_actors_admit_racer(MwOpeningActors *,unsigned,bool ready);
/* Must include an actual loaded COPMIDSIZE model and collision capability.
 * Required by start only when this event has original police triggers. */
bool mw_opening_actors_admit_police(MwOpeningActors *,bool ready);
bool mw_opening_actors_start(MwOpeningActors *);
bool mw_opening_actors_pause(MwOpeningActors *,bool);
bool mw_opening_actors_relocate(MwOpeningActors *,const float player_source[3]);
/* Call after admitted controlled-player motion. Exact source Width triggers
 * run each call; physical NPCs tick at bounded native 30Hz, at most three ticks
 * and fifteen drive callbacks per call (elapsed_us <=100000). No allocation,
 * IO, graph search, or fake motion. Pause freezes clocks, triggers and poses.
 * A failed physical callback invalidates rank until a successful later tick;
 * each underlying controller commits its own complete successful tick.
 * The work output, if provided, is replaced with this call's counters. */
bool mw_opening_actors_update(MwOpeningActors *,const DriveState *player,
    float player_height,const float player_source[3],float player_radius,
    uint64_t elapsed_us,MwRaceAIDrive,void *,MwOpeningActorsWork *);
/* Refuses a rank before an actual successful NPC tick or after failed motion.
 * Caller alone owns finish validation, rewards and scripted story outcomes. */
bool mw_opening_actors_rank(const MwOpeningActors *,const MwRaceProgress *,
    const float player_source[3],unsigned *rank);
void mw_opening_actors_reset(MwOpeningActors *);
#endif
