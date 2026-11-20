#include "mw_game_audio.h"
#include <math.h>
#include <string.h>
static bool engine_stream_update(MwGameAudio*);
static void release(MwGameAudioClip*c){if(c->pcm)linearFree(c->pcm);memset(c,0,sizeof(*c));}
static void gain(int channel,float value){float mix[12]={value,value};ndspChnSetMix(channel,mix);}
static void configure(int channel,uint32_t rate){ndspChnWaveBufClear(channel);ndspChnReset(channel);ndspChnSetInterp(channel,NDSP_INTERP_LINEAR);ndspChnSetRate(channel,(float)rate);ndspChnSetFormat(channel,NDSP_FORMAT_STEREO_PCM16);}
static bool clip_load(MwGameAudioClip*out,const char*path,size_t cap,bool engine){
 MwMovie m={0};MwAudioStreamInfo info;
 if(!mw_audio_stream_open(&m,&info,path))return false;
 bool valid=(uint64_t)m.audio_frames*4<=cap;
 if(engine)valid=valid&&(info.flags&1u)&&!(info.flags&2u)&&info.reference_rpm>0;
 else valid=valid&&!info.flags;
 uint32_t start=engine?info.loop_start:0,end=engine?info.loop_end:m.audio_frames;
 if(!valid){mw_movie_close(&m);return false;}
 MwGameAudioClip next={.frames=end-start,.rate=m.sample_rate,.info=info};
 next.pcm=linearAlloc((size_t)next.frames*4);if(!next.pcm){mw_movie_close(&m);return false;}
 unsigned char scratch[MW_MOVIE_AUDIO_BLOCK_BYTES];
 uint32_t first=start/4096,last=(end-1)/4096,done=0;
 for(uint32_t b=first;b<=last;b++){
  uint32_t count=0;if(!mw_movie_audio_block(&m,b,scratch,sizeof(scratch),&count))goto fail;
  uint32_t lo=b==first?start%4096:0,hi=b==last?(end-1)%4096+1:count;
  if(hi>count||lo>=hi)goto fail;
  memcpy(next.pcm+done*4,scratch+lo*4,(hi-lo)*4);done+=hi-lo;
 }
 if(done!=next.frames)goto fail;
 DSP_FlushDataCache(next.pcm,done*4);mw_movie_close(&m);next.loaded=true;
 release(out);*out=next;return true;
fail:mw_movie_close(&m);release(&next);return false;
}
bool mw_game_audio_start(MwGameAudio*a,const char*path){
 if(!a||a->active||!path)return false;
 MwMovie m={0};MwAudioStreamInfo info;
 if(!mw_audio_stream_open(&m,&info,path))return false;
 if(info.flags){mw_movie_close(&m);return false;}
 memset(a,0,sizeof(*a));a->music=m;a->music_info=info;
 if(!mw_movie_audio_start(&a->stream,&a->music)){mw_movie_close(&a->music);memset(a,0,sizeof(*a));return false;}
 a->active=true;return true;
}
bool mw_game_audio_update(MwGameAudio*a){return a&&a->active&&mw_movie_audio_update(&a->stream)&&engine_stream_update(a);}
bool mw_game_audio_muted(const MwGameAudio*a){return a&&a->active&&a->stream.muted_fallback;}
bool mw_game_audio_issued(const MwGameAudio*a){return a&&a->active&&a->stream.started&&!a->stream.muted_fallback&&!a->stream.failed;}
bool mw_game_audio_finished(MwGameAudio*a){return a&&a->active&&!a->stream.failed&&mw_movie_audio_finished(&a->stream);}
void mw_game_audio_pause(MwGameAudio*a,bool paused){
 if(!a||!a->active)return;
 mw_movie_audio_pause(&a->stream,paused);
 if(a->engine_stream.active){LightLock_Lock(&a->engine_stream.lock);a->engine_stream.paused=paused;LightLock_Unlock(&a->engine_stream.lock);LightEvent_Signal(&a->engine_stream.wake);}
 if(a->stream.ndsp_ready)for(int channel=1;channel<=1+MW_GAME_AUDIO_EFFECTS;channel++)ndspChnSetPaused(channel,paused);
}
void mw_game_audio_stop(MwGameAudio*a){
 if(!a)return;
 mw_game_audio_engine_stream_stop(a);
 if(a->stream.ndsp_ready)for(int channel=1;channel<=1+MW_GAME_AUDIO_EFFECTS;channel++){ndspChnWaveBufClear(channel);ndspChnReset(channel);}
 mw_movie_audio_stop(&a->stream);mw_movie_close(&a->music);
 release(&a->engine);for(unsigned i=0;i<MW_GAME_AUDIO_EFFECTS;i++)release(a->effects+i);memset(a,0,sizeof(*a));
}
bool mw_game_audio_load_engine(MwGameAudio*a,const char*path){
 if(!a||!a->active||!a->stream.ndsp_ready||a->stream.failed||a->engine_stream.active||a->engine.wave.status==NDSP_WBUF_QUEUED||a->engine.wave.status==NDSP_WBUF_PLAYING)return false;
 return clip_load(&a->engine,path,MW_GAME_AUDIO_ENGINE_BYTES,true);
}
bool mw_game_audio_load_effect(MwGameAudio*a,unsigned slot,const char*path){
 if(!a||!a->active||slot>=MW_GAME_AUDIO_EFFECTS||!a->stream.ndsp_ready||a->stream.failed)return false;
 MwGameAudioClip*c=a->effects+slot;if(c->wave.status==NDSP_WBUF_QUEUED||c->wave.status==NDSP_WBUF_PLAYING)return false;
 return clip_load(c,path,MW_GAME_AUDIO_EFFECT_BYTES,false);
}
bool mw_game_audio_engine(MwGameAudio*a,float rpm,float level,bool enabled){
 if(!a||!a->active||!a->stream.ndsp_ready||a->stream.failed||a->engine_stream.active)return false;
 MwGameAudioClip*c=&a->engine;
 if(!enabled){ndspChnWaveBufClear(1);ndspChnReset(1);memset(&c->wave,0,sizeof(c->wave));return true;}
 if(!c->loaded||!isfinite(rpm)||rpm<=0||!isfinite(level)||level<0||level>1||!isfinite(c->info.reference_rpm)||c->info.reference_rpm<=0)return false;
 float ratio=rpm/c->info.reference_rpm;if(ratio<.25f||ratio>4||a->stream.paused)return false;
 if(c->wave.status!=NDSP_WBUF_QUEUED&&c->wave.status!=NDSP_WBUF_PLAYING){
  configure(1,c->rate);memset(&c->wave,0,sizeof(c->wave));c->wave.data_vaddr=c->pcm;c->wave.nsamples=c->frames;c->wave.looping=true;ndspChnWaveBufAdd(1,&c->wave);
 }
 ndspChnSetRate(1,(float)c->rate*ratio);gain(1,level);return true;
}
bool mw_game_audio_effect(MwGameAudio*a,unsigned slot,float level){
 if(!a||!a->active||!a->stream.ndsp_ready||a->stream.failed||a->stream.paused||slot>=MW_GAME_AUDIO_EFFECTS||!isfinite(level)||level<0||level>1)return false;
 MwGameAudioClip*c=a->effects+slot;if(!c->loaded)return false;
 int channel=2+(int)slot;configure(channel,c->rate);memset(&c->wave,0,sizeof(c->wave));c->wave.data_vaddr=c->pcm;c->wave.nsamples=c->frames;gain(channel,level);ndspChnWaveBufAdd(channel,&c->wave);return true;
}

