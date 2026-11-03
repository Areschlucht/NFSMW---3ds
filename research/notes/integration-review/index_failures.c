#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "world_index.h"
static unsigned allocation_call,fail_call,live;
static void *review_malloc(size_t size){unsigned at=allocation_call++;if(at==fail_call)return NULL;void*p=malloc(size);if(p)++live;return p;}
static void *review_calloc(size_t count,size_t size){unsigned at=allocation_call++;if(at==fail_call)return NULL;void*p=calloc(count,size);if(p)++live;return p;}
static void review_free(void*p){if(p){assert(live);--live;}free(p);}
#define malloc review_malloc
#define calloc review_calloc
#define free review_free
#include "/workspace/NFSMW---3ds/source_bmw/world_index.c"
#undef malloc
#undef calloc
#undef free
static uint32_t review_hash(const WorldVertex*v){uint32_t h=2166136261u;const unsigned char*p=(const unsigned char*)v;for(unsigned i=0;i<sizeof(*v);++i){h^=p[i];h*=16777619u;}return h;}
int main(void){
 NfsVertex source[3]={0};for(unsigned i=0;i<3;++i){source[i].position[0]=i*.1f;source[i].color[3]=1;}
 for(unsigned fail=0;fail<3;++fail){allocation_call=0;fail_call=fail;WorldIndexedVertices out;memset(&out,0xa5,sizeof(out));assert(world_index_encode(source,3,&out)==WORLD_INDEX_ALLOCATION);assert(!out.vertices&&!out.indices&&!out.vertex_count&&!out.index_count);assert(live==0);world_index_free(&out);assert(live==0);}
 allocation_call=0;fail_call=UINT32_MAX;WorldIndexedVertices out;assert(world_index_encode(source,3,&out)==WORLD_INDEX_OK);assert(live==2);world_index_free(&out);assert(live==0);
 NfsVertex collisions[96]={0};unsigned found=0;
 for(uint32_t n=0;found<96 && n<1000000;++n){NfsVertex candidate={0};uint32_t bits=0x3e000000u+n;memcpy(&candidate.position[0],&bits,4);candidate.color[3]=1;WorldVertex packed;world_vertex_pack(&packed,&candidate,1);if((review_hash(&packed)&255u)==0)collisions[found++]=candidate;}
 assert(found==96);allocation_call=0;fail_call=UINT32_MAX;assert(world_index_encode(collisions,96,&out)==WORLD_INDEX_BUDGET);assert(!out.vertices&&!out.indices&&!out.vertex_count&&!out.index_count);assert(live==0);
 puts("Independent allocator-failure and adversarial hash-probe-budget checks passed; outputs empty, allocations balanced.");return 0;
}
