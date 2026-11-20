#include "mw_ginsu_audio.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint32_t word(const unsigned char*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint32_t crc(const unsigned char*p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1));}return ~c;}
void mw_ginsu_audio_close(MwGinsuAudio*a){if(!a)return;free(a->bytes);memset(a,0,sizeof(*a));}
bool mw_ginsu_audio_open(MwGinsuAudio*out,const char*path,const unsigned char expected[32]){
 if(!out||!path||out->loaded)return false;
 FILE*f=fopen(path,"rb");if(!f)return false;
 unsigned char h[96];MwGinsuAudio a={0};long size;
 if(fseek(f,0,SEEK_END)||(size=ftell(f))<96||size>2*1024*1024||fseek(f,0,SEEK_SET)||fread(h,1,96,f)!=96)goto fail;
 uint32_t bytes=word(h+16);
 if(memcmp(h,"NGI1",4)||word(h+4)!=1||word(h+8)!=(uint32_t)size||word(h+12)!=crc(h+16,80)||bytes!=(uint32_t)size-96||(expected&&memcmp(expected,h+32,32)))goto fail;
 unsigned hash=0;for(unsigned i=32;i<64;i++)hash|=h[i];if(!hash)goto fail;
 for(unsigned i=64;i<96;i++)if(h[i])goto fail;
 a.bytes=malloc(bytes);if(!a.bytes||fread(a.bytes,1,bytes,f)!=bytes||crc(a.bytes,bytes)!=word(h+20)||!mw_ginsu_bank_open(&a.bank,a.bytes,bytes)||a.bank.rate!=word(h+24)||a.bank.sample_count!=word(h+28))goto fail;
 fclose(f);a.loaded=true;*out=a;return true;
fail:fclose(f);mw_ginsu_audio_close(&a);return false;
}
bool mw_ginsu_audio_calibrate(MwGinsuAudio*a,float low,float high){
 if(!a||!a->loaded||a->started||!isfinite(low)||!isfinite(high)||low<=0||high<=low)return false;
 a->source_min_rpm=low;a->source_max_rpm=high;a->calibrated=true;return true;
}
bool mw_ginsu_audio_frequency(const MwGinsuAudio*a,float rpm,float*grain,float*ratio){
 if(!a||!a->loaded||!a->calibrated)return false;
 return mw_ginsu_engine_frequency(&a->bank,rpm,a->source_min_rpm,a->source_max_rpm,grain,ratio);
}
bool mw_ginsu_audio_render(void*context,int16_t*out,unsigned frames,float rpm,float load){
 MwGinsuAudio*a=context;
 if(!a||!a->loaded||!a->calibrated||a->failed||!out||!frames||frames>16384||!isfinite(rpm)||rpm<=0||!isfinite(load)||load<0||load>1)return false;
 float grain,ratio;if(!mw_ginsu_audio_frequency(a,rpm,&grain,&ratio))return false;
 bool ok=true;if(!a->started){ok=mw_ginsu_start(&a->synth,&a->bank,grain);a->started=ok;}
 if(ok)ok=mw_ginsu_frequency(&a->synth,&a->bank,grain,60.0f)&&mw_ginsu_render(&a->synth,&a->bank,out,frames);
 if(!ok){a->failed=true;return false;}
 a->last_rpm=rpm;a->last_load=load;return true;
}
