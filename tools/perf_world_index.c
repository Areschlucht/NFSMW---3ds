#include "perf_world_index.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

static uint32_t hash_vertex(const WorldVertex *v)
{
    const unsigned char *bytes=(const unsigned char *)v;
    uint32_t hash=2166136261u;
    for (size_t i=0;i<sizeof(*v);++i) { hash^=bytes[i];hash*=16777619u; }
    return hash;
}
void perf_world_index_free(PerfIndexedWorld *world)
{
    if (!world) return;
    free(world->vertices);free(world->indices);memset(world,0,sizeof(*world));
}
PerfIndexResult perf_world_index(const NfsVertex *source,size_t count,PerfIndexedWorld *out)
{
    if (!out) return PERF_INDEX_INVALID;
    memset(out,0,sizeof(*out));
    if (!source || !count || count>200000 || count%3) return PERF_INDEX_INVALID;
    size_t slots=1;
    while (slots<count*2) slots*=2;
    uint32_t *table=calloc(slots,sizeof(*table));
    PerfIndexedWorld candidate={.index_count=(uint32_t)count};
    size_t capacity=count<65536?count:65536;
    candidate.vertices=malloc(capacity*sizeof(*candidate.vertices));
    candidate.indices=malloc(count*sizeof(*candidate.indices));
    PerfIndexResult result=PERF_INDEX_ALLOCATION;
    if (!table || !candidate.vertices || !candidate.indices) goto failed;
    size_t probes=0;
    for (size_t i=0;i<count;++i) {
        /* The NFM decoder remains the authoritative range/normal validator.
           Guard the fields this packer consumes when called independently. */
        for (unsigned a=0;a<3;++a) if (!isfinite(source[i].position[a])) { result=PERF_INDEX_INVALID;goto failed; }
        for (unsigned a=0;a<2;++a) if (!isfinite(source[i].uv[a])) { result=PERF_INDEX_INVALID;goto failed; }
        for (unsigned a=0;a<4;++a) if (!isfinite(source[i].color[a])) { result=PERF_INDEX_INVALID;goto failed; }
        WorldVertex vertex;world_vertex_pack(&vertex,&source[i],1);
        uint32_t bucket=hash_vertex(&vertex)&(uint32_t)(slots-1);
        while (table[bucket]) {
            if (++probes>count*32) { result=PERF_INDEX_BUDGET;goto failed; }
            uint32_t index=table[bucket]-1;
            if (!memcmp(&candidate.vertices[index],&vertex,sizeof(vertex))) {
                candidate.indices[i]=(uint16_t)index;goto next_vertex;
            }
            bucket=(bucket+1)&(uint32_t)(slots-1);
        }
        if (candidate.vertex_count==65536) { result=PERF_INDEX_OVERFLOW;goto failed; }
        candidate.vertices[candidate.vertex_count]=vertex;
        candidate.indices[i]=(uint16_t)candidate.vertex_count;
        table[bucket]=++candidate.vertex_count;
next_vertex:;
    }
    free(table);*out=candidate;return PERF_INDEX_OK;
failed:
    free(table);perf_world_index_free(&candidate);return result;
}
