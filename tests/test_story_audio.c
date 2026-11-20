#define _POSIX_C_SOURCE 200809L
#include "mw_story_audio.h"
#include "mw_story_speech.h"
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static uint32_t crc(const unsigned char*p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1));}return ~c;}
static void header_crc(unsigned char*p){uint32_t c=crc(p+16,80);for(unsigned i=0;i<4;i++)p[12+i]=(unsigned char)(c>>(i*8));}
static void await_issue(MwStoryAudio*a){for(unsigned i=0;i<4000;i++){assert(mw_story_audio_update(a));if(mw_story_audio_issued_playback(a))return;mock_movie_audio_yield();}assert(!"speech never queued");}
int main(int argc,char**argv){
 assert(argc==3);MwMovie m={0};assert(!mw_story_speech_open(&m,argv[1],11));assert(!m.audio);
 assert(mw_story_speech_open(&m,argv[1],10));assert(!m.video&&!m.frames&&m.audio_frames==245803&&m.sample_rate==22050);
 FILE*mono=fopen(argv[2],"rb");assert(mono);unsigned char scratch[16384],src[8192];uint32_t total=0;
 for(uint32_t i=0;i<m.audio_blocks;i++){uint32_t frames=0;assert(mw_movie_audio_block(&m,i,scratch,sizeof(scratch),&frames));assert(fread(src,2,frames,mono)==frames);for(uint32_t j=0;j<frames;j++)assert(!memcmp(scratch+j*4,src+j*2,2)&&!memcmp(scratch+j*4+2,src+j*2,2));total+=frames;}
 assert(total==245803&&fgetc(mono)==EOF);fclose(mono);
 MwStoryAudio a={0};mock_movie_audio_time(1000);mock_movie_audio_fail_init(false);
 assert(mw_story_audio_start(&a,argv[1],10));assert(!mw_story_audio_issued_playback(&a)&&!mw_story_audio_muted(&a));assert(!mw_story_audio_start(&a,argv[1],10));await_issue(&a);
 mock_movie_audio_advance(512);uint64_t played=mw_movie_audio_played_samples(&a.queue);assert(played==512);
 mw_story_audio_pause(&a,true);mock_movie_audio_advance(22050);assert(mw_movie_audio_played_samples(&a.queue)==played);mw_story_audio_pause(&a,false);
 for(unsigned i=0;i<8000&&!mw_story_audio_finished(&a);i++){mock_movie_audio_advance(512);assert(mw_story_audio_update(&a));mock_movie_audio_yield();}
 assert(mw_story_audio_finished(&a)&&mw_movie_audio_played_samples(&a.queue)==245803);mw_story_audio_stop(&a);mw_story_audio_stop(&a);assert(!a.active&&!a.speech.audio);
 mock_movie_audio_fail_init(true);assert(mw_story_audio_start(&a,argv[1],10)&&mw_story_audio_muted(&a));assert(!mw_story_audio_issued_playback(&a));mock_movie_audio_advance(22050);assert(mw_story_audio_update(&a)&&!mw_story_audio_issued_playback(&a));mw_story_audio_stop(&a);mock_movie_audio_fail_init(false);
 FILE*f=fopen(argv[1],"rb");assert(f);unsigned char*raw=malloc(m.total_bytes);assert(raw&&fread(raw,1,m.total_bytes,f)==m.total_bytes);fclose(f);
 char path[]="/tmp/nfsmw-story-audio.XXXXXX";int fd=mkstemp(path);assert(fd>=0);f=fdopen(fd,"wb");assert(f);
 raw[m.audio_at+20]^=1;assert(fwrite(raw,1,m.total_bytes,f)==m.total_bytes&&!fclose(f));
 assert(mw_story_audio_start(&a,path,10));bool failed=false;for(unsigned i=0;i<4000;i++){if(!mw_story_audio_update(&a)){failed=true;break;}mock_movie_audio_yield();}assert(failed&&!mw_story_audio_issued_playback(&a)&&!mock_movie_audio_queued());mw_story_audio_stop(&a);
 /* A malformed header fails transactionally without publishing a FILE. */
 raw[24]^=1;f=fopen(path,"wb");assert(f&&fwrite(raw,1,m.total_bytes,f)==m.total_bytes&&!fclose(f));MwMovie untouched={0};untouched.frames=123;assert(!mw_story_speech_open(&untouched,path,10)&&untouched.frames==123&&!untouched.audio);
 raw[24]^=1;
 /* Recomputed header CRC must not bypass source identity or exact frame bound. */
 for(unsigned which=0;which<2;which++){
  unsigned byte=which?48:24;raw[byte]^=1;header_crc(raw);
  f=fopen(path,"wb");assert(f&&fwrite(raw,1,m.total_bytes,f)==m.total_bytes&&!fclose(f));
  assert(!mw_story_speech_open(&untouched,path,10)&&untouched.frames==123&&!untouched.audio);
  raw[byte]^=1;
 }
 free(raw);mw_movie_close(&m);unlink(path);puts("Original speech: all stereo samples retain mono provenance; bounded queue, pause, finish, muted policy and corruption failures pass.");return 0;
}
