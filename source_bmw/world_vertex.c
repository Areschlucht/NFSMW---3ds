#include "world_vertex.h"
#include <string.h>
_Static_assert(sizeof(WorldVertex)==36,"World vertex stride must match the GPU layout");
_Static_assert(offsetof(WorldVertex,uv)==12 && offsetof(WorldVertex,color)==20,"World attribute offsets");
void world_vertex_pack(WorldVertex *out,const NfsVertex *source,size_t count)
{
    for (size_t i=0;i<count;++i) {
        memcpy(out[i].position,source[i].position,sizeof(out[i].position));
        out[i].uv[0]=source[i].uv[0];out[i].uv[1]=1-source[i].uv[1];
        memcpy(out[i].color,source[i].color,sizeof(out[i].color));
    }
}
