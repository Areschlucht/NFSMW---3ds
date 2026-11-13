#ifndef MW_MOVIE_AUDIO_H
#define MW_MOVIE_AUDIO_H
#include <3ds.h>
#include "mw_movie.h"
enum { MW_MOVIE_AUDIO_QUEUES=3 };
typedef struct {
    ndspWaveBuf wave;
    uint32_t block,first_sample,frames;
    unsigned state;
} MwMovieAudioSlot;
typedef struct {
    MwMovie *movie;
    Thread worker;
    LightLock lock;
    LightEvent wake;
    unsigned char *pcm;
    MwMovieAudioSlot slots[MW_MOVIE_AUDIO_QUEUES];
    uint32_t next_read_block,next_queue_block,completed_samples,last_played;
    bool active,ndsp_ready,muted_fallback,paused,started,failed,
         worker_stop,worker_failed,audio_done;
    Result ndsp_result;
    uint64_t wall_start_ms,pause_start_ms,paused_ms,tail_start_ms;
} MwMovieAudio;
/* Initialize to zero; stop before reopening/moving/closing the borrowed movie.
   Owns channel0 and ndspInit/Exit for this playback. DSP unavailable is an
   explicit muted_fallback state; video can still use the wall clock. Fallback
   must not be reported as successful original audio playback. */
bool mw_movie_audio_start(MwMovieAudio *,MwMovie *);
/* Main-thread, bounded queue work only: no FILE reads, decode, sleep or wait.
   A worker fills three fixed linear buffers and validates PCM CRCs. On false,
   stop playback; failed data is never submitted to NDSP. */
bool mw_movie_audio_update(MwMovieAudio *);
uint64_t mw_movie_audio_played_samples(MwMovieAudio *);
/* Uses DSP sample progress; after actual audio EOF continues a wall-clock tail
   if video is longer. In muted_fallback this is pause-aware wall time. */
uint64_t mw_movie_audio_elapsed_us(MwMovieAudio *);
bool mw_movie_audio_finished(MwMovieAudio *);
void mw_movie_audio_pause(MwMovieAudio *,bool paused);
void mw_movie_audio_stop(MwMovieAudio *);
#endif
