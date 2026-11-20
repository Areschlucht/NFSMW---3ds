#ifndef MW_STORY_AUDIO_H
#define MW_STORY_AUDIO_H
#include "mw_movie_audio.h"
typedef struct { MwMovie speech;MwMovieAudio queue;bool active; } MwStoryAudio;
/* Initialize zero; stop before reuse. Exclusively owns shared NDSP channel0.
 * Stop before movies. A successful start admits loading; issuedPlayback becomes
 * true only after CRC-verified actual PCM submission, never on muted fallback. */
bool mw_story_audio_start(MwStoryAudio*,const char *path,int sms_id);
bool mw_story_audio_update(MwStoryAudio*);
bool mw_story_audio_issued_playback(const MwStoryAudio*);
bool mw_story_audio_muted(const MwStoryAudio*);
bool mw_story_audio_finished(MwStoryAudio*);
void mw_story_audio_pause(MwStoryAudio*,bool);
void mw_story_audio_stop(MwStoryAudio*);
#endif
