#include "mw_nis.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint32_t word(const unsigned char *p){return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void put(unsigned char *p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(n>>(i*8));}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned b=0;b<8;b++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static bool identity(void *ctx,uint8_t mode,bool target,const float input[3],float output[3]){
    (void)ctx;(void)target;if(mode>3)return false;memcpy(output,input,3*sizeof(float));return true;
}
static bool refuse(void *ctx,uint8_t mode,bool target,const float input[3],float output[3]){
    (void)ctx;(void)mode;(void)target;(void)input;(void)output;return false;
}
static void reject(unsigned char *data,size_t n){
    MwNisPack before={.data=(const void*)1,.bytes=42},out=before;
    assert(!mw_nis_open(&out,data,n));assert(!memcmp(&out,&before,sizeof(out)));
}
int main(int argc,char **argv){
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>128);rewind(f);
    unsigned char *data=malloc((size_t)n),*bad=malloc((size_t)n);assert(data&&bad&&fread(data,1,(size_t)n,f)==(size_t)n);fclose(f);
    MwNisPack p;assert(mw_nis_open(&p,data,(size_t)n));assert(p.scenes==6&&p.tracks==7&&p.keys==86);unsigned samples=0,tracks=0;
    static const char *names[]={"GenericStart","IntroNisDD","IntroNis04","IntroNis05","IntroNis10","EndingNis03"};
    for(unsigned i=0;i<6;i++){
        MwNisScene s,find;assert(mw_nis_scene(&p,i,&s)&&!strcmp(s.name,names[i]));assert(mw_nis_find(&p,names[i],&find)&&find.hash==s.hash);
        for(unsigned t=0;t<s.track_count;t++){
            MwNisTrack track;assert(mw_nis_track(&p,&s,t,&track));tracks++;
            for(unsigned step=0;step<=120;step++){
                MwNisCamera c;float time=track.duration*(float)step/120;
                assert(mw_nis_camera_sample(&p,&track,time,identity,NULL,&c));
                MwNisProviders providers={.prepare=identity,.resolve=identity};MwNisCamera runtime;
                assert(mw_nis_camera_sample_provided(&p,&track,time,&providers,&runtime));
                assert(!memcmp(c.eye,runtime.eye,12)&&!memcmp(c.target,runtime.target,12));
                assert(c.roll_source==runtime.roll_source&&c.fov_turn==runtime.fov_turn);
                for(unsigned a=0;a<3;a++)assert(isfinite(c.eye[a])&&isfinite(c.target[a]));
                assert(c.fov_turn>0&&c.fov_turn<32768&&c.key_index<track.key_count);samples++;
            }
            MwNisCamera last;assert(mw_nis_camera_sample(&p,&track,track.duration+100,identity,NULL,&last)&&last.finished);
            MwNisCamera before={.key_index=99},out=before;
            assert(!mw_nis_camera_sample(&p,&track,0,refuse,NULL,&out)&&!memcmp(&out,&before,sizeof(out)));
            assert(!mw_nis_camera_sample(&p,&track,-1,identity,NULL,&out));
            assert(!mw_nis_camera_sample(&p,&track,NAN,identity,NULL,&out));
        }
    }
    assert(tracks==7);reject(data,0);reject(data,127);reject(data,(size_t)n-1);
    const unsigned offsets[]={0,4,8,12,16,20,24,28,32,36,40,44,112};
    for(unsigned i=0;i<sizeof offsets/sizeof *offsets;i++){
        memcpy(bad,data,(size_t)n);bad[offsets[i]]^=1;reject(bad,(size_t)n);
    }
    const unsigned structural[]={128,128+36,128+40,128+44,512+28,512+32,512+36,512+44};
    for(unsigned i=0;i<sizeof structural/sizeof *structural;i++){
        memcpy(bad,data,(size_t)n);put(bad+structural[i],UINT32_MAX);put(bad+12,crc(bad+16,(size_t)n-16));reject(bad,(size_t)n);
    }
    memcpy(bad,data,(size_t)n);uint32_t at=word(data+36);put(bad+at+16,0x7fc00000);put(bad+12,crc(bad+16,(size_t)n-16));reject(bad,(size_t)n);
    free(data);free(bad);printf("NIS cameras:6 source scenes/7 tracks/86 keys, %u guarded samples and malformed/provider rejection checks pass\n",samples);return 0;
}
