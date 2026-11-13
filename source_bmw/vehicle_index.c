#include "vehicle_index.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

_Static_assert(sizeof(NfsVertex)==48,"Vehicle indexing preserves the complete48-byte NfsVertex");

static uint32_t hash_vertex(const NfsVertex *vertex)
{
    const unsigned char *bytes=(const unsigned char *)vertex;uint32_t hash=2166136261u;
    for(size_t i=0;i<sizeof(*vertex);i++){hash^=bytes[i];hash*=16777619u;}
    return hash;
}
static bool finite_vertex(const NfsVertex *v)
{
    for(unsigned i=0;i<3;i++)if(!isfinite(v->position[i])||!isfinite(v->normal[i]))return false;
    for(unsigned i=0;i<2;i++)if(!isfinite(v->uv[i]))return false;
    for(unsigned i=0;i<4;i++)if(!isfinite(v->color[i]))return false;
    return true;
}
void vehicle_index_free(VehicleIndexedVertices *mesh)
{
    if(!mesh)return;
    free(mesh->vertices);free(mesh->indices);memset(mesh,0,sizeof(*mesh));
}
VehicleIndexResult vehicle_index_encode(const NfsVertex *source,size_t count,VehicleIndexedVertices *out)
{
    if(!out||!source||!count||count>200000||count%3)return VEHICLE_INDEX_INVALID;
    size_t slots=1;while(slots<count*2)slots*=2;
    uint32_t *table=calloc(slots,sizeof(*table));
    size_t capacity=count<65535?count:65535;
    VehicleIndexedVertices result={.index_count=(uint32_t)count};
    result.vertices=malloc(capacity*sizeof(*result.vertices));result.indices=malloc(count*sizeof(*result.indices));
    VehicleIndexResult error=VEHICLE_INDEX_ALLOCATION;
    if(!table||!result.vertices||!result.indices)goto failed;
    size_t probes=0;
    for(size_t i=0;i<count;i++){
        if(!finite_vertex(&source[i])){error=VEHICLE_INDEX_INVALID;goto failed;}
        uint32_t bucket=hash_vertex(&source[i])&(uint32_t)(slots-1);
        while(table[bucket]){
            if(++probes>count*32){error=VEHICLE_INDEX_BUDGET;goto failed;}
            uint32_t index=table[bucket]-1;
            if(!memcmp(&result.vertices[index],&source[i],sizeof(*source))){result.indices[i]=(uint16_t)index;goto next;}
            bucket=(bucket+1)&(uint32_t)(slots-1);
        }
        if(result.vertex_count==65535){error=VEHICLE_INDEX_OVERFLOW;goto failed;}
        memcpy(&result.vertices[result.vertex_count],&source[i],sizeof(*source));
        result.indices[i]=(uint16_t)result.vertex_count;table[bucket]=++result.vertex_count;
next:;
    }
    free(table);*out=result;return VEHICLE_INDEX_OK;
failed:
    free(table);vehicle_index_free(&result);return error;
}
