#ifndef PERF_WORLD_INDEX_H
#define PERF_WORLD_INDEX_H
#include "world_vertex.h"
#include <stdint.h>

/* Review prototype, not wired into the renderer. No triangle reordering,
   quantization, UV changes beyond world_vertex_pack, or material regrouping. */
typedef struct {
    WorldVertex *vertices;
    uint16_t *indices;
    uint32_t vertex_count,index_count;
} PerfIndexedWorld;
typedef enum {
    PERF_INDEX_OK,
    PERF_INDEX_INVALID,
    PERF_INDEX_OVERFLOW,
    PERF_INDEX_ALLOCATION,
    PERF_INDEX_BUDGET
} PerfIndexResult;

/* Output must be empty. Every failure leaves it empty, so a caller can retain
   the existing DrawArrays path on overflow/allocation/probe-budget failure. CPU allocations
   returned here must be copied to flushed GPU-accessible linear buffers before
   C3D_DrawElements. These malloc pointers are not GPU buffers. */
PerfIndexResult perf_world_index(const NfsVertex *source,size_t count,PerfIndexedWorld *out);
void perf_world_index_free(PerfIndexedWorld *world);
#endif
