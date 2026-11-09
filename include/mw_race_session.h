#ifndef MW_RACE_SESSION_H
#define MW_RACE_SESSION_H
#include "mw_alias.h"
#include "mw_event_catalog.h"
typedef enum { MW_SESSION_IDLE,MW_SESSION_LOADING,MW_SESSION_READY,MW_SESSION_RUNNING,
    MW_SESSION_PAUSED,MW_SESSION_FINISHED,MW_SESSION_CANCELLED } MwRaceSessionPhase;
typedef struct {
    MwRaceSessionPhase phase;
    uint32_t alias_id,event_key;
    uintptr_t player_actor;
    MwEventNode source_start;
    MwRaceRoute route;
    MwRaceProgress progress;
    uint32_t checkpoint_keys[1024];
} MwRaceSession;
/* Startup-only listing of source courses with supported progress rules.
   This is preparation eligibility, not a claim that an event can start. */
bool mw_race_session_courses(const MwEventCatalog *,bool localized_only,uint32_t *,size_t,size_t *);
/* Native port lifecycle, not a recovered original career interpreter. Initialize
   to zero. Only P2P/circuit are supported; other source rules remain unimplemented.
   Session owns its ordered keys, and must not be copied/moved after preparation. */
bool mw_race_session_prepare(MwRaceSession *,const MwEventCatalog *,uint32_t,const MwAliasStore *,uintptr_t);
/* All three admissions must be confirmed for THIS event. No implicit fallback
   for missing collision, renderer or event activation data. */
bool mw_race_session_admit(MwRaceSession *,bool render_ready,bool collision_ready,bool activation_ready);
/* Caller starts after its countdown/intro policy completes. No movie auto-skip. */
bool mw_race_session_start(MwRaceSession *);
bool mw_race_session_pause(MwRaceSession *);
bool mw_race_session_resume(MwRaceSession *);
bool mw_race_session_tick(MwRaceSession *,uint64_t delta_us);
/* Call only for an authoritative trigger-entry notification. This API supplies
   no point/radius detector or original actor-shape implementation. */
MwRaceEvent mw_race_session_enter(MwRaceSession *,uintptr_t actor,uint32_t gate);
bool mw_race_session_cancel(MwRaceSession *);
#endif
