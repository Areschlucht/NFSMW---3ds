#ifndef WORLD_INDEX_H
#define WORLD_INDEX_H
#include "world_vertex.h"
#include <stdint.h>

/* Exact startup encoder for indexed world rendering. No triangle reordering,
   quantization, UV changes beyond world_vertex_pack, or material regrouping. */
typedef struct {
    WorldVertex *vertices;
    uint16_t *indices;
    uint32_t vertex_count,index_count;
} WorldIndexedVertices;
typedef enum {
    WORLD_INDEX_OK,
    WORLD_INDEX_INVALID,
    WORLD_INDEX_OVERFLOW,
    WORLD_INDEX_ALLOCATION,
    WORLD_INDEX_BUDGET
} WorldIndexResult;

/* Free any previous result before reuse. Every failure leaves it empty, so a caller can retain
   the existing DrawArrays path on overflow/allocation/probe-budget failure. CPU allocations
   returned here must be copied to flushed GPU-accessible linear buffers before
   C3D_DrawElements. These malloc pointers are not GPU buffers. */
WorldIndexResult world_index_encode(const NfsVertex *source,size_t count,WorldIndexedVertices *out);
void world_index_free(WorldIndexedVertices *world);
#endif
