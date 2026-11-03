#ifndef PERF_VERTEX20_COMPONENTS_H
#define PERF_VERTEX20_COMPONENTS_H
#include "world_vertex.h"
#include <stdint.h>
typedef struct { float position[3];int16_t uv[2];float color[4]; } PerfVertexUV32;
typedef struct { float position[3],uv[2];uint8_t color[4]; } PerfVertexColor24;
/* Research codecs only. Each pack rejects any changed source bit on CPU
   reconstruction. Failure can leave a converted prefix: discard the whole
   candidate output. Unpack requires valid nonoverlapping buffers and count. */
bool perf_vertex20_uv32_pack(PerfVertexUV32 *out,const WorldVertex *source,size_t count);
void perf_vertex20_uv32_unpack(WorldVertex *out,const PerfVertexUV32 *source,size_t count);
bool perf_vertex20_color24_pack(PerfVertexColor24 *out,const WorldVertex *source,size_t count);
void perf_vertex20_color24_unpack(WorldVertex *out,const PerfVertexColor24 *source,size_t count);
#endif
