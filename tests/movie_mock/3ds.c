#include "3ds.h"
#include <assert.h>
#include <pthread.h>
#include <sched.h>
#include <stdlib.h>
#include <time.h>
struct MovieTestThread { pthread_t id;void (*function)(void *);void *argument; };
static uint64_t milliseconds;static bool fail_init,paused;static ndspWaveBuf *head,*tail;static u16 sequence,next_sequence;static u32 position;
void mock_movie_audio_yield(void){struct timespec duration={0,1000000};nanosleep(&duration,NULL);}
void LightLock_Init(LightLock *p){atomic_flag_clear(&p->held);}
void LightLock_Lock(LightLock *p){while(atomic_flag_test_and_set_explicit(&p->held,memory_order_acquire))sched_yield();}
void LightLock_Unlock(LightLock *p){atomic_flag_clear_explicit(&p->held,memory_order_release);}
void LightEvent_Init(LightEvent *p,int mode){(void)mode;atomic_init(&p->signaled,false);}
void LightEvent_Signal(LightEvent *p){atomic_store_explicit(&p->signaled,true,memory_order_release);}
void LightEvent_Wait(LightEvent *p){while(!atomic_exchange_explicit(&p->signaled,false,memory_order_acquire))mock_movie_audio_yield();}
static void *thread_entry(void *p){Thread t=p;t->function(t->argument);return NULL;}
Thread threadCreate(void (*f)(void *),void *arg,size_t stack,int priority,int affinity,bool detached)
{ (void)stack;(void)priority;(void)affinity;assert(!detached);Thread t=malloc(sizeof(*t));assert(t);t->function=f;t->argument=arg;if(pthread_create(&t->id,NULL,thread_entry,t)){free(t);return NULL;}return t; }
Result threadJoin(Thread t,uint64_t timeout){(void)timeout;return pthread_join(t->id,NULL);}
void threadFree(Thread t){free(t);}
void *linearAlloc(size_t n){return malloc(n);}void linearFree(void *p){free(p);}
Result DSP_FlushDataCache(const void *p,u32 n){assert(p&&n);return 0;}
uint64_t osGetTime(void){return milliseconds;}
void mock_movie_audio_time(uint64_t ms){milliseconds=ms;}void mock_movie_audio_fail_init(bool fail){fail_init=fail;}
Result ndspInit(void){return fail_init?-1:0;}void ndspExit(void){}
void ndspChnReset(int id){assert(id==0);head=tail=NULL;position=0;sequence=next_sequence=0;paused=false;}
void ndspChnSetInterp(int id,int mode){assert(id==0&&mode==NDSP_INTERP_LINEAR);}
void ndspChnSetRate(int id,float rate){assert(id==0&&rate==32000);}
void ndspChnSetFormat(int id,int format){assert(id==0&&format==NDSP_FORMAT_STEREO_PCM16);}
void ndspChnSetMix(int id,const float *mix){assert(id==0&&mix[0]==1&&mix[1]==1);}
void ndspChnWaveBufAdd(int id,ndspWaveBuf *w)
{ assert(id==0&&w->nsamples&&w->data_vaddr);w->sequence_id=++next_sequence;w->status=NDSP_WBUF_QUEUED;w->next=NULL;if(tail)tail->next=w;else head=w;tail=w; }
void ndspChnWaveBufClear(int id){assert(id==0);while(head){head->status=NDSP_WBUF_DONE;head=head->next;}tail=NULL;}
u16 ndspChnGetWaveBufSeq(int id){assert(id==0);return sequence;}u32 ndspChnGetSamplePos(int id){assert(id==0);return position;}
void ndspChnSetPaused(int id,bool value){assert(id==0);paused=value;}
unsigned mock_movie_audio_queued(void){unsigned count=0;for(ndspWaveBuf *w=head;w;w=w->next)count++;return count;}
void mock_movie_audio_advance(u32 samples)
{
    milliseconds+=(uint64_t)samples*1000/32000;
    if(paused)return;
    while(samples&&head){
        if(head->status==NDSP_WBUF_QUEUED){head->status=NDSP_WBUF_PLAYING;sequence=head->sequence_id;position=0;}
        u32 remain=head->nsamples-position,take=remain<samples?remain:samples;
        position+=take;samples-=take;
        if(position==head->nsamples){head->status=NDSP_WBUF_DONE;head=head->next;if(!head)tail=NULL;}
    }
}
