#define _POSIX_C_SOURCE 200809L
#include "mw_movie_audio.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static void wait_queue(MwMovieAudio *audio)
{
    for(unsigned attempt=0;attempt<2000;attempt++){
        assert(mw_movie_audio_update(audio));
        if(mock_movie_audio_queued()>=2)return;
        mock_movie_audio_yield();
    }
    assert(!"Movie worker did not prefill its bounded queue");
}
int main(int argc,char **argv)
{
    assert(argc==2);MwMovie movie={0};assert(mw_movie_open(&movie,argv[1]));MwMovieAudio audio={0};
    mock_movie_audio_time(1000);mock_movie_audio_fail_init(false);
    assert(mw_movie_audio_start(&audio,&movie)&&audio.ndsp_ready&&!audio.muted_fallback);wait_queue(&audio);
    assert(mw_movie_audio_played_samples(&audio)==0);mock_movie_audio_advance(512);
    assert(mw_movie_audio_played_samples(&audio)==512&&mw_movie_audio_elapsed_us(&audio)==16000);
    mw_movie_audio_pause(&audio,true);mock_movie_audio_advance(3200);
    assert(mw_movie_audio_played_samples(&audio)==512&&mw_movie_audio_elapsed_us(&audio)==16000);
    mw_movie_audio_pause(&audio,false);
    uint64_t previous=512;
    for(unsigned step=0;step<4000&&!mw_movie_audio_finished(&audio);step++){
        mock_movie_audio_advance(512);assert(mw_movie_audio_update(&audio));
        uint64_t samples=mw_movie_audio_played_samples(&audio);assert(samples>=previous&&samples<=movie.audio_frames);previous=samples;
        mock_movie_audio_yield();
    }
    assert(mw_movie_audio_finished(&audio)&&previous==movie.audio_frames);
    uint64_t end=mw_movie_audio_elapsed_us(&audio);assert(end==3765125);
    mock_movie_audio_advance(3200);assert(mw_movie_audio_elapsed_us(&audio)==end+100000);
    mw_movie_audio_pause(&audio,true);mock_movie_audio_advance(6400);assert(mw_movie_audio_elapsed_us(&audio)==end+100000);
    mw_movie_audio_pause(&audio,false);mock_movie_audio_advance(3200);assert(mw_movie_audio_elapsed_us(&audio)==end+200000);
    mw_movie_audio_stop(&audio);mw_movie_audio_stop(&audio);assert(!audio.active&&!audio.worker&&!audio.pcm);
    /* Device unavailable is an explicit muted clock fallback, not success audio. */
    mock_movie_audio_fail_init(true);mock_movie_audio_time(10000);
    assert(mw_movie_audio_start(&audio,&movie)&&audio.muted_fallback&&!audio.ndsp_ready);
    mock_movie_audio_time(10500);assert(mw_movie_audio_played_samples(&audio)==16000&&mw_movie_audio_elapsed_us(&audio)==500000);
    mw_movie_audio_pause(&audio,true);mock_movie_audio_time(12500);assert(mw_movie_audio_elapsed_us(&audio)==500000);
    mw_movie_audio_pause(&audio,false);mock_movie_audio_time(13000);assert(mw_movie_audio_elapsed_us(&audio)==1000000);
    mw_movie_audio_stop(&audio);mock_movie_audio_fail_init(false);
    /* Stop during prefill wakes/joins worker without freeing live PCM pointers. */
    for(unsigned i=0;i<12;i++){assert(mw_movie_audio_start(&audio,&movie));mw_movie_audio_stop(&audio);}
    FILE *f=fopen(argv[1],"rb");assert(f);unsigned char *raw=malloc(movie.total_bytes);assert(raw&&fread(raw,1,movie.total_bytes,f)==movie.total_bytes);fclose(f);raw[movie.audio_at+20]^=1;
    char path[]="/tmp/nfsmw-movie-audio.XXXXXX";int fd=mkstemp(path);assert(fd>=0);f=fdopen(fd,"wb");assert(f&&fwrite(raw,1,movie.total_bytes,f)==movie.total_bytes&&!fclose(f));free(raw);
    mw_movie_close(&movie);assert(mw_movie_open(&movie,path));assert(mw_movie_audio_start(&audio,&movie));
    bool detected=false;for(unsigned i=0;i<2000;i++){if(!mw_movie_audio_update(&audio)){detected=true;break;}mock_movie_audio_yield();}
    assert(detected&&audio.failed&&!mock_movie_audio_queued());mw_movie_audio_stop(&audio);mw_movie_close(&movie);assert(!unlink(path));
    puts("Movie audio: threaded three-buffer order, sample clock, pause/tail, muted fallback, prefill cancellation and CRC failure passed.");
    return 0;
}
