#ifndef PERF_VERTEX20_H
#define PERF_VERTEX20_H
#include "world_vertex.h"
#include <stdint.h>
typedef struct { float position[3];int16_t uv[2];uint8_t color[4]; } PerfVertex20;
/* Stores original, unflipped Q12 UVs. Returns false unless CPU reconstruction
   matches every source byte, including signed zero. A failure leaves earlier
   output records written; discard the entire candidate buffer in that case. */
bool perf_vertex20_pack(PerfVertex20 *out,const WorldVertex *source,size_t count);
void perf_vertex20_unpack(WorldVertex *out,const PerfVertex20 *source,size_t count);
#endif
