#ifndef MW_STORY_SERVICES_H
#define MW_STORY_SERVICES_H
#include <stdint.h>
/* Source EngineRacer scheduling semantics. Caller supplies the original-style
 * simulation clock, paused with simulation. This is not wall-clock time. */
typedef struct { float deadline; uint8_t blown; } MwStoryEngine;
void mw_story_engine_reset(MwStoryEngine *engine);
int mw_story_engine_sabotage(MwStoryEngine *engine,float simulation_clock,float delay);
/* Returns 1 exactly once for an actual transition to engine-blown. Dispatch the
 * career EngineBlown notification only for this return value. */
int mw_story_engine_blow(MwStoryEngine *engine);
int mw_story_engine_tick(MwStoryEngine *engine,float simulation_clock);
/* Original SMS mapping. This identifies a speech selector, not an audio file.
 * No CallStarted event is synthesized: the real playback service must emit it. */
int mw_story_cell_selector(int sms_id,uint32_t *bucket,uint32_t *number);
#endif
