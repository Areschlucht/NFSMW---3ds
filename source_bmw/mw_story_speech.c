#include "mw_story_speech.h"
#include <limits.h>
#include <string.h>
static uint32_t word(const unsigned char*p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint32_t crc(const unsigned char*p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1));}return ~c;}
bool mw_story_speech_open(MwMovie*out,const char*path,int sms_id){
 static const unsigned char source[32]={0xa1,0x1b,0xf1,0x44,0x13,0xe8,0xd8,0xaa,0x35,0x60,0xdf,0x81,0xf0,0x93,0x2b,0xe0,0x90,0xe4,0x23,0x75,0x23,0xf0,0x30,0xa9,0x4b,0x7f,0x2e,0x55,0xc8,0x60,0x81,0x0a};
 if(!out||!path||sms_id!=10)return false;
 MwMovie m={0};unsigned char h[96],table[244];m.audio=fopen(path,"rb");if(!m.audio)return false;
 if(fseek(m.audio,0,SEEK_END))goto fail;
 long size=ftell(m.audio);
 if(size<96||size>INT32_MAX||fseek(m.audio,0,SEEK_SET)||fread(h,1,96,m.audio)!=96)goto fail;
 if(memcmp(h,"NVS1",4)||word(h+4)!=1||word(h+8)!=(uint32_t)size||word(h+12)!=crc(h+16,80)||
 word(h+16)!=10||word(h+20)!=22050||word(h+24)!=245803||word(h+28)!=2||word(h+32)!=4096||word(h+36)!=61||
 word(h+40)!=96||word(h+44)!=352||memcmp(h+48,source,32)||word(h+84)!=65536||word(h+88)!=1||word(h+92)||
 (uint64_t)word(h+44)+(uint64_t)word(h+24)*4!=(uint32_t)size)goto fail;
 if(fread(table,1,sizeof(table),m.audio)!=sizeof(table)||word(h+80)!=crc(table,sizeof(table)))goto fail;
 /* Bounded alignment padding is required to be zero. */
 for(unsigned i=340;i<352;i++)if(fgetc(m.audio)!=0)goto fail;
 m.total_bytes=(uint32_t)size;m.audio_crc_at=96;m.audio_blocks=61;m.audio_at=352;m.audio_frames=245803;m.sample_rate=22050;
 memcpy(m.source_sha256,h+48,32);*out=m;return true;
fail:mw_movie_close(&m);return false;
}
