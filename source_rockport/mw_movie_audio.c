#include "mw_movie_audio.h"
#include <string.h>

enum { SLOT_EMPTY,SLOT_FILLING,SLOT_READY,SLOT_QUEUED };

static void fill_worker(void *context)
{
    MwMovieAudio *a=context;
    for(;;){
        unsigned slot=MW_MOVIE_AUDIO_QUEUES;uint32_t block=0;
        LightLock_Lock(&a->lock);
        bool stop=a->worker_stop;
        if(!stop&&a->next_read_block<a->movie->audio_blocks){
            for(unsigned i=0;i<MW_MOVIE_AUDIO_QUEUES;i++)if(a->slots[i].state==SLOT_EMPTY){
                slot=i;block=a->next_read_block++;a->slots[i].state=SLOT_FILLING;break;
            }
        }
        LightLock_Unlock(&a->lock);
        if(stop)return;
        if(slot==MW_MOVIE_AUDIO_QUEUES){LightEvent_Wait(&a->wake);continue;}
        uint32_t frames=0;
        bool ok=mw_movie_audio_block(a->movie,block,a->pcm+slot*MW_MOVIE_AUDIO_BLOCK_BYTES,MW_MOVIE_AUDIO_BLOCK_BYTES,&frames);
        if(ok)DSP_FlushDataCache(a->pcm+slot*MW_MOVIE_AUDIO_BLOCK_BYTES,frames*4);
        LightLock_Lock(&a->lock);
        if(!ok){a->worker_failed=true;a->worker_stop=true;}
        else {
            MwMovieAudioSlot *s=&a->slots[slot];s->block=block;s->first_sample=block*MW_MOVIE_AUDIO_BLOCK_FRAMES;s->frames=frames;s->state=SLOT_READY;
        }
        LightLock_Unlock(&a->lock);
    }
}

bool mw_movie_audio_start(MwMovieAudio *a,MwMovie *movie)
{
    if(!a||!movie||!movie->audio||!movie->sample_rate||!movie->audio_frames)return false;
    memset(a,0,sizeof(*a));a->movie=movie;a->active=true;
    LightLock_Init(&a->lock);LightEvent_Init(&a->wake,RESET_ONESHOT);
    a->ndsp_result=ndspInit();
    if(R_FAILED(a->ndsp_result)){a->muted_fallback=true;a->started=true;a->wall_start_ms=osGetTime();return true;}
    a->ndsp_ready=true;
    a->pcm=linearAlloc(MW_MOVIE_AUDIO_QUEUES*MW_MOVIE_AUDIO_BLOCK_BYTES);
    if(!a->pcm){mw_movie_audio_stop(a);return false;}
    ndspChnReset(0);ndspChnSetInterp(0,NDSP_INTERP_LINEAR);ndspChnSetRate(0,(float)movie->sample_rate);ndspChnSetFormat(0,NDSP_FORMAT_STEREO_PCM16);
    float mix[12]={1,1};ndspChnSetMix(0,mix);
    a->worker=threadCreate(fill_worker,a,16*1024,0x38,-2,false);
    if(!a->worker){mw_movie_audio_stop(a);return false;}
    return true;
}

bool mw_movie_audio_update(MwMovieAudio *a)
{
    if(!a||!a->active)return false;
    if(a->muted_fallback)return true;
    LightLock_Lock(&a->lock);
    if(a->worker_failed){a->failed=true;LightLock_Unlock(&a->lock);return false;}
    unsigned ready=0,queued=0;
    for(unsigned i=0;i<MW_MOVIE_AUDIO_QUEUES;i++){
        MwMovieAudioSlot *s=&a->slots[i];
        if(s->state==SLOT_QUEUED&&s->wave.status==NDSP_WBUF_DONE){
            uint32_t end=s->first_sample+s->frames;if(end>a->completed_samples)a->completed_samples=end;
            s->state=SLOT_EMPTY;LightEvent_Signal(&a->wake);
        }
        ready+=s->state==SLOT_READY;queued+=s->state==SLOT_QUEUED;
    }
    bool can_start=a->started||ready>=2||(a->movie->audio_blocks==1&&ready==1);
    if(can_start&&!a->paused){
        for(unsigned count=0;count<MW_MOVIE_AUDIO_QUEUES;count++){
            MwMovieAudioSlot *s=NULL;
            for(unsigned i=0;i<MW_MOVIE_AUDIO_QUEUES;i++)if(a->slots[i].state==SLOT_READY&&a->slots[i].block==a->next_queue_block){s=&a->slots[i];break;}
            if(!s)break;
            unsigned i=(unsigned)(s-a->slots);memset(&s->wave,0,sizeof(s->wave));
            s->wave.data_vaddr=a->pcm+i*MW_MOVIE_AUDIO_BLOCK_BYTES;s->wave.nsamples=s->frames;
            ndspChnWaveBufAdd(0,&s->wave);s->state=SLOT_QUEUED;++a->next_queue_block;++queued;
            if(!a->started){a->started=true;a->wall_start_ms=osGetTime();a->paused_ms=0;}
        }
    }
    if(a->next_queue_block==a->movie->audio_blocks&&!queued&&a->completed_samples==a->movie->audio_frames&&!a->audio_done){a->audio_done=true;a->tail_start_ms=osGetTime();}
    LightLock_Unlock(&a->lock);
    return true;
}

