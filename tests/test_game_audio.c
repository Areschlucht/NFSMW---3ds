#define _POSIX_C_SOURCE 200809L
#include "mw_game_audio.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static unsigned char *read_file(const char*path,size_t*bytes){FILE*f=fopen(path,"rb");assert(f&&!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0);rewind(f);unsigned char*p=malloc((size_t)n);assert(p&&fread(p,1,(size_t)n,f)==(size_t)n&&!fclose(f));*bytes=(size_t)n;return p;}
static void issue(MwGameAudio*a){for(unsigned i=0;i<5000;i++){assert(mw_game_audio_update(a));if(mw_game_audio_issued(a))return;mock_movie_audio_yield();}assert(!"No CRC-verified PCM submission");}
typedef struct {int16_t pcm[512];atomic_uint calls;unsigned fail_after;} EngineContext;
static bool engine_render(void*context,int16_t*out,unsigned frames,float rpm,float load){EngineContext*c=context;assert(frames==512&&rpm==3500&&load==.75f);unsigned n=atomic_fetch_add(&c->calls,1)+1;if(c->fail_after&&n>=c->fail_after)return false;memcpy(out,c->pcm,frames*2);return true;}
int main(int argc,char**argv){
 assert(argc==4);MwMovie m={0};MwAudioStreamInfo info;
 assert(mw_audio_stream_open(&m,&info,argv[1]));assert(m.audio_frames==720384&&m.sample_rate==24000&&info.original_channels==2&&!info.flags);mw_movie_close(&m);
 MwGameAudio a={0};mock_movie_audio_time(0);assert(mw_game_audio_start(&a,argv[1]));assert(mock_game_audio_owners()==1&&!mw_game_audio_issued(&a));assert(!mw_game_audio_start(&a,argv[1]));issue(&a);
 assert(mw_game_audio_load_effect(&a,0,argv[2]));assert(!mw_game_audio_load_effect(&a,MW_GAME_AUDIO_EFFECTS,argv[2]));assert(!mw_game_audio_load_engine(&a,argv[2]));
 assert(mw_game_audio_effect(&a,0,.5f)&&mock_game_audio_queued(2)==1);assert(!mw_game_audio_load_effect(&a,0,argv[2]));
 assert(!mw_game_audio_effect(&a,0,NAN)&&!mw_game_audio_effect(&a,0,1.1f));
 assert(mw_game_audio_load_loop(&a,1,argv[3]));assert(mw_game_audio_effect(&a,1,.25f));mock_game_audio_advance(3,4096);assert(mock_game_audio_queued(3)==1);mw_game_audio_stop_effect(&a,1);assert(!mock_game_audio_queued(3));
 assert(mw_game_audio_load_loop(&a,5,argv[3])&&mw_game_audio_effect(&a,5,.5f));assert(mock_game_audio_queued(7)==1);mw_game_audio_stop_effect(&a,5);assert(!mock_game_audio_queued(7));
 assert(mw_game_audio_load_loop(&a,6,argv[3])&&mw_game_audio_effect(&a,6,.5f));assert(mock_game_audio_queued(8)==1);mw_game_audio_stop_effect(&a,6);assert(!mock_game_audio_queued(8));
 assert(mw_game_audio_load_effect(&a,7,argv[2])&&mw_game_audio_effect(&a,7,.5f));assert(mock_game_audio_queued(9)==1);mw_game_audio_stop_effect(&a,7);assert(!mock_game_audio_queued(9));
 assert(mw_game_audio_load_engine(&a,argv[3]));assert(!mw_game_audio_engine(&a,NAN,.5f,true));assert(mw_game_audio_engine(&a,3000,.7f,true));assert(mock_game_audio_queued(1)==1&&mock_game_audio_rate(1)==(float)a.engine.rate*2);
 mw_game_audio_pause(&a,true);assert(!mw_game_audio_effect(&a,0,.5f));uint64_t played=mw_movie_audio_played_samples(&a.stream);mock_movie_audio_advance(4096);assert(mw_movie_audio_played_samples(&a.stream)==played);mock_game_audio_advance(2,4096);assert(mock_game_audio_queued(2)==1);
 mw_game_audio_pause(&a,false);mock_game_audio_advance(2,0x100000);assert(!mock_game_audio_queued(2));assert(mw_game_audio_effect(&a,0,1));assert(mw_game_audio_engine(&a,0,0,false)&&!mock_game_audio_queued(1));
 for(unsigned i=0;i<5000&&!mw_game_audio_finished(&a);i++){mock_movie_audio_advance(4096);assert(mw_game_audio_update(&a));mock_movie_audio_yield();}assert(mw_game_audio_finished(&a)&&mw_movie_audio_played_samples(&a.stream)==720384);
 mw_game_audio_stop(&a);assert(!mock_game_audio_owners());for(unsigned i=0;i<2+MW_GAME_AUDIO_EFFECTS;i++)assert(!mock_game_audio_queued(i));mw_game_audio_stop(&a);
 EngineContext engine={0};atomic_init(&engine.calls,0);MwMovie clip={0};assert(mw_audio_stream_open(&clip,&info,argv[2]));int16_t stereo[8192];uint32_t samples;assert(mw_movie_audio_block(&clip,0,stereo,sizeof(stereo),&samples)&&samples>=512);for(unsigned i=0;i<512;i++)engine.pcm[i]=stereo[i*2];mw_movie_close(&clip);
 assert(mw_game_audio_start(&a,argv[1]));assert(mw_game_audio_engine_stream_start(&a,24000,engine_render,&engine));assert(mw_game_audio_engine_stream_rate(&a,.5f)&&mock_game_audio_rate(1)==12000);assert(!mw_game_audio_engine_stream_rate(&a,NAN));assert(!mw_game_audio_engine_stream_rate(&a,0));assert(!mw_game_audio_engine_stream_input(&a,NAN,.75f,true));assert(mw_game_audio_engine_stream_input(&a,3500,.75f,true));
 for(unsigned i=0;i<5000&&!mock_game_audio_queued(1);i++){assert(mw_game_audio_update(&a));mock_movie_audio_yield();}assert(mock_game_audio_queued(1)&&mock_game_audio_queued(1)<=3);assert(!mw_game_audio_load_engine(&a,argv[3]));
 mw_game_audio_pause(&a,true);u32 pos=ndspChnGetSamplePos(1);mock_game_audio_advance(1,1024);assert(ndspChnGetSamplePos(1)==pos);mw_game_audio_pause(&a,false);
 assert(mw_game_audio_engine_stream_input(&a,0,0,false)&&!mock_game_audio_queued(1));mw_game_audio_engine_stream_stop(&a);assert(!a.engine_stream.active&&!a.engine_stream.pcm);unsigned calls=atomic_load(&engine.calls);assert(calls>0&&calls<=3);
 atomic_store(&engine.calls,0);engine.fail_after=1;assert(mw_game_audio_engine_stream_start(&a,24000,engine_render,&engine));assert(mw_game_audio_engine_stream_input(&a,3500,.75f,true));bool synth_failed=false;for(unsigned i=0;i<5000;i++){if(!mw_game_audio_update(&a)){synth_failed=true;break;}mock_movie_audio_yield();}assert(synth_failed&&!mock_game_audio_queued(1));mw_game_audio_stop(&a);assert(!mock_game_audio_owners());
 mock_movie_audio_fail_init(true);assert(mw_game_audio_start(&a,argv[1])&&mw_game_audio_muted(&a)&&!mw_game_audio_issued(&a)&&!mock_game_audio_owners());assert(!mw_game_audio_load_effect(&a,0,argv[2]));assert(!mw_game_audio_effect(&a,0,1));mw_game_audio_stop(&a);mock_movie_audio_fail_init(false);
 /* Header failure leaves caller unchanged. Payload failure never queues sound. */
 size_t n;unsigned char*p=read_file(argv[1],&n);char tmp[]="/tmp/nfsmw-game-audio.XXXXXX";int fd=mkstemp(tmp);assert(fd>=0);FILE*f=fdopen(fd,"wb");assert(f);p[n-1]^=1;assert(fwrite(p,1,n,f)==n&&!fclose(f));
 assert(mw_game_audio_start(&a,tmp));bool failed=false;for(unsigned i=0;i<10000;i++){mock_movie_audio_advance(4096);if(!mw_game_audio_update(&a)){failed=true;break;}mock_movie_audio_yield();}assert(failed&&a.stream.failed);mw_game_audio_stop(&a);assert(!mock_game_audio_owners());
 p[4]^=1;f=fopen(tmp,"wb");assert(f&&fwrite(p,1,n,f)==n&&!fclose(f));m.audio_frames=123;assert(!mw_audio_stream_open(&m,&info,tmp)&&m.audio_frames==123&&!m.audio);unlink(tmp);free(p);
 puts("Game audio: real source music EOF, cached effects/engine calibration gates, pause, ownership release, muted status and CRC rejection pass");return 0;
}