static void engine_worker(void*context){
 MwGameAudioEngineQueue*q=context;
 for(;;){
  unsigned slot=MW_GAME_AUDIO_ENGINE_QUEUES,sequence=0,generation;float rpm,load;
  LightLock_Lock(&q->lock);bool stop=q->stop;generation=q->generation;rpm=q->rpm;load=q->load;
  if(!stop&&q->enabled&&!q->paused)for(unsigned i=0;i<MW_GAME_AUDIO_ENGINE_QUEUES;i++)if(!q->state[i]){slot=i;q->state[i]=1;sequence=q->next_render++;break;}
  LightLock_Unlock(&q->lock);if(stop)return;
  if(slot==MW_GAME_AUDIO_ENGINE_QUEUES){LightEvent_Wait(&q->wake);continue;}
  int16_t*pcm=q->pcm+slot*MW_GAME_AUDIO_ENGINE_FRAMES;
  bool ok=q->render(q->context,pcm,MW_GAME_AUDIO_ENGINE_FRAMES,rpm,load);
  if(ok)DSP_FlushDataCache(pcm,MW_GAME_AUDIO_ENGINE_FRAMES*2);
  LightLock_Lock(&q->lock);
  if(!ok){q->failed=true;q->stop=true;q->state[slot]=0;}
  else if(generation==q->generation){q->serial[slot]=sequence;q->state[slot]=2;}
  else q->state[slot]=0;
  LightLock_Unlock(&q->lock);
 }
}
static bool engine_stream_update(MwGameAudio*a){
 MwGameAudioEngineQueue*q=&a->engine_stream;if(!q->active)return true;
 LightLock_Lock(&q->lock);
 if(q->failed){LightLock_Unlock(&q->lock);ndspChnWaveBufClear(1);return false;}
 for(unsigned i=0;i<MW_GAME_AUDIO_ENGINE_QUEUES;i++)if(q->state[i]==3&&q->wave[i].status==NDSP_WBUF_DONE){q->state[i]=0;LightEvent_Signal(&q->wake);}
 if(q->enabled&&!q->paused)for(unsigned count=0;count<MW_GAME_AUDIO_ENGINE_QUEUES;count++){
  unsigned slot=MW_GAME_AUDIO_ENGINE_QUEUES;
  for(unsigned i=0;i<MW_GAME_AUDIO_ENGINE_QUEUES;i++)if(q->state[i]==2&&q->serial[i]==q->next_queue){slot=i;break;}
  if(slot==MW_GAME_AUDIO_ENGINE_QUEUES)break;
  ndspWaveBuf*w=q->wave+slot;memset(w,0,sizeof(*w));w->data_vaddr=q->pcm+slot*MW_GAME_AUDIO_ENGINE_FRAMES;w->nsamples=MW_GAME_AUDIO_ENGINE_FRAMES;
  ndspChnWaveBufAdd(1,w);q->state[slot]=3;q->next_queue++;
 }
 LightLock_Unlock(&q->lock);return true;
}
bool mw_game_audio_engine_stream_start(MwGameAudio*a,uint32_t rate,MwGameAudioEngineRender render,void*context){
 if(!a||!a->active||!a->stream.ndsp_ready||a->engine.loaded||a->engine_stream.active||!render||rate<8000||rate>48000)return false;
 MwGameAudioEngineQueue*q=&a->engine_stream;memset(q,0,sizeof(*q));q->pcm=linearAlloc(MW_GAME_AUDIO_ENGINE_QUEUES*MW_GAME_AUDIO_ENGINE_FRAMES*2);
 if(!q->pcm)return false;
 q->render=render;q->context=context;q->active=true;q->paused=a->stream.paused;LightLock_Init(&q->lock);LightEvent_Init(&q->wake,RESET_ONESHOT);
 ndspChnWaveBufClear(1);ndspChnReset(1);ndspChnSetInterp(1,NDSP_INTERP_LINEAR);ndspChnSetRate(1,(float)rate);ndspChnSetFormat(1,NDSP_FORMAT_MONO_PCM16);gain(1,1);
 q->worker=threadCreate(engine_worker,q,16*1024,0x38,-2,false);
 if(!q->worker){linearFree(q->pcm);memset(q,0,sizeof(*q));return false;}
 return true;
}
bool mw_game_audio_engine_stream_input(MwGameAudio*a,float rpm,float load,bool enabled){
 if(!a||!a->active||!a->engine_stream.active||(enabled&&(!isfinite(rpm)||rpm<=0||!isfinite(load)||load<0||load>1)))return false;
 MwGameAudioEngineQueue*q=&a->engine_stream;LightLock_Lock(&q->lock);
 if(q->failed){LightLock_Unlock(&q->lock);return false;}
 if(q->enabled!=enabled){
  q->generation++;q->next_queue=q->next_render=0;
  ndspChnWaveBufClear(1);
  for(unsigned i=0;i<MW_GAME_AUDIO_ENGINE_QUEUES;i++)if(q->state[i]!=1)q->state[i]=0;
 }
 q->enabled=enabled;if(enabled){q->rpm=rpm;q->load=load;}LightLock_Unlock(&q->lock);LightEvent_Signal(&q->wake);return true;
}
void mw_game_audio_engine_stream_stop(MwGameAudio*a){
 if(!a)return;
 MwGameAudioEngineQueue*q=&a->engine_stream;if(!q->active)return;
 LightLock_Lock(&q->lock);q->stop=true;LightLock_Unlock(&q->lock);LightEvent_Signal(&q->wake);
 if(q->worker){threadJoin(q->worker,UINT64_MAX);threadFree(q->worker);}
 if(a->stream.ndsp_ready){ndspChnWaveBufClear(1);ndspChnReset(1);}
 if(q->pcm)linearFree(q->pcm);
 memset(q,0,sizeof(*q));
}
