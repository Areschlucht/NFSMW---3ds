#ifndef MW_STORY_TUTORIAL_H
#define MW_STORY_TUTORIAL_H
#include <stdbool.h>
#include <stdint.h>
typedef struct { const char *movie_stem; uint32_t profile_flags; } MwStoryTutorial;
/* Original bounded selector801C6688..801C6710. Caller must establish outer
   manager/player/event preconditions. Flags are updated at selection time,
   before playback, as in the original. No stem means no tutorial selected;
   it is not proof that an arbitrary career movie has finished. */
bool mw_story_tutorial_select(int32_t original_event_type,uint32_t profile_flags,MwStoryTutorial *);
#endif
