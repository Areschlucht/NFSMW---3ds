#ifndef MW_RACE_PROGRESS_H
#define MW_RACE_PROGRESS_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
/* Ordered original key references are borrowed and must outlive the race.
   Gate detection, original timing producers and AI remain caller responsibilities. */
typedef struct { const uint32_t *checkpoints; size_t count; uint32_t finish; unsigned laps; } MwRaceRoute;
typedef struct { MwRaceRoute route; size_t next; unsigned lap; uint64_t elapsed_us; bool running,finished; } MwRaceProgress;
typedef enum { MW_RACE_IGNORED,MW_RACE_CHECKPOINT,MW_RACE_LAP,MW_RACE_FINISHED } MwRaceEvent;
bool mw_race_begin(MwRaceProgress *,const MwRaceRoute *);
bool mw_race_tick(MwRaceProgress *,uint64_t delta_us);
MwRaceEvent mw_race_gate(MwRaceProgress *,uint32_t gate);
#endif
