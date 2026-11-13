#include "mw_pursuit.h"
#include "mw_playable_race.h"
#include <math.h>
#include <string.h>
static uint32_t word(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static float real(const unsigned char *p){uint32_t n=word(p);float f;memcpy(&f,&n,4);return f;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static bool point(const float p[3]){return p&&isfinite(p[0])&&isfinite(p[1])&&isfinite(p[2])&&fabsf(p[0])<=20000&&fabsf(p[1])<=20000&&fabsf(p[2])<=20000;}
static float clamp(float v,float lo,float hi){return v<lo?lo:v>hi?hi:v;}
static const unsigned char *event_at(const MwPursuitPack *p,uint32_t i){return p->data+p->events_at+i*32;}
bool mw_pursuit_pack_open(MwPursuitPack *out,const void *data,size_t bytes){
 if(!out||!data||bytes<160||bytes>16384)return false;
 const unsigned char *p=data;
 if(memcmp(p,"NPP1",4)||word(p+4)!=1||word(p+8)!=bytes||word(p+12)!=crc(p+16,bytes-16))return false;
 MwPursuitPack v={.data=p,.bytes=bytes,.events=word(p+16),.events_at=word(p+20),.spawns_at=word(p+24),.spawns=word(p+28),.triggers_at=word(p+32),.triggers=word(p+36),.model_key=word(p+40),.source_speed_multiplier=real(p+48),.source_acceleration_multiplier=real(p+52)};
 if(v.events!=2||v.spawns!=4||v.triggers!=5||v.events_at!=160||v.spawns_at!=224||v.triggers_at!=352||bytes!=512||!v.model_key||word(p+44)||word(p+60)||!isfinite(v.source_speed_multiplier)||v.source_speed_multiplier<=0||!isfinite(v.source_acceleration_multiplier)||v.source_acceleration_multiplier<=0||!isfinite(real(p+56)))return false;
 uint32_t expected_spawn=0,expected_trigger=0,previous=0;
 for(uint32_t i=0;i<v.events;i++){
  const unsigned char *e=event_at(&v,i);uint32_t key=word(e),s=word(e+4),ns=word(e+8),t=word(e+12),nt=word(e+16);
  if(!key||(i&&key<=previous)||s!=expected_spawn||ns!=2||t!=expected_trigger||nt<2||nt>3||word(e+20)||word(e+24)||word(e+28))return false;
  expected_spawn+=ns;expected_trigger+=nt;previous=key;
 }
 if(expected_spawn!=v.spawns||expected_trigger!=v.triggers)return false;
 for(uint32_t i=0;i<v.spawns;i++){
  const unsigned char *s=p+v.spawns_at+i*32;
  if(!word(s)||word(s+4)!=v.model_key||word(s+24)||word(s+28))return false;
  for(unsigned a=0;a<4;a++)if(!isfinite(real(s+8+a*4)))return false;
  for(unsigned a=0;a<3;a++)if(fabsf(real(s+8+a*4))>20000)return false;
 }
 for(uint32_t i=0;i<v.triggers;i++){
  const unsigned char *t=p+v.triggers_at+i*32;uint32_t action=word(t+4);
  if(!word(t)||(action!=MW_PURSUIT_SPAWN&&action!=MW_PURSUIT_BAIL&&action!=MW_PURSUIT_911)||word(t+28))return false;
  for(unsigned a=0;a<5;a++)if(!isfinite(real(t+8+a*4)))return false;
  for(unsigned a=0;a<3;a++)if(fabsf(real(t+8+a*4))>20000)return false;
  if(real(t+24)<=0||real(t+24)>1000)return false;
 }
 for(uint32_t i=0;i<v.events;i++){
  const unsigned char *e=event_at(&v,i);unsigned actions=0;
  for(uint32_t j=0;j<word(e+16);j++){const unsigned char *t=p+v.triggers_at+(word(e+12)+j)*32;unsigned a=word(t+4);if(actions&a)return false;actions|=a;}
  if((actions&(MW_PURSUIT_SPAWN|MW_PURSUIT_BAIL))!=(MW_PURSUIT_SPAWN|MW_PURSUIT_BAIL))return false;
 }
 *out=v;return true;
}
MwPursuitTuning mw_pursuit_default_tuning(void){return (MwPursuitTuning){.top_speed=65,.closing_speed=8,.follow_distance=5,.trail_spacing=6,.steering_gain=2.5f};}
static bool tuning(const MwPursuitTuning *t){return isfinite(t->top_speed)&&t->top_speed>0&&t->top_speed<=65&&isfinite(t->closing_speed)&&t->closing_speed>=0&&t->closing_speed<=30&&isfinite(t->follow_distance)&&t->follow_distance>0&&t->follow_distance<=50&&isfinite(t->trail_spacing)&&t->trail_spacing>0&&t->trail_spacing<=50&&isfinite(t->steering_gain)&&t->steering_gain>0&&t->steering_gain<=10;}
bool mw_pursuit_begin(MwPursuit *out,const MwPursuitPack *pack,uint32_t event,const float origin[3],uintptr_t actor,const float source[3]){
 if(!out||!pack||!pack->data||!point(origin)||!point(source)||!actor)return false;
 MwPursuit s={.pack=pack,.event=event,.player_actor=actor,.tuning=mw_pursuit_default_tuning()};memcpy(s.origin,origin,sizeof(s.origin));memcpy(s.previous_source,source,sizeof(s.previous_source));
 for(uint32_t i=0;i<pack->events;i++)if(word(event_at(pack,i))==event){s.event_index=i;s.has_event=true;break;}
 s.trail[0][0]=source[0]-origin[0];s.trail[0][1]=source[2]-origin[1];s.trail[0][2]=-source[1]-origin[2];s.trail_total=1;*out=s;return true;
}
bool mw_pursuit_trigger_get(const MwPursuit *s,unsigned i,MwPursuitTrigger *out){
 if(!s||!s->pack||!out||!s->has_event)return false;
 const unsigned char *e=event_at(s->pack,s->event_index);if(i>=word(e+16))return false;
 const unsigned char *p=s->pack->data+s->pack->triggers_at+(word(e+12)+i)*32;
 MwPursuitTrigger t={.key=word(p),.action=word(p+4),.rotation=real(p+20),.width=real(p+24)};
 for(unsigned a=0;a<3;a++)t.position[a]=real(p+8+a*4);
 *out=t;return true;
}
bool mw_pursuit_enter(MwPursuit *s,uintptr_t actor,uint32_t key,unsigned *signals){
 if(!s||!s->pack||!signals||actor!=s->player_actor)return false;
 *signals=0;if(!s->has_event)return true;
 const unsigned char *e=event_at(s->pack,s->event_index);
 for(unsigned i=0;i<word(e+16);i++){
  MwPursuitTrigger t;mw_pursuit_trigger_get(s,i,&t);if(t.key!=key)continue;if(s->fired&(1u<<i))return true;
  if(t.action==MW_PURSUIT_SPAWN){
   if(s->no_new_pursuits){s->fired|=1u<<i;return true;}
   for(unsigned j=0;j<MW_PURSUIT_COPS;j++){
    const unsigned char *p=s->pack->data+s->pack->spawns_at+(word(e+4)+j)*32;MwPursuitCar c={.active=true,.model_key=word(p+4),.spawn_key=word(p),.height=real(p+16)-s->origin[1],.trail_serial=s->trail_total-1};
    float yaw=(90+remainderf(real(p+20),360))*.017453292519943295f;drive_reset(&c.motion,real(p+8)-s->origin[0],-real(p+12)-s->origin[2],yaw);s->actors[j]=c;
   }
   s->cops_enabled=true;s->pursuit_active=true;
  }else if(t.action==MW_PURSUIT_BAIL){
   s->pursuit_active=false;s->no_new_pursuits=true;
   for(unsigned j=0;j<MW_PURSUIT_COPS;j++)s->actors[j].released=true;
  }else s->called_911=true;
  s->fired|=1u<<i;*signals=t.action;return true;
 }
 return true;
}
static bool append_trail(MwPursuit *s,const float source[3],bool reset){
 float p[3]={source[0]-s->origin[0],source[2]-s->origin[1],-source[1]-s->origin[2]};
 if(reset){s->trail_total=1;memcpy(s->trail[0],p,sizeof(p));for(unsigned j=0;j<MW_PURSUIT_COPS;j++)s->actors[j].trail_serial=0;return true;}
 const float *last=s->trail[(s->trail_total-1)%MW_PURSUIT_TRAIL];float dx=p[0]-last[0],dz=p[2]-last[2];
 if(dx*dx+dz*dz<s->tuning.trail_spacing*s->tuning.trail_spacing)return true;
 if(s->trail_total==UINT32_MAX)return false;
 memcpy(s->trail[s->trail_total%MW_PURSUIT_TRAIL],p,sizeof(p));s->trail_total++;return true;
}
bool mw_pursuit_relocate(MwPursuit *s,uintptr_t actor,const float source[3]){
 if(!s||!s->pack||actor!=s->player_actor||!point(source))return false;
 if(!append_trail(s,source,true))return false;
 memcpy(s->previous_source,source,sizeof(s->previous_source));return true;
}
bool mw_pursuit_motion(MwPursuit *s,uintptr_t actor,const float source[3],float radius,unsigned *signals,MwPursuitWork *work){
 if(!s||!s->pack||!signals||actor!=s->player_actor||!point(source)||!isfinite(radius)||radius<0||radius>10||!tuning(&s->tuning))return false;
 MwPursuit next=*s;unsigned flags=0;double fractions[3];unsigned ids[3],count=0;
 if(s->has_event){
  const unsigned char *e=event_at(s->pack,s->event_index);
  for(unsigned i=0;i<word(e+16);i++){
   if(s->fired&(1u<<i))continue;
   MwPursuitTrigger t;mw_pursuit_trigger_get(s,i,&t);MwEventNode n={.present=3,.rotation=t.rotation};memcpy(n.position,t.position,sizeof(n.position));double at;
   if(work)work->trigger_tests++;
   if(mw_playable_race_width_sweep(&n,t.width,s->previous_source,source,radius,&at)){fractions[count]=at;ids[count++]=i;}
  }
  for(unsigned i=0;i<count;i++)for(unsigned j=i+1;j<count;j++)if(fractions[j]<fractions[i]){double f=fractions[i];fractions[i]=fractions[j];fractions[j]=f;unsigned n=ids[i];ids[i]=ids[j];ids[j]=n;}
  for(unsigned i=0;i<count;i++){MwPursuitTrigger t;mw_pursuit_trigger_get(s,ids[i],&t);unsigned action;if(!mw_pursuit_enter(&next,actor,t.key,&action))return false;flags|=action;}
 }
 if(!append_trail(&next,source,false))return false;
 memcpy(next.previous_source,source,sizeof(next.previous_source));*s=next;*signals=flags;return true;
}
static bool drive_valid(const DriveState *d){return d&&isfinite(d->x)&&isfinite(d->z)&&isfinite(d->heading)&&isfinite(d->speed)&&isfinite(d->steering)&&isfinite(d->lateral_speed)&&isfinite(d->yaw_rate)&&isfinite(d->drift);}
bool mw_pursuit_step(MwPursuit *s,const DriveState *player,float player_height,float seconds,MwPursuitDrive drive,void *ctx,MwPursuitWork *work){
 if(!s||!s->pack||!drive_valid(player)||!isfinite(player_height)||!isfinite(seconds)||seconds<=0||seconds>.1f||!drive||!tuning(&s->tuning)||!s->trail_total)return false;
 MwPursuit next=*s;
 for(unsigned i=0;i<MW_PURSUIT_COPS;i++){
  MwPursuitCar *c=next.actors+i;if(!c->active)continue;if(!drive_valid(&c->motion)||!isfinite(c->height))return false;if(work)work->controllers++;
  DriveInput input={0};
  if(c->released){input.brake=.15f;input.steering=0;}
  else {
   uint32_t oldest=next.trail_total>MW_PURSUIT_TRAIL?next.trail_total-MW_PURSUIT_TRAIL:0;
   if(c->trail_serial<oldest)c->trail_serial=oldest;
   if(c->trail_serial>=next.trail_total)c->trail_serial=next.trail_total-1;
   for(unsigned j=0;j<MW_PURSUIT_TRAIL&&c->trail_serial+1<next.trail_total;j++){
    const float *p=next.trail[c->trail_serial%MW_PURSUIT_TRAIL];float dx=p[0]-c->motion.x,dz=p[2]-c->motion.z;if(work)work->navigation_checks++;
    if(dx*dx+dz*dz>next.tuning.follow_distance*next.tuning.follow_distance)break;
    c->trail_serial++;
   }
   float tx=player->x,tz=player->z;
   if(c->trail_serial+1<next.trail_total){const float *p=next.trail[c->trail_serial%MW_PURSUIT_TRAIL];tx=p[0];tz=p[2];}
   float dx=tx-c->motion.x,dz=tz-c->motion.z,distance=sqrtf(dx*dx+dz*dz),angle=remainderf(atan2f(dx,dz)-c->motion.heading,6.283185307179586f);
   input.steering=clamp(angle*next.tuning.steering_gain,-1,1);
   float wanted=fminf(next.tuning.top_speed,fmaxf(0,player->speed)+next.tuning.closing_speed);
   wanted*=fmaxf(.2f,1-fminf(fabsf(angle),1.3f)*.6f);
   if(c->trail_serial+1>=next.trail_total&&distance<next.tuning.follow_distance*2)wanted=fmaxf(0,player->speed-2);
   input.throttle=c->motion.speed<wanted?1:0;input.brake=clamp((c->motion.speed-wanted)*.1f,0,1);
  }
  DriveState previous=c->motion;float old_height=c->height;
  if(work)work->drive_calls++;
  int admitted=drive(ctx,&c->motion,&c->height,input,seconds);
  if(admitted<0||!drive_valid(&c->motion)||!isfinite(c->height))return false;
  if(!admitted){c->motion=previous;c->height=old_height;c->motion.speed=0;c->motion.lateral_speed=0;if(work)work->blocked_steps++;}
 }
 *s=next;return true;
}
