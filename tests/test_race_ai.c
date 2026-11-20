#include "mw_race_ai.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static MwRaceAI ai;
static void *load(const char *path,size_t *n){FILE *f=fopen(path,"rb");assert(f);assert(!fseek(f,0,SEEK_END));long bytes=ftell(f);rewind(f);assert(bytes>0);void *p=malloc((size_t)bytes);assert(p&&fread(p,1,(size_t)bytes,f)==(size_t)bytes);fclose(f);*n=(size_t)bytes;return p;}
static int drive(void *ctx,DriveState *s,float *height,DriveInput input,float dt){(void)ctx;(void)height;return drive_step(s,input,dt)?1:-1;}
static int fail_drive(void *ctx,DriveState *s,float *height,DriveInput input,float dt){(void)ctx;(void)height;(void)input;(void)dt;s->x=12345;return -1;}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void put(unsigned char *p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(n>>(i*8));}
int main(int argc,char **argv){
 assert(argc==4);size_t a,b,c;void *pack_bytes=load(argv[1],&a),*catalog_bytes=load(argv[2],&b),*road_bytes=load(argv[3],&c);
 MwRaceAIPack pack;MwEventCatalog catalog;MwTrafficWorld roads;assert(mw_race_ai_pack_open(&pack,pack_bytes,a)&&mw_event_catalog_open(&catalog,catalog_bytes,b)&&mw_traffic_open(&roads,road_bytes,c));
 const uint32_t ids[]={0x42938ce2,0xd348f2cd,0x6ddd8383,0x9f60a40e,0xf7e4440a};unsigned actual_count=0,explicit_count=0;
 for(unsigned event=0;event<5;event++){
  unsigned count=event==3?3:1;MwRaceAIWork prepare={0};assert(mw_race_ai_begin(&ai,&pack,&catalog,&roads,ids[event],(float[3]){0,0,0},&prepare));assert(ai.count==count&&!ai.running);
  for(unsigned i=0;i<count;i++){
   MwRaceAISpec spec;assert(mw_race_ai_spec(&pack,ids[event],i,&spec));assert(!strcmp(spec.model,ai.actors[i].spec.model));actual_count++;explicit_count+=spec.explicit_spawn;
   assert(ai.actors[i].path_count>2&&ai.actors[i].path_count<=MW_RACE_AI_POINTS);assert(ai.actors[i].progress.route.checkpoints==ai.checkpoints);
   printf("%08x actor%u %s %s: %u source-curve guide points\n",ids[event],i,spec.model,spec.explicit_spawn?"explicitspawn":"nativegrid",ai.actors[i].path_count);
  }
  unsigned rank=999;MwRaceProgress player;assert(mw_race_begin(&player,&ai.route));float player_position[]={0,0,0};assert(!mw_race_ai_rank(&ai,&player,player_position,&rank)&&rank==999);
  assert(!mw_race_ai_start(&ai));for(unsigned i=0;i<count;i++)assert(mw_race_ai_admit(&ai,i,true));assert(mw_race_ai_start(&ai));assert(!mw_race_ai_admit(&ai,0,false));
  MwRaceAIActor before[3];memcpy(before,ai.actors,sizeof before);assert(mw_race_ai_pause(&ai,true));MwRaceAIWork work={0};assert(mw_race_ai_step(&ai,1.f/30,drive,NULL,&work));assert(!memcmp(before,ai.actors,sizeof before)&&!work.drive_calls);assert(mw_race_ai_pause(&ai,false));
  assert(!mw_race_ai_step(&ai,1.f/30,fail_drive,NULL,&work));assert(!memcmp(before,ai.actors,sizeof before));assert(!mw_race_ai_rank(&ai,&player,player_position,&rank));
  memset(&work,0,sizeof work);for(unsigned frame=0;frame<1200;frame++)assert(mw_race_ai_step(&ai,1.f/30,drive,NULL,&work));assert(work.drive_calls<=1200*count&&work.guide_checks<=1200*count*32&&work.gate_tests<=1200*count*32);
  assert(!work.planner_nodes&&!work.planner_edges&&!work.nearest_nodes);assert(mw_race_ai_rank(&ai,&player,player_position,&rank)&&rank>=1&&rank<=count+1);
  for(unsigned i=0;i<count;i++){printf("  actor%u after40s: gate%zu lap%u cursor%u/%u speed%.2f\n",i,ai.actors[i].progress.next,ai.actors[i].progress.lap,ai.actors[i].path_cursor,ai.actors[i].path_count,(double)ai.actors[i].motion.speed);assert(isfinite(ai.actors[i].motion.x)&&isfinite(ai.actors[i].motion.z));}
  /* Rank is a function of actual progress, never a default player win. */
  for(unsigned i=0;i<count;i++){ai.actors[i].progress.finished=true;ai.actors[i].progress.elapsed_us=100;}
  player.finished=true;player.elapsed_us=101;assert(mw_race_ai_rank(&ai,&player,player_position,&rank)&&rank==count+1);
  player.elapsed_us=99;assert(mw_race_ai_rank(&ai,&player,player_position,&rank)&&rank==1);
  ai.actors[0].admitted=false;assert(!mw_race_ai_rank(&ai,&player,player_position,&rank));
 }
 assert(actual_count==7&&explicit_count==4);
 unsigned char *bad=malloc(a);assert(bad);memcpy(bad,pack_bytes,a);bad[a-1]^=1;MwRaceAIPack old=pack;assert(!mw_race_ai_pack_open(&pack,bad,a)&&!memcmp(&pack,&old,sizeof pack));
 const unsigned corrupt[]={16,20,24,28,32,64,96,128,132,136,140,220,228,248,656};
 for(unsigned i=0;i<sizeof corrupt/sizeof *corrupt;i++){memcpy(bad,pack_bytes,a);bad[corrupt[i]]^=1;put(bad+12,crc(bad+16,a-16));assert(!mw_race_ai_pack_open(&pack,bad,a));assert(!memcmp(&pack,&old,sizeof pack));}
 assert(!mw_race_ai_pack_open(&pack,pack_bytes,a-1));free(bad);
 free(pack_bytes);free(catalog_bytes);free(road_bytes);puts("Five source-event plans, seven actual models/spawns, bounded native steps, rollback/pause and honest ranking passed.");return 0;
}