uint64_t mw_movie_audio_played_samples(MwMovieAudio *a)
{
    if(!a||!a->active||!a->started)return 0;
    uint64_t played=0;
    if(a->muted_fallback){
        uint64_t now=a->paused?a->pause_start_ms:osGetTime();
        uint64_t ms=now-a->wall_start_ms-a->paused_ms;played=ms*a->movie->sample_rate/1000;
        if(played>a->movie->audio_frames)played=a->movie->audio_frames;
        return played;
    }
    LightLock_Lock(&a->lock);played=a->completed_samples;
    for(unsigned attempt=0;attempt<2;attempt++){
        u16 seq=ndspChnGetWaveBufSeq(0);u32 pos=ndspChnGetSamplePos(0);
        if(seq!=ndspChnGetWaveBufSeq(0))continue;
        for(unsigned i=0;i<MW_MOVIE_AUDIO_QUEUES;i++){
            MwMovieAudioSlot *s=&a->slots[i];
            if(s->state!=SLOT_QUEUED||s->wave.sequence_id!=seq)continue;
            if(pos>s->frames)pos=s->frames;
            uint64_t value=(uint64_t)s->first_sample+pos;if(value>played)played=value;
        }
        break;
    }
    if(played<a->last_played)played=a->last_played;
    if(played>a->movie->audio_frames)played=a->movie->audio_frames;
    a->last_played=(uint32_t)played;LightLock_Unlock(&a->lock);return played;
}

uint64_t mw_movie_audio_elapsed_us(MwMovieAudio *a)
{
    if(!a||!a->active||!a->started)return 0;
    uint64_t now=a->paused?a->pause_start_ms:osGetTime();
    if(a->muted_fallback)return (now-a->wall_start_ms-a->paused_ms)*1000;
    if(a->audio_done){
        uint64_t tail=now>a->tail_start_ms?now-a->tail_start_ms:0;
        return ((uint64_t)a->movie->audio_frames*1000000/a->movie->sample_rate)+tail*1000;
    }
    return mw_movie_audio_played_samples(a)*1000000/a->movie->sample_rate;
}
bool mw_movie_audio_finished(MwMovieAudio *a)
{ return a&&a->active&&(a->muted_fallback?mw_movie_audio_played_samples(a)>=a->movie->audio_frames:a->audio_done); }

void mw_movie_audio_pause(MwMovieAudio *a,bool paused)
{
    if(!a||!a->active||a->paused==paused)return;
    uint64_t now=osGetTime();
    if(paused)a->pause_start_ms=now;
    else {
        uint64_t duration=now-a->pause_start_ms;a->paused_ms+=duration;
        if(a->audio_done)a->tail_start_ms+=duration;
    }
    a->paused=paused;if(a->ndsp_ready)ndspChnSetPaused(0,paused);
}
void mw_movie_audio_stop(MwMovieAudio *a)
{
    if(!a||!a->active)return;
    if(a->worker){
        LightLock_Lock(&a->lock);a->worker_stop=true;LightLock_Unlock(&a->lock);LightEvent_Signal(&a->wake);
        threadJoin(a->worker,UINT64_MAX);threadFree(a->worker);
    }
    if(a->ndsp_ready){ndspChnWaveBufClear(0);ndspChnReset(0);ndspExit();}
    if(a->pcm)linearFree(a->pcm);
    memset(a,0,sizeof(*a));
}
