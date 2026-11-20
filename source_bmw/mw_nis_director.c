#include "mw_nis_director.h"
#include "mw_gekko_math.h"
#include <math.h>
#include <string.h>
static float real(const unsigned char *p){uint32_t u=(uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;float f;memcpy(&f,&u,4);return f;}
static bool finite_array(const float *v,unsigned n){for(unsigned i=0;i<n;i++)if(!isfinite(v[i]))return false;return true;}
bool mw_nis_director_transform(const float m[16],const float in[3],float out[3]){
    if(!m||!in||!out||!finite_array(m,16)||!finite_array(in,3))return false;
    float result[3];for(unsigned a=0;a<3;a++){float v=in[0]*m[a];v=fmaf(in[1],m[4+a],v);v=fmaf(in[2],m[8+a],v);result[a]=v+m[12+a];}
    if(!finite_array(result,3))return false;
    memcpy(out,result,sizeof(result));return true;
}
/* Original eSin polynomial8010B0FC. Its coefficients/range folds differ from
 * the renderer LOD sine; do not substitute that function or system-libm sine. */
static float source_sin(float x){
    float sign=1.0f;
    while(x>6.283185482025146484375f)x=x-6.283185482025146484375f;
    while(x<0)x=x+6.283185482025146484375f;
    if(x>=3.1415927410125732421875f){x=x-3.1415927410125732421875f;sign=-1.0f;}
    if(x>=1.57079637050628662109375f)x=3.1415927410125732421875f-x;
    float x2=x*x,x3=x*x2,x5=x3*x2;
    float v=fmaf(x3,-0.16666656732559204f,x);
    float x7=x5*x2;v=fmaf(x5,0.008333025500178337f,v);
    float x9=x7*x2;v=fmaf(x7,-0.00019807413627859205f,v);
    v=fmaf(x9,2.601886990305502e-6f,v);
    return v*sign;
}
bool mw_nis_director_scene_frame(float out[16],const float origin[3],uint16_t heading,uint32_t scene_type){
    if(!out||!origin||!finite_array(origin,3))return false;
    float m[16]={1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1};
    if(scene_type==0||scene_type==2||scene_type==3){
        uint16_t angle=(uint16_t)(heading-0x4000u);
        float r=(float)angle*9.5873801910784095526e-5f;
        /* Original rotation8010B1D0 cos path computes radians+90deg radians
         * BEFORE sine range reduction; preserve that distinct rounding. */
        float c=source_sin(fmaf(90.0f,0.01745329424738884f,r));
        float s=source_sin(r);m[0]=c;m[1]=s;m[4]=-s;m[5]=c;
        m[12]=origin[0];m[13]=origin[1];m[14]=origin[2];
    }
    memcpy(out,m,sizeof(m));return true;
}
static bool prepare(void *context,uint8_t mode,bool target,const float in[3],float out[3]){
    MwNisDirector *d=context;(void)target;memcpy(out,in,3*sizeof(float));
    if(mode!=3||!d->fix_elevation)return true;
    if(!d->has_scene)return false;
    if((d->world_queries_enabled&&!d->ground)||d->prepared_count>16)return false;
    for(unsigned i=0;i<d->prepared_count;i++)if(!memcmp(d->prepared[i].input,in,12)){memcpy(out,d->prepared[i].output,12);return true;}
    float world[3];if(!mw_nis_director_transform(d->scene,in,world))return false;
    float height=0;
    if(d->world_queries_enabled){
        if(!d->ground)return false;
        if(!d->ground(d->ground_context,world,&height))height=world[2];
    }
    if(!isfinite(height)||!isfinite(d->scene_ground_height))return false;
    if(height>0)out[2]=in[2]+(height-d->scene_ground_height);
    if(!isfinite(out[2]))return false;
    if(d->prepared_count<16){memcpy(d->prepared[d->prepared_count].input,in,12);memcpy(d->prepared[d->prepared_count].output,out,12);d->prepared_count++;}
    return true;
}
static bool resolve(void *context,uint8_t mode,bool target,const float in[3],float out[3]){
    MwNisDirector *d=context;(void)target;
    if(mode==1){memcpy(out,in,3*sizeof(float));return true;}
    if(mode==3)return d->has_scene&&mw_nis_director_transform(d->scene,in,out);
    if(!d->has_subject)return false;
    if(mode==2){for(unsigned a=0;a<3;a++)out[a]=in[a]+d->subject[12+a];return finite_array(out,3);}
    if(mode!=0)return false;
    if(d->key_reference_flags[0]){
        if(!d->has_fixed_subject)return false;
        float m[16];memcpy(m,d->fixed_subject,sizeof(m));for(unsigned a=0;a<3;a++)m[12+a]=d->subject[12+a];
        return mw_nis_director_transform(m,in,out);
    }
    if(d->key_reference_flags[1])return false;
    return mw_nis_director_transform(d->subject,in,out);
}
static bool keys_shared(const unsigned char *a,const unsigned char *b){
    if(a[0]!=b[0]||a[4]!=b[4]||a[5]!=b[5])return false;
    const unsigned scalar[]={20,76,84};
    for(unsigned i=0;i<3;i++)if(fabsf(real(a+scalar[i]+4)-real(b+scalar[i]))>.0010000000474974513f)return false;
    for(unsigned i=0;i<3;i++){
        if(fabsf(real(a+40+i*4)-real(b+28+i*4))>.0010000000474974513f)return false;
        if(fabsf(real(a+64+i*4)-real(b+52+i*4))>.0010000000474974513f)return false;
    }
    return true;
}
static bool parameter_camera(MwNisDirector *d,const MwNisPack *p,const MwNisTrack *t,float time,MwNisCamera *out){
    if(!d||!p||!p->data||!t||!out||!isfinite(time)||time<0||!isfinite(t->duration)||t->duration<=0||!t->key_count||t->first_key>=p->keys||t->key_count>p->keys-t->first_key)return false;
    if(time>1)time=1;
    uint32_t index=0;
    for(uint32_t i=1;i<t->key_count;i++)if(real(p->data+p->key_at+(t->first_key+i)*212+16)<=time)index=i;else break;
    const unsigned char *key=p->data+p->key_at+(t->first_key+index)*212;
    MwNisDirector staged=*d;memcpy(staged.key_reference_flags,key+8,4);
    bool previous=staged.has_active_key&&staged.active_data==p->data&&staged.active_first_key==t->first_key&&staged.active_key<t->key_count;
    bool changed=!previous||staged.active_key!=index;
    if(changed||memcmp(staged.scene,staged.prepared_scene,64)||staged.scene_ground_height!=staged.prepared_height){
        staged.prepared_count=0;memcpy(staged.prepared_scene,staged.scene,64);staged.prepared_height=staged.scene_ground_height;
    }
    bool reset=changed&&(previous?!keys_shared(p->data+p->key_at+(t->first_key+staged.active_key)*212,key):!(key[1]&1u));
    if(reset&&staged.has_subject){memcpy(staged.fixed_subject,staged.subject,64);staged.has_fixed_subject=true;}
    MwNisProviders provider={prepare,resolve,&staged};
    if(!mw_nis_camera_parameter_provided(p,t,time,&provider,out))return false;
    staged.has_active_key=true;staged.active_data=p->data;staged.active_first_key=t->first_key;staged.active_key=index;
    *d=staged;return true;
}
bool mw_nis_director_camera(MwNisDirector *d,const MwNisPack *p,const MwNisTrack *t,float seconds,MwNisCamera *out){
    if(!t||!isfinite(seconds)||seconds<0||!isfinite(t->duration)||t->duration<=0)return false;
    return parameter_camera(d,p,t,seconds/t->duration,out);
}
bool mw_nis_director_scene_camera(MwNisDirector *d,const MwNisPack *p,const MwNisTrack *t,float elapsed,float start,float total,MwNisCamera *out){
    if(!d||!p||!t||!out||!isfinite(elapsed)||!isfinite(start)||!isfinite(total)||!(total>start))return false;
    float parameter=(elapsed-start)/(total-start);if(parameter<0)parameter=0;if(parameter>1)parameter=1;
    MwNisCamera result;
    if(!parameter_camera(d,p,t,parameter,&result))return false;
    result.fov_turn=(float)(uint16_t)result.fov_turn;
    result.finished=elapsed>=total;*out=result;return true;
}
static bool selection_point(MwNisDirector *d,uint8_t mode,bool target,const float in[3],float out[3]){
    float adjusted[3];if(!prepare(d,mode,target,in,adjusted))return false;
    if(mode==0)return d->has_subject&&mw_nis_director_transform(d->subject,adjusted,out);
    return resolve(d,mode,target,adjusted,out);
}
bool mw_nis_director_choose_track(MwNisDirector *d,const MwNisPack *p,const MwNisScene *s,uint32_t *index){
    if(!d||!p||!p->data||!s||!index||!s->track_count)return false;
    if(s->track_count==1){*index=0;return true;}
    if(!d->has_subject||!finite_array(d->subject,16))return false;
    uint32_t best=0;float score=-1;
    for(uint32_t i=0;i<s->track_count;i++){
        MwNisTrack track;if(!mw_nis_track(p,s,i,&track)||!track.key_count)return false;
        const unsigned char *first=p->data+p->key_at+track.first_key*212;
        unsigned skip=first[1]?1u:0u;if(skip>=track.key_count)return false;
        const unsigned char *r=first+skip*212;float eye[3],look[3],point[3];
        for(unsigned a=0;a<3;a++)point[a]=real(r+28+skip*12+a*4);
        if(!selection_point(d,r[4],false,point,eye))return false;
        for(unsigned a=0;a<3;a++)point[a]=real(r+52+skip*12+a*4);
        if(!selection_point(d,r[5],true,point,look))return false;
        float x=eye[0]-look[0],y=eye[1]-look[1],z=0;
        float length=mw_gekko_sqrt_newton2(fmaf(x,x,y*y));
        if(length!=0){float reciprocal=1/length;x=x*reciprocal;y=y*reciprocal;}else{x=1;y=0;}
        float value=fmaf(z,d->subject[2],fmaf(x,d->subject[0],y*d->subject[1]));
        if(value>score){score=value;best=i;}
    }
    *index=best;return true;
}
void mw_nis_director_invalidate_ground(MwNisDirector *d){if(d)d->prepared_count=0;}
