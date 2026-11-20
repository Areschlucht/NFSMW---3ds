#include "mw_story_audio.h"
#include "mw_story_speech.h"
#include <string.h>
bool mw_story_audio_start(MwStoryAudio*a,const char*path,int sms_id){
 if(!a||a->active)return false;
 memset(a,0,sizeof(*a));if(!mw_story_speech_open(&a->speech,path,sms_id))return false;
 if(!mw_movie_audio_start(&a->queue,&a->speech)){mw_movie_close(&a->speech);return false;}
 a->active=true;return true;
}
bool mw_story_audio_update(MwStoryAudio*a){return a&&a->active&&mw_movie_audio_update(&a->queue);}
bool mw_story_audio_issued_playback(const MwStoryAudio*a){return a&&a->active&&a->queue.started&&!a->queue.muted_fallback&&!a->queue.failed;}
bool mw_story_audio_muted(const MwStoryAudio*a){return a&&a->active&&a->queue.muted_fallback;}
bool mw_story_audio_finished(MwStoryAudio*a){return a&&a->active&&!a->queue.failed&&mw_movie_audio_finished(&a->queue);}
void mw_story_audio_pause(MwStoryAudio*a,bool paused){if(a&&a->active)mw_movie_audio_pause(&a->queue,paused);}
void mw_story_audio_stop(MwStoryAudio*a){if(!a)return;if(a->active)mw_movie_audio_stop(&a->queue);mw_movie_close(&a->speech);memset(a,0,sizeof(*a));}
