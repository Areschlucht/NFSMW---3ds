#include "mw_ginsu.h"
#include "mw_ginsu_bindings.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void *read_file(const char*path,size_t*bytes){FILE*f=fopen(path,"rb");assert(f&&!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>32);rewind(f);void*p=malloc((size_t)n);assert(p&&fread(p,1,(size_t)n,f)==(size_t)n&&!fclose(f));*bytes=(size_t)n;return p;}
static uint32_t crc(const unsigned char*p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void put(unsigned char*p,uint32_t u){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(u>>(i*8));}
int main(int argc,char**argv){
 assert(argc==3);size_t bytes,bind_bytes;unsigned char*raw=read_file(argv[1],&bytes),*binding=read_file(argv[2],&bind_bytes);
 MwGinsuBank b={0};assert(mw_ginsu_bank_open(&b,raw,bytes));assert(b.rate==24000&&b.sample_count==162173&&b.cycles==235&&b.segments==50);
 assert(b.min_frequency==1239.5f&&b.max_frequency==7784.10009765625f);
 MwGinsuBank saved=b;raw[0]^=1;assert(!mw_ginsu_bank_open(&b,raw,bytes)&&!memcmp(&b,&saved,sizeof(b)));raw[0]^=1;assert(!mw_ginsu_bank_open(&b,raw,bytes-1));
 MwGinsuBindings bindings={0};assert(mw_ginsu_bindings_open(&bindings,binding,bind_bytes));assert(bindings.count==103);
 MwGinsuBinding v;assert(mw_ginsu_binding_profile(&bindings,"m3gtre46careerstart","BMWM3GTRE46",&v));assert(!strcmp(v.engineaudio,"tvr_cerb")&&!strcmp(v.accel,"b2a1056e.ngi")&&(v.flags&5)==5);
 MwGinsuBinding guard=v;assert(!mw_ginsu_binding_profile(&bindings,"m3gtre46careerstart","GTI",&v)&&!memcmp(&guard,&v,sizeof(v)));assert(!mw_ginsu_binding_profile(&bindings,"unknown",NULL,&v));
 for(uint32_t i=0;i<bindings.count;i++){assert(mw_ginsu_binding_get(&bindings,i,&v));assert(*v.profile&&v.physical_key&&v.engineaudio_key);}
 assert(!mw_ginsu_binding_get(&bindings,bindings.count,&v));
 unsigned char*bad=malloc(bind_bytes);assert(bad);
 for(size_t i=0;i<bind_bytes;i+=17){memcpy(bad,binding,bind_bytes);bad[i]^=1;MwGinsuBindings before=bindings;assert(!mw_ginsu_bindings_open(&bindings,bad,bind_bytes)&&!memcmp(&bindings,&before,sizeof(before)));}
 memcpy(bad,binding,bind_bytes);bad[64]^=1;put(bad+12,crc(bad+16,bind_bytes-16));assert(!mw_ginsu_bindings_open(&bindings,bad,bind_bytes));free(bad);
 MwGinsuState a={0},z={0};assert(mw_ginsu_start(&a,&b,b.min_frequency));assert(a.playback==360&&a.packet_size==264&&a.overlap_size==12&&a.no_jump_remaining==264&&a.countdown==1);
 assert(mw_ginsu_start(&z,&b,b.min_frequency));assert(mw_ginsu_frequency(&a,&b,4000,60)&&a.countdown==6);assert(mw_ginsu_frequency(&z,&b,4000,60));
 int16_t whole[8192],chunked[8192];assert(mw_ginsu_render(&a,&b,whole,8192));uint32_t at=0;
 while(at<8192){uint32_t n=1+(at*17u+31u)%731u;if(n>8192-at)n=8192-at;assert(mw_ginsu_render(&z,&b,chunked+at,n));at+=n;}
 assert(!memcmp(whole,chunked,sizeof(whole)));assert(a.playback==z.playback&&a.current==z.current&&a.current_cycle==z.current_cycle&&a.cursor==z.cursor&&a.available==z.available);
 bool sounded=false;for(unsigned i=0;i<8192;i++)sounded|=whole[i]!=0;assert(sounded);
 assert(mw_ginsu_start(&a,&b,b.min_frequency));assert(mw_ginsu_start(&z,&b,b.min_frequency));int16_t packet[1024];assert(mw_ginsu_packet(&a,&b,packet,1024));assert(mw_ginsu_packet(&z,&b,z.packet,1024));assert(!memcmp(packet,z.packet,a.packet_size*2));
 int16_t refused[1024];memset(refused,0x65,sizeof(refused));a.playback=(int32_t)b.sample_count-1;MwGinsuState previous=a;assert(!mw_ginsu_packet(&a,&b,refused,1024)&&!memcmp(&a,&previous,sizeof(a)));for(unsigned i=0;i<1024;i++)assert(refused[i]==0x6565);
 float frequency=123,pitch=456;assert(!mw_ginsu_engine_frequency(&b,NAN,1000,8000,&frequency,&pitch)&&frequency==123&&pitch==456);assert(!mw_ginsu_engine_frequency(&b,1000,0,8000,&frequency,&pitch));
 assert(mw_ginsu_engine_frequency(&b,-1000,1000,8000,&frequency,&pitch)&&frequency==b.min_frequency&&pitch==1000.f/b.min_frequency);
 assert(mw_ginsu_engine_frequency(&b,10000,1000,8000,&frequency,&pitch)&&frequency==8000&&pitch==1);
 free(raw);free(binding);puts("Ginsu: exact BMW source bank, authoritative103profile bindings, arbitrary queue sizes, in-place packet tail, rollback and malformed-source gates pass.");return 0;
}
