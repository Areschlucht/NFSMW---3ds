#define _POSIX_C_SOURCE 200809L
#include "3ds.h"
#include <assert.h>
#include <math.h>
#include <pthread.h>
#include <sched.h>
#include <stdlib.h>
#include <time.h>
struct MovieTestThread {pthread_t id;void(*function)(void*);void*argument;};
typedef struct {ndspWaveBuf *head,*tail;u16 sequence,next;u32 position;bool paused;float rate;} Channel;
static Channel channels[10];static bool failed;static uint64_t milliseconds;static unsigned owners;
static Channel *get(int channel){assert(channel>=0&&channel<10);return channels+channel;}
void mock_movie_audio_yield(void){struct timespec duration={0,1000000};nanosleep(&duration,NULL);}
void LightLock_Init(LightLock*p){atomic_flag_clear(&p->held);}void LightLock_Lock(LightLock*p){while(atomic_flag_test_and_set_explicit(&p->held,memory_order_acquire))sched_yield();}void LightLock_Unlock(LightLock*p){atomic_flag_clear_explicit(&p->held,memory_order_release);}
void LightEvent_Init(LightEvent*p,int mode){(void)mode;atomic_init(&p->signaled,false);}void LightEvent_Signal(LightEvent*p){atomic_store_explicit(&p->signaled,true,memory_order_release);}void LightEvent_Wait(LightEvent*p){while(!atomic_exchange_explicit(&p->signaled,false,memory_order_acquire))mock_movie_audio_yield();}
static void *entry(void*p){Thread t=p;t->function(t->argument);return NULL;}
Thread threadCreate(void(*f)(void*),void*argument,size_t stack,int priority,int affinity,bool detached){(void)stack;(void)priority;(void)affinity;assert(!detached);Thread t=malloc(sizeof(*t));assert(t);t->function=f;t->argument=argument;if(pthread_create(&t->id,NULL,entry,t)){free(t);return NULL;}return t;}
Result threadJoin(Thread t,uint64_t timeout){(void)timeout;return pthread_join(t->id,NULL);}void threadFree(Thread t){free(t);}void*linearAlloc(size_t n){return malloc(n);}void linearFree(void*p){free(p);}Result DSP_FlushDataCache(const void*p,u32 bytes){assert(p&&bytes);return 0;}
uint64_t osGetTime(void){return milliseconds;}void mock_movie_audio_time(uint64_t value){milliseconds=value;}void mock_movie_audio_fail_init(bool value){failed=value;}
Result ndspInit(void){if(failed)return -1;assert(!owners);owners++;return 0;}void ndspExit(void){assert(owners==1);owners--;}
void ndspChnWaveBufClear(int channel){Channel*c=get(channel);while(c->head){c->head->status=NDSP_WBUF_DONE;c->head=c->head->next;}c->tail=NULL;}
void ndspChnReset(int channel){Channel*c=get(channel);ndspChnWaveBufClear(channel);*c=(Channel){0};}
void ndspChnSetInterp(int channel,int mode){(void)get(channel);assert(mode==NDSP_INTERP_LINEAR);}void ndspChnSetRate(int channel,float rate){assert(isfinite(rate)&&rate>0&&rate<=192000);get(channel)->rate=rate;}void ndspChnSetFormat(int channel,int format){(void)get(channel);assert(format==NDSP_FORMAT_STEREO_PCM16||format==NDSP_FORMAT_MONO_PCM16);}void ndspChnSetMix(int channel,const float*mix){(void)get(channel);assert(mix&&mix[0]>=0&&mix[0]<=1&&mix[1]==mix[0]);}
void ndspChnWaveBufAdd(int channel,ndspWaveBuf*w){Channel*c=get(channel);assert(owners&&w->data_vaddr&&w->nsamples);w->sequence_id=++c->next;w->status=NDSP_WBUF_QUEUED;w->next=NULL;if(c->tail)c->tail->next=w;else c->head=w;c->tail=w;}
u16 ndspChnGetWaveBufSeq(int channel){return get(channel)->sequence;}u32 ndspChnGetSamplePos(int channel){return get(channel)->position;}void ndspChnSetPaused(int channel,bool paused){get(channel)->paused=paused;}
unsigned mock_game_audio_queued(unsigned channel){unsigned n=0;for(ndspWaveBuf*w=get((int)channel)->head;w;w=w->next)n++;return n;}unsigned mock_movie_audio_queued(void){return mock_game_audio_queued(0);}unsigned mock_game_audio_owners(void){return owners;}float mock_game_audio_rate(unsigned channel){return get((int)channel)->rate;}
void mock_game_audio_advance(unsigned channel,u32 samples){Channel*c=get((int)channel);if(channel==0&&c->rate>0)milliseconds+=(uint64_t)samples*1000/(unsigned)c->rate;if(c->paused)return;while(samples&&c->head){ndspWaveBuf*w=c->head;if(w->status==NDSP_WBUF_QUEUED){w->status=NDSP_WBUF_PLAYING;c->sequence=w->sequence_id;c->position=0;}u32 left=w->nsamples-c->position,take=left<samples?left:samples;c->position+=take;samples-=take;if(c->position==w->nsamples){if(w->looping)c->position=0;else{w->status=NDSP_WBUF_DONE;c->head=w->next;if(!c->head)c->tail=NULL;}}}}
void mock_movie_audio_advance(u32 samples){mock_game_audio_advance(0,samples);}
