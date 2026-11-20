#include "mw_audio_stream.h"
#include <limits.h>
#include <math.h>
#include <string.h>
static uint32_t word(const unsigned char*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint32_t crc(const unsigned char*p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1));}return ~c;}
bool mw_audio_stream_open(MwMovie*out,MwAudioStreamInfo*info,const char*path){
 if(!out||!info||!path)return false;
 MwMovie m={0};MwAudioStreamInfo v={0};unsigned char h[128],scratch[1024];
 m.audio=fopen(path,"rb");if(!m.audio)return false;
 if(fseek(m.audio,0,SEEK_END))goto fail;
 long size=ftell(m.audio);if(size<128||size>INT32_MAX||fseek(m.audio,0,SEEK_SET)||fread(h,1,128,m.audio)!=128)goto fail;
 uint32_t rate=word(h+16),channels=word(h+20),frames=word(h+24),blocks=word(h+32),at=word(h+40),flags=word(h+52);
 if(memcmp(h,"NAG1",4)||word(h+4)!=1||word(h+8)!=(uint32_t)size||word(h+12)!=crc(h+16,112)||
    rate<8000||rate>48000||channels!=2||!frames||frames>0x10000000u||word(h+28)!=4096||blocks!=(frames+4095)/4096||blocks>65536||word(h+36)!=128||at!=(128+blocks*4+31u)/32*32||
    (uint64_t)at+(uint64_t)frames*4!=(uint32_t)size||flags>3||(flags&2u&&!(flags&1u)))goto fail;
 v.original_channels=word(h+60);v.loop_start=word(h+44);v.loop_end=word(h+48);v.flags=flags;memcpy(&v.reference_rpm,h+56,4);
 if((v.original_channels!=1&&v.original_channels!=2)||!isfinite(v.reference_rpm)||v.reference_rpm<0||v.reference_rpm>30000)goto fail;
 if(flags&1u){if(v.loop_start>=v.loop_end||v.loop_end>frames)goto fail;}else if(v.loop_start||v.loop_end)goto fail;
 unsigned source=0;for(unsigned i=64;i<96;i++)source|=h[i];if(!source)goto fail;
 /* Index CRC protects every expected payload CRC before a worker sees it. */
 uint32_t running=~0u;size_t left=blocks*4;
 while(left){size_t n=left<sizeof(scratch)?left:sizeof(scratch);if(fread(scratch,1,n,m.audio)!=n)goto fail;for(size_t i=0;i<n;i++){running^=scratch[i];for(unsigned b=0;b<8;b++)running=(running>>1)^(0xedb88320u&-(running&1));}left-=n;}
 if(~running!=word(h+96))goto fail;
 for(uint32_t i=128+blocks*4;i<at;i++)if(fgetc(m.audio)!=0)goto fail;
 for(unsigned i=100;i<128;i++)if(h[i])goto fail;
 m.total_bytes=(uint32_t)size;m.audio_crc_at=128;m.audio_blocks=blocks;m.audio_at=at;m.audio_frames=frames;m.sample_rate=rate;memcpy(m.source_sha256,h+64,32);
 *out=m;*info=v;return true;
fail:mw_movie_close(&m);return false;
}
