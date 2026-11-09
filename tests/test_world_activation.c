#include "mw_world_state.h"
#include "world_collision_runtime.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static WorldCollisionRuntime world;
static void *load(const char *name,size_t *bytes){FILE *f=fopen(name,"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0);rewind(f);void *p=malloc((size_t)n);assert(p&&fread(p,1,(size_t)n,f)==(size_t)n);fclose(f);*bytes=(size_t)n;return p;}
static void activate(void){uint16_t ids[WORLD_COLLISION_MAX_ASSOCIATIONS];for(uint32_t i=0;i<world.association_count;i++)ids[i]=world.associations[i].section;WorldCollisionAdmission a;assert(!world_collision_runtime_activate(&world,ids,world.association_count,&a));}
int main(int argc,char **argv){
 assert(argc==5);size_t n,m;unsigned char *explore=load(argv[2],&n),*career=load(argv[3],&m);MwWorldState e,c;assert(mw_world_state_open(&e,explore,n)&&mw_world_state_open(&c,career,m));
 assert(e.bin==1&&c.bin==15);assert(mw_world_state_group(&e,0)==1&&mw_world_state_group(&e,3)==0&&mw_world_state_group(&e,71)==1);
 assert(mw_world_state_group(&c,496)==1&&mw_world_state_group(&e,496)==0&&mw_world_state_group(&c,3)==0);
 uint32_t flags;assert(mw_world_state_instance(&e,24588384,0x02808070,&flags)&&flags==0x02808070);
 void *arena=malloc(32*1024*1024);assert(arena);assert(!world_collision_runtime_open(&world,argv[1],arena,32*1024*1024));assert(mw_world_state_source_matches(&e,world.source_sha256));activate();
 const float a[]={-2482.38501f,166.637665f,354.401031f},b[]={-2482.58667f,166.637665f,354.244019f};
 WorldCollisionContact hit;assert(world_collision_runtime_wall(&world,a,b,0,&hit)==1&&hit.group_id==3);world_collision_runtime_close(&world);
 assert(!world_collision_runtime_open(&world,argv[1],arena,32*1024*1024));assert(!world_collision_runtime_bind_groups(&world,mw_world_state_group,&e));activate();
 assert(world_collision_runtime_wall(&world,a,b,0,&hit)==0);
 const float normal_a[]={-2447.614293f,170,396.274078f},normal_b[]={-2446.385705f,170,394.695924f};
 assert(world_collision_runtime_wall(&world,normal_a,normal_b,0,&hit)==1&&hit.group_id==0);
 world_collision_runtime_close(&world);
 size_t restore_bytes;void *restore=load(argv[4],&restore_bytes);MwWorldState r;assert(mw_world_state_open(&r,restore,restore_bytes));
 assert(!world_collision_runtime_open(&world,argv[1],arena,32*1024*1024));assert(!world_collision_runtime_bind_groups(&world,mw_world_state_group,&r));activate();
 assert(world_collision_runtime_wall(&world,a,b,0,&hit)==1&&hit.group_id==3);
 assert(mw_world_state_instance(&r,24588384,0x02808070,&flags)&&!(flags&16));
 world_collision_runtime_close(&world);free(restore);free(arena);free(explore);free(career);
 puts("Actual spawn blocker group3 removed; ordinary group0 wall still blocks; original career groups retained; enabling source group3 restores both its wall and render flags.");
}
