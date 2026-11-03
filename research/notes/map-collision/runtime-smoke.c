#include "world_collision_runtime.h"
#include <stdlib.h>
#include <stdio.h>
int main(int argc,char **argv){
    if(argc!=2)return 2;
    static WorldCollisionRuntime w;unsigned char *arena=malloc(6*1024*1024);if(!arena)return 3;
    int status=world_collision_runtime_open(&w,argv[1],arena,6*1024*1024);if(status){printf("open %d\n",status);return 4;}
    uint16_t ids[WORLD_COLLISION_MAX_ASSOCIATIONS];for(unsigned i=0;i<w.association_count;i++)ids[i]=w.associations[i].section;
    WorldCollisionAdmission a;status=world_collision_runtime_activate(&w,ids,w.association_count,&a);
    printf("status=%d packages=%u associations=%u active=%u bytes=%zu context=%zu\n",status,w.package_count,w.association_count,w.active_count,w.arena_used,sizeof w);
    world_collision_runtime_close(&w);free(arena);return status?5:0;
}
