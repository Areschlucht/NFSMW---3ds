#ifndef MOVIE_TEST_3DS_H
#define MOVIE_TEST_3DS_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdatomic.h>
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;typedef int32_t Result;
#define R_FAILED(r) ((r)<0)
enum { RESET_ONESHOT,NDSP_INTERP_LINEAR,NDSP_FORMAT_STEREO_PCM16 };
enum { NDSP_WBUF_FREE,NDSP_WBUF_QUEUED,NDSP_WBUF_PLAYING,NDSP_WBUF_DONE };
typedef struct { atomic_flag held; } LightLock;
typedef struct { atomic_bool signaled; } LightEvent;
typedef struct MovieTestThread *Thread;
typedef struct tag_ndspWaveBuf {
    const void *data_vaddr;u32 nsamples;void *adpcm_data;u32 offset;bool looping;u8 status;u16 sequence_id;struct tag_ndspWaveBuf *next;
} ndspWaveBuf;
void LightLock_Init(LightLock *);void LightLock_Lock(LightLock *);void LightLock_Unlock(LightLock *);
void LightEvent_Init(LightEvent *,int);void LightEvent_Wait(LightEvent *);void LightEvent_Signal(LightEvent *);
Thread threadCreate(void (*)(void *),void *,size_t,int,int,bool);
Result threadJoin(Thread,uint64_t);void threadFree(Thread);
void *linearAlloc(size_t);void linearFree(void *);Result DSP_FlushDataCache(const void *,u32);
uint64_t osGetTime(void);
Result ndspInit(void);void ndspExit(void);
void ndspChnReset(int);void ndspChnSetInterp(int,int);void ndspChnSetRate(int,float);void ndspChnSetFormat(int,int);void ndspChnSetMix(int,const float *);
void ndspChnWaveBufAdd(int,ndspWaveBuf *);void ndspChnWaveBufClear(int);
u16 ndspChnGetWaveBufSeq(int);u32 ndspChnGetSamplePos(int);void ndspChnSetPaused(int,bool);
void mock_movie_audio_advance(u32);void mock_movie_audio_time(uint64_t);void mock_movie_audio_fail_init(bool);
unsigned mock_movie_audio_queued(void);void mock_movie_audio_yield(void);
#endif
