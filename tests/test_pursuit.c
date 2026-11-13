#include "mw_pursuit.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint32_t le(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void put(unsigned char *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void repair(unsigned char *p,size_t n){put(p+12,crc(p+16,n-16));}
static void reject(const void *p,size_t n){MwPursuitPack out={.bytes=123},before=out;assert(!mw_pursuit_pack_open(&out,p,n));assert(!memcmp(&out,&before,sizeof(out)));}
typedef struct {unsigned calls,fail_on;bool block;} DriveFixture;
static int driving(void *ctx,DriveState *d,float *height,DriveInput input,float seconds){
 DriveFixture *f=ctx;f->calls++;if(f->fail_on==f->calls){d->x+=100;*height+=50;return -1;}
 if(f->block){d->x+=100;*height+=50;return 0;}
 return drive_step(d,input,seconds)?1:-1;
}
static void crossing(const MwPursuitTrigger *t,float before[3],float after[3]){
 float angle=t->rotation*.017453292519943295f;
 for(unsigned a=0;a<3;a++)before[a]=after[a]=t->position[a];
 before[0]-=cosf(angle)*4;before[1]-=sinf(angle)*4;after[0]+=cosf(angle)*4;after[1]+=sinf(angle)*4;
}
int main(int argc,char **argv){
 assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);unsigned char data[512],bad[512];assert(fread(data,1,sizeof(data),f)==sizeof(data)&&fgetc(f)==EOF&&!fclose(f));
 MwPursuitPack pack;assert(mw_pursuit_pack_open(&pack,data,sizeof(data)));assert(pack.events==2&&pack.spawns==4&&pack.triggers==5);
 assert(fabsf(pack.source_speed_multiplier-1.6f)<.000001f&&fabsf(pack.source_acceleration_multiplier-1.05f)<.000001f);
 const uint32_t events[]={0x6ddd8383,0xf7e4440a};float origin[]={-200,20,300};uintptr_t actor=123;
 unsigned checks=0;
 for(unsigned e=0;e<2;e++){
  float initial[]={0,0,0};MwPursuit s;assert(mw_pursuit_begin(&s,&pack,events[e],origin,actor,initial));assert(s.has_event&&!s.cops_enabled&&!s.pursuit_active);
  MwPursuitTrigger spawn;assert(mw_pursuit_trigger_get(&s,0,&spawn)&&spawn.action==MW_PURSUIT_SPAWN);
  float from[3],to[3];crossing(&spawn,from,to);assert(mw_pursuit_relocate(&s,actor,from));
  MwPursuit unchanged=s;unsigned signal=99;assert(!mw_pursuit_motion(&s,actor+1,to,1,&signal,NULL));assert(!memcmp(&s,&unchanged,sizeof(s))&&signal==99);
  MwPursuitWork work={0};assert(mw_pursuit_motion(&s,actor,to,1,&signal,&work));assert(signal==MW_PURSUIT_SPAWN&&s.cops_enabled&&s.pursuit_active);
  assert(work.trigger_tests<=3&&s.actors[0].active&&s.actors[1].active);
  const unsigned char *record=data+pack.spawns_at+e*64;float source_x;uint32_t bits=le(record+8);memcpy(&source_x,&bits,4);assert(s.actors[0].motion.x==source_x-origin[0]);
  MwPursuit spawned=s;assert(mw_pursuit_enter(&s,actor,spawn.key,&signal)&&signal==0);assert(!memcmp(&s,&spawned,sizeof(s)));
  DriveState player={.x=to[0]-origin[0],.z=-to[1]-origin[2],.heading=1.57079632679f,.speed=6};float height=to[2]-origin[1];
  float first_distance=hypotf(s.actors[0].motion.x-player.x,s.actors[0].motion.z-player.z),closest=first_distance;unsigned max_nav=0;
  DriveFixture fixture={0};
  for(unsigned frame=0;frame<1200;frame++){
   player.x+=6.f/30;float source[]={player.x+origin[0],-(player.z+origin[2]),height+origin[1]};
   /* Exercise continuous actual-player motion and the bounded native trail. */
   assert(mw_pursuit_motion(&s,actor,source,1,&signal,NULL));MwPursuitWork w={0};assert(mw_pursuit_step(&s,&player,height,1.f/30,driving,&fixture,&w));
   assert(w.controllers<=2&&w.drive_calls<=2&&w.navigation_checks<=MW_PURSUIT_COPS*MW_PURSUIT_TRAIL);if(w.navigation_checks>max_nav)max_nav=w.navigation_checks;
   float distance=hypotf(s.actors[0].motion.x-player.x,s.actors[0].motion.z-player.z);if(distance<closest)closest=distance;checks++;
  }
  assert(closest<first_distance*.8f);
  printf("Event%08x: 2 cops,1200 controller ticks, nearest gap %.1f→%.1f, max%u navigation checks/tick.\n",events[e],(double)first_distance,(double)closest,max_nav);
  fixture.calls=0;fixture.fail_on=2;unchanged=s;assert(!mw_pursuit_step(&s,&player,height,1.f/30,driving,&fixture,NULL));assert(!memcmp(&s,&unchanged,sizeof(s)));
  fixture.fail_on=0;fixture.block=true;fixture.calls=0;float px=s.actors[0].motion.x,py=s.actors[0].height;assert(mw_pursuit_step(&s,&player,height,1.f/30,driving,&fixture,&work));assert(s.actors[0].motion.x==px&&s.actors[0].height==py&&s.actors[0].motion.speed==0);
  MwPursuitTrigger bail;assert(mw_pursuit_trigger_get(&s,1,&bail)&&bail.action==MW_PURSUIT_BAIL);crossing(&bail,from,to);assert(mw_pursuit_relocate(&s,actor,from));assert(mw_pursuit_motion(&s,actor,to,1,&signal,NULL)&&signal==MW_PURSUIT_BAIL);
  assert(!s.pursuit_active&&s.no_new_pursuits&&s.actors[0].active&&s.actors[0].released&&s.actors[1].released);
  if(e==0){MwPursuitTrigger call;assert(mw_pursuit_trigger_get(&s,2,&call)&&call.action==MW_PURSUIT_911);assert(mw_pursuit_enter(&s,actor,call.key,&signal)&&signal==MW_PURSUIT_911&&s.called_911);}
  unchanged=s;assert(mw_pursuit_enter(&s,actor,0xdeadbeef,&signal)&&signal==0);assert(!memcmp(&s,&unchanged,sizeof(s)));
 }
 /* Bail before reaching spawn must prohibit a later new pursuit. */
 MwPursuit s;float zero[3]={0};assert(mw_pursuit_begin(&s,&pack,events[0],zero,actor,zero));MwPursuitTrigger t;unsigned signal;assert(mw_pursuit_trigger_get(&s,1,&t)&&mw_pursuit_enter(&s,actor,t.key,&signal));assert(mw_pursuit_trigger_get(&s,0,&t)&&mw_pursuit_enter(&s,actor,t.key,&signal)&&signal==0&&!s.actors[0].active);
 MwPursuit before=s;float nan[]={NAN,0,0};assert(!mw_pursuit_motion(&s,actor,nan,1,&signal,NULL));assert(!memcmp(&s,&before,sizeof(s)));
 reject(data,0);reject(data,159);reject(data,511);reject(NULL,512);
 const unsigned corrupt[]={0,4,8,12,16,20,24,28,32,36,40,44,60,160,164,168,172,176,180,184,188,224,228,248,252,352,356,380};
 for(unsigned i=0;i<sizeof(corrupt)/sizeof(*corrupt);i++){memcpy(bad,data,512);bad[corrupt[i]]^=1;if(corrupt[i]!=12)repair(bad,512);if(corrupt[i]==160||corrupt[i]==224||corrupt[i]==352)continue;reject(bad,512);}
 memcpy(bad,data,512);put(bad+48,0x7fc00000);repair(bad,512);reject(bad,512);
 memcpy(bad,data,512);put(bad+pack.triggers_at+24,0);repair(bad,512);reject(bad,512);
 printf("Pursuit: %u bounded two-cop ticks, source Width spawning/bail/911, actor guards, callback rollback, no-new-pursuit and malformed packet checks pass; state%zuB.\n",checks,sizeof(MwPursuit));return 0;
}
