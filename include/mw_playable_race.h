#ifndef MW_PLAYABLE_RACE_H
#define MW_PLAYABLE_RACE_H
#include "mw_race_session.h"

/* Practical native-port detector, NOT the recovered GameCube actor narrowphase.
   Source coordinates are (X,Y horizontal,Z up). Radius expands source gate
   boxes conservatively; the caller chooses its controlled actor's proxy. */
typedef enum {
    MW_PLAYABLE_EMPTY, MW_PLAYABLE_LOADING, MW_PLAYABLE_READY,
    MW_PLAYABLE_COUNTDOWN, MW_PLAYABLE_RUNNING, MW_PLAYABLE_PAUSED,
    MW_PLAYABLE_FINISHED, MW_PLAYABLE_CANCELLED
} MwPlayableRacePhase;
typedef struct {
    MwRaceSession *session;
    const MwEventCatalog *catalog;
    MwPlayableRacePhase phase, resume_phase;
    uint64_t countdown_us;
    float previous_source[3], actor_radius;
    uint32_t last_gate;
} MwPlayableRace;
typedef struct {
    MwRaceEvent event; /* Last accepted event this step, or MW_RACE_IGNORED. */
    uint32_t gate;
    unsigned crossed;
    bool started, finished;
    double finish_fraction; /* [0,1] of the current running motion segment. */
} MwPlayableRaceUpdate;

/* All views/session storage must stay alive and unmoved. Initialize to zero.
   Session exclusively belongs to this controller until finish/cancel. Failure
   leaves both controller and session unchanged. Only source P2P/circuit. */
bool mw_playable_race_prepare(MwPlayableRace *,MwRaceSession *,const MwEventCatalog *,
    uint32_t event,const MwAliasStore *,uintptr_t actor,float actor_radius);
bool mw_playable_race_admit(MwPlayableRace *,bool render,bool collision,bool activation);
/* Caller chooses countdown policy AFTER required movies/intro complete. This
   code invents no original countdown duration or automatic movie skip. */
bool mw_playable_race_countdown(MwPlayableRace *,uint64_t duration_us,const float source_position[3]);
/* Move the controlled actor only in RUNNING. During COUNTDOWN hold its pose.
   Sweeps can accept several sequential gates in chronological order. Finishing
   stops elapsed time at the interpolated hit, not at the end of the frame.
   Paused, wrong-actor, invalid/nonfinite/overflow input fails without mutation. */
bool mw_playable_race_update(MwPlayableRace *,uintptr_t actor,const float source_position[3],
    uint64_t delta_us,MwPlayableRaceUpdate *);
/* After an explicit admitted respawn/recovery, discard the teleport sweep.
   This does not advance gates or alter elapsed time. */
bool mw_playable_race_relocate(MwPlayableRace *,uintptr_t actor,const float source_position[3]);
bool mw_playable_race_pause(MwPlayableRace *);
bool mw_playable_race_resume(MwPlayableRace *);
bool mw_playable_race_cancel(MwPlayableRace *);
bool mw_playable_race_next(const MwPlayableRace *,MwEventNode *);
/* Native viewer adapter: (sourceX,sourceZ,-sourceY), yaw0 points viewer+Z.
   Source forward=(cos R,sin R,0); viewer yaw=(90+R) degrees. Recovery uses the
   last accepted source gate center; caller must admit/sample physical ground. */
bool mw_playable_race_start_pose(const MwPlayableRace *,float source_position[3],float *viewer_yaw);
bool mw_playable_race_recovery_pose(const MwPlayableRace *,float source_position[3],float *viewer_yaw);

/* Public pure geometry helper for testing/integration. Radius takes precedence
   over Dimensions as in source construction. Box half-extents in original
   internal basis are (DimensionsY/2, DimensionsZ, DimensionsX/2), yaw=-R.
   Entry only: beginning inside the expanded volume does not generate an entry.
   Touching counts as inside. Unsupported/incomplete nodes fail without writes. */
bool mw_playable_race_sweep(const MwEventNode *,const float from_source[3],
    const float to_source[3],float radius,double *entry_fraction);
/* Original Width-only fallback is a kind1 box, not a sphere/kind3 slab:
   internal half-extents=(Width/2,50,.5). Pose needs Position+Rotation only.
   The same explicitly native swept actor proxy is used after that conversion. */
bool mw_playable_race_width_sweep(const MwEventNode *pose,float source_width,
    const float from_source[3],const float to_source[3],float radius,double *entry_fraction);
#endif
