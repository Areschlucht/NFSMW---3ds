#ifndef MW_STORY_SPEECH_H
#define MW_STORY_SPEECH_H
#include "mw_movie.h"
/* Owns an AUDIO-ONLY MwMovie view for shared CRC block/NDSP queues. video=NULL,
 * frames=0: this is not a movie and must not enter video rendering functions.
 * Initialize zero; close before reopening. Failed open leaves out unchanged. */
bool mw_story_speech_open(MwMovie *out,const char *path,int sms_id);
#endif
