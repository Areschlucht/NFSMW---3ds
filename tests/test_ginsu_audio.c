#define _POSIX_C_SOURCE 200809L
#include "mw_ginsu_audio.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
int main(int argc,char**argv){
 assert(argc==2);MwGinsuAudio a={0};assert(mw_ginsu_audio_open(&a,argv[1],NULL));assert(a.loaded&&!a.calibrated&&!a.started);
 float grain,ratio;int16_t actual[512],expected[512];assert(!mw_ginsu_audio_frequency(&a,3500,&grain,&ratio));assert(!mw_ginsu_audio_render(&a,actual,512,3500,.75f));
 assert(!mw_ginsu_audio_calibrate(&a,NAN,7784));assert(!mw_ginsu_audio_calibrate(&a,7784,1500));assert(mw_ginsu_audio_calibrate(&a,1500,7784));
 assert(mw_ginsu_audio_frequency(&a,3500,&grain,&ratio)&&grain!=3500&&ratio>0&&ratio<=1);
 MwGinsuState reference;assert(mw_ginsu_start(&reference,&a.bank,grain));
 for(unsigned i=0;i<8;i++){
  float rpm=3500+(float)i*225;assert(mw_ginsu_audio_frequency(&a,rpm,&grain,&ratio));assert(mw_ginsu_frequency(&reference,&a.bank,grain,60));assert(mw_ginsu_render(&reference,&a.bank,expected,512));
  assert(mw_ginsu_audio_render(&a,actual,512,rpm,.75f));assert(!memcmp(actual,expected,sizeof(actual)));assert(!memcmp(&a.synth,&reference,sizeof(reference)));
 }
 assert(a.started&&!a.failed&&!mw_ginsu_audio_calibrate(&a,1500,7784));assert(!mw_ginsu_audio_render(&a,actual,512,0,.75f));assert(!mw_ginsu_audio_render(&a,actual,512,3500,NAN));
 /* Expected-bank identity and source payload CRC reject before publication. */
 unsigned char wrong[32]={0};MwGinsuAudio untouched={0};assert(!mw_ginsu_audio_open(&untouched,argv[1],wrong)&&!untouched.loaded&&!untouched.bytes);
 FILE*f=fopen(argv[1],"rb");assert(f&&!fseek(f,0,SEEK_END));long bytes=ftell(f);rewind(f);unsigned char*p=malloc((size_t)bytes);assert(p&&fread(p,1,(size_t)bytes,f)==(size_t)bytes&&!fclose(f));
 char path[]="/tmp/nfsmw-ginsu-audio.XXXXXX";int fd=mkstemp(path);assert(fd>=0);f=fdopen(fd,"wb");assert(f);p[bytes-1]^=1;assert(fwrite(p,1,(size_t)bytes,f)==(size_t)bytes&&!fclose(f));assert(!mw_ginsu_audio_open(&untouched,path,NULL)&&!untouched.loaded&&!untouched.bytes);free(p);unlink(path);
 mw_ginsu_audio_close(&a);mw_ginsu_audio_close(&a);assert(!a.loaded&&!a.bytes);
 puts("Ginsu audio adapter: source calibration gate, eight full packet-adapter comparisons, immutable startup and selected-bank/payload rejection pass");return 0;
}
