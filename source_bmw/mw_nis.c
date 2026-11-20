#include "mw_nis.h"
#include <math.h>
#include <string.h>
static uint32_t word(const unsigned char *p){return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const unsigned char *p){uint32_t n=word(p);float f;memcpy(&f,&n,4);return f;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned b=0;b<8;b++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static bool text(const unsigned char *p,unsigned bytes){
    bool end=false;
    for(unsigned i=0;i<bytes;i++){
        if(!p[i])end=true;
        else if(end||p[i]<32||p[i]>126)return false;
    }
    return end&&p[0];
}
bool mw_nis_scene(const MwNisPack *p,uint32_t index,MwNisScene *out){
    if(!p||!p->data||!out||index>=p->scenes)return false;
    const unsigned char *r=p->data+p->scene_at+index*64;
    *out=(MwNisScene){.name=(const char*)r,.hash=word(r+32),.first_track=word(r+36),.track_count=word(r+40)};return true;
}
bool mw_nis_find(const MwNisPack *p,const char *name,MwNisScene *out){
    if(!p||!name||!out)return false;
    for(uint32_t i=0;i<p->scenes;i++){MwNisScene s;if(!mw_nis_scene(p,i,&s))return false;if(!strcmp(s.name,name)){*out=s;return true;}}
    return false;
}
bool mw_nis_track(const MwNisPack *p,const MwNisScene *s,uint32_t index,MwNisTrack *out){
    if(!p||!p->data||!s||!out||index>=s->track_count||s->first_track>=p->tracks||index>=p->tracks-s->first_track)return false;
    const unsigned char *r=p->data+p->track_at+(s->first_track+index)*64;
    *out=(MwNisTrack){.name=(const char*)r,.first_key=word(r+28),.key_count=word(r+32),.duration=real(r+36)};return true;
}
bool mw_nis_open(MwNisPack *out,const void *data,size_t bytes){
    if(!out||!data||bytes<128||bytes>4*1024*1024)return false;
    const unsigned char *r=data;
    if(memcmp(r,"NIS1",4)||word(r+4)!=1||word(r+8)!=bytes||word(r+12)!=crc(r+16,bytes-16)||word(r+40)!=212)return false;
    MwNisPack p={.data=r,.bytes=bytes,.scenes=word(r+16),.tracks=word(r+20),.keys=word(r+24),.scene_at=word(r+28),.track_at=word(r+32),.key_at=word(r+36)};
    if(!p.scenes||p.scenes>64||!p.tracks||p.tracks>128||!p.keys||p.keys>8192||p.scene_at!=128||p.track_at!=128+p.scenes*64||p.key_at!=p.track_at+p.tracks*64||bytes!=p.key_at+(uint64_t)p.keys*212)return false;
    for(unsigned i=44;i<48;i++)if(r[i])return false;
    for(unsigned i=112;i<128;i++)if(r[i])return false;
    uint32_t next_track=0,next_key=0;
    for(uint32_t i=0;i<p.scenes;i++){
        const unsigned char *row=r+p.scene_at+i*64;MwNisScene scene;mw_nis_scene(&p,i,&scene);
        if(!text(row,32)||!scene.hash||scene.first_track!=next_track||!scene.track_count||scene.track_count>p.tracks-next_track)return false;
        for(unsigned b=44;b<64;b++)if(row[b])return false;
        for(uint32_t j=0;j<i;j++){MwNisScene before;mw_nis_scene(&p,j,&before);if(before.hash==scene.hash||!strcmp(before.name,scene.name))return false;}
        for(uint32_t j=0;j<scene.track_count;j++){
            const unsigned char *tr=r+p.track_at+(next_track+j)*64;MwNisTrack t;mw_nis_track(&p,&scene,j,&t);
            if(!text(tr,24)||word(tr+24)!=i||t.first_key!=next_key||!t.key_count||t.key_count>p.keys-next_key||!isfinite(t.duration)||t.duration<=0||t.duration>600)return false;
            for(unsigned b=44;b<64;b++)if(tr[b])return false;
            float previous=-1;
            for(uint32_t k=0;k<t.key_count;k++){
                const unsigned char *key=r+p.key_at+(next_key+k)*212;float time=real(key+16);
                if(!isfinite(time)||time<=previous||time<0||time>=1||key[4]>3||key[5]>3)return false;
                previous=time;
                for(unsigned b=12;b<124;b+=4)if(!isfinite(real(key+b)))return false;
                for(unsigned b=132;b<212;b+=4)if(!isfinite(real(key+b)))return false;
                if(real(key+196)<=0||real(key+196)>=32768||real(key+200)<=0||real(key+200)>=32768)return false;
            }
            next_key+=t.key_count;
        }
        next_track+=scene.track_count;
    }
    if(next_key!=p.keys||next_track!=p.tracks)return false;
    *out=p;return true;
}
static float cubic(float a,float da,float b,float db,float t){
    float difference=b-a,twice=difference+difference,double_rate=da+da;
    float c0=da+db;c0=c0-twice;
    float c1=fmaf(difference,3,-db);c1=c1-double_rate;
    return fmaf(fmaf(fmaf(c0,t,c1),t,da),t,a);
}
static const unsigned char *key_at(const MwNisPack *p,const MwNisTrack *t,uint32_t index){return p->data+p->key_at+(t->first_key+index)*212;}
static float key_duration(const MwNisPack *p,const MwNisTrack *t,uint32_t index){
    return (index+1<t->key_count?real(key_at(p,t,index+1)+16):1)-real(key_at(p,t,index)+16);
}
static bool continuous(const unsigned char *a,unsigned end,const unsigned char *b){
    unsigned other=end^1u;
    if(a[0]!=b[0]||a[4]!=b[4]||a[5]!=b[5])return false;
    const unsigned scalar[]={20,76,84};
    for(unsigned i=0;i<3;i++)if(fabsf(real(a+scalar[i]+end*4)-real(b+scalar[i]+other*4))>.0010000000474974513f)return false;
    for(unsigned i=0;i<3;i++){
        if(fabsf(real(a+28+end*12+i*4)-real(b+28+other*12+i*4))>.0010000000474974513f)return false;
        if(fabsf(real(a+52+end*12+i*4)-real(b+52+other*12+i*4))>.0010000000474974513f)return false;
    }
    return true;
}
static bool point(const unsigned char *r,unsigned end,bool target,const MwNisProviders *providers,float out[3]){
    float raw[3];unsigned at=(target?52u:28u)+end*12;
    for(unsigned i=0;i<3;i++)raw[i]=real(r+at+i*4);
    if(!providers->prepare)return false;
    if(!providers->prepare(providers->context,r[target?5:4],target,raw,out))return false;
    return isfinite(out[0])&&isfinite(out[1])&&isfinite(out[2]);
}
static bool tangent(const MwNisPack *p,const MwNisTrack *t,uint32_t index,unsigned end,bool target,const MwNisProviders *providers,float out[3]){
    const unsigned char *r=key_at(p,t,index);memset(out,0,3*sizeof(float));if(!r[0])return true;
    float begin[3],finish[3];if(!point(r,0,target,providers,begin)||!point(r,1,target,providers,finish))return false;
    float weight=real(r+20+end*4);bool adjacent=end?index+1<t->key_count:index>0;
    uint32_t other=end?index+1:index-1;
    const unsigned char *neighbor=adjacent?key_at(p,t,other):NULL;
    if(neighbor&&neighbor[0]&&continuous(r,end,neighbor)){
        float previous[3],next[3];if(!point(neighbor,0,target,providers,previous)||!point(neighbor,1,target,providers,next))return false;
        float duration=key_duration(p,t,index),neighbor_duration=key_duration(p,t,other);
        float ratio=duration/(duration+neighbor_duration),complement=1-ratio;
        if(neighbor_duration>0.0000009999999974752427f)ratio=ratio*(duration/neighbor_duration);
        ratio=ratio*weight;complement=complement*weight;
        for(unsigned i=0;i<3;i++){float a=(next[i]-previous[i])*ratio;out[i]=fmaf(finish[i]-begin[i],complement,a);}
    }else for(unsigned i=0;i<3;i++)out[i]=(finish[i]-begin[i])*weight;
    return true;
}
static bool sample(const MwNisPack *p,const MwNisTrack *t,float seconds,bool normalized,MwNisResolve resolve,void *context,const MwNisProviders *providers,MwNisCamera *out){
    if(!p||!p->data||!t||!out||!resolve||!isfinite(seconds)||seconds<0||!isfinite(t->duration)||t->duration<=0||!t->key_count||t->first_key>=p->keys||t->key_count>p->keys-t->first_key)return false;
    float time=normalized?seconds:seconds/t->duration;if(time>1)time=1;
    uint32_t index=0;
    for(uint32_t i=1;i<t->key_count;i++)if(real(p->data+p->key_at+(t->first_key+i)*212+16)<=time)index=i;else break;
    const unsigned char *r=p->data+p->key_at+(t->first_key+index)*212;
    float first=real(r+16),last=index+1<t->key_count?real(r+212+16):1;
    if(!(last>first))return false;
    float u=(time-first)/(last-first);if(u<0)u=0;if(u>1)u=1;
    float eye[3],target[3];MwNisCamera sample={.key_index=index,.eye_mode=r[4],.target_mode=r[5],.finished=normalized?seconds>=1:seconds>=t->duration};
    memcpy(sample.flags,r,4);
    memcpy(sample.reference_flags,r+8,4);
    if(providers){
        float ends[2][3],derivatives[2][3];
        for(unsigned target_kind=0;target_kind<2;target_kind++){
            for(unsigned end=0;end<2;end++)if(!point(r,end,target_kind!=0,providers,ends[end])||!tangent(p,t,index,end,target_kind!=0,providers,derivatives[end]))return false;
            for(unsigned a=0;a<3;a++)(target_kind?target:eye)[a]=r[2+target_kind]?cubic(ends[0][a],derivatives[0][a],ends[1][a],derivatives[1][a],u):fmaf(ends[1][a],u,ends[0][a]*(1-u));
        }
    }else for(unsigned a=0;a<3;a++){
        eye[a]=r[2]?cubic(real(r+28+a*4),real(r+132+a*4),real(r+40+a*4),real(r+164+a*4),u):fmaf(real(r+40+a*4),u,real(r+28+a*4)*(1-u));
        target[a]=r[3]?cubic(real(r+52+a*4),real(r+144+a*4),real(r+64+a*4),real(r+176+a*4),u):fmaf(real(r+64+a*4),u,real(r+52+a*4)*(1-u));
    }
    sample.roll_source=r[2]?cubic(real(r+76),real(r+156),real(r+80),real(r+188),u):fmaf(real(r+76),1-u,real(r+80)*u);
    sample.fov_turn=r[2]?cubic(real(r+196),real(r+204),real(r+200),real(r+208),u):fmaf(real(r+196),1-u,real(r+200)*u);
    if(!resolve(context,sample.eye_mode,false,eye,sample.eye)||!resolve(context,sample.target_mode,true,target,sample.target))return false;
    for(unsigned a=0;a<3;a++)if(!isfinite(sample.eye[a])||!isfinite(sample.target[a]))return false;
    if(!isfinite(sample.roll_source)||!isfinite(sample.fov_turn)||sample.fov_turn<=0||sample.fov_turn>=32768)return false;
    *out=sample;return true;
}
bool mw_nis_camera_sample(const MwNisPack *p,const MwNisTrack *t,float seconds,MwNisResolve resolve,void *context,MwNisCamera *out){
    return sample(p,t,seconds,false,resolve,context,NULL,out);
}
bool mw_nis_camera_sample_provided(const MwNisPack *p,const MwNisTrack *t,float seconds,const MwNisProviders *providers,MwNisCamera *out){
    if(!providers||!providers->prepare||!providers->resolve)return false;
    return sample(p,t,seconds,false,providers->resolve,providers->context,providers,out);
}
bool mw_nis_camera_parameter_provided(const MwNisPack *p,const MwNisTrack *t,float parameter,const MwNisProviders *providers,MwNisCamera *out){
    if(!providers||!providers->prepare||!providers->resolve)return false;
    return sample(p,t,parameter,true,providers->resolve,providers->context,providers,out);
}
