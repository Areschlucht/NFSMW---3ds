#include "world_collision_runtime.h"
#include <stdlib.h>
WorldCollisionRuntime *open_test_world(const char *path,size_t capacity){
    WorldCollisionRuntime *w=calloc(1,sizeof *w+capacity);if(!w)return NULL;
    if(world_collision_runtime_open(w,path,(unsigned char*)w+sizeof *w,capacity)){free(w);return NULL;}return w;
}
void close_test_world(WorldCollisionRuntime *w){world_collision_runtime_close(w);free(w);}
size_t test_active_bytes(const WorldCollisionRuntime *w){return w->arena_used;}
unsigned test_active_count(const WorldCollisionRuntime *w){return w->active_count;}
