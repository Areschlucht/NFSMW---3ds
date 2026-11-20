#include "mw_audio_stream.h"
#include <assert.h>
#include <stdio.h>
#include <stdint.h>
int main(int argc,char**argv){
 assert(argc>1);unsigned char pcm[MW_MOVIE_AUDIO_BLOCK_BYTES];uint64_t total=0;unsigned blocks=0;
 for(int i=1;i<argc;i++){
  MwMovie m={0};MwAudioStreamInfo info;assert(mw_audio_stream_open(&m,&info,argv[i]));uint64_t count=0;
  for(uint32_t b=0;b<m.audio_blocks;b++){uint32_t frames=0;assert(mw_movie_audio_block(&m,b,pcm,sizeof(pcm),&frames));assert(frames&&frames<=4096);count+=frames;blocks++;}
  assert(count==m.audio_frames);total+=count;mw_movie_close(&m);
 }
 printf("Native audio: %d streams, %u CRC-verified blocks, %llu exact PCM frames pass\n",argc-1,blocks,(unsigned long long)total);return 0;
}
