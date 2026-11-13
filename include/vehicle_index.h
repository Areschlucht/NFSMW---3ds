#ifndef VEHICLE_INDEX_H
#define VEHICLE_INDEX_H
#include "nfs_scene.h"

typedef struct {
    NfsVertex *vertices;
    uint16_t *indices;
    uint32_t vertex_count,index_count;
} VehicleIndexedVertices;
typedef enum {
    VEHICLE_INDEX_OK,
    VEHICLE_INDEX_INVALID,
    VEHICLE_INDEX_OVERFLOW,
    VEHICLE_INDEX_ALLOCATION,
    VEHICLE_INDEX_BUDGET
} VehicleIndexResult;
/* Startup-only exact48-byte indexing. First occurrence determines unique order;
   index order and every original batch range stay unchanged. Finite triangle
   lists of1..200000 vertices are accepted, with at most65535 unique vertices.
   No float canonicalization, quantization, UV/material/wheel regrouping occurs.
   Every failure leaves out unchanged. Free an earlier successful result before
   reuse; successful output owns ordinary malloc buffers, not GPU memory. Copy
   to flushed linear memory before C3D_DrawElements. */
VehicleIndexResult vehicle_index_encode(const NfsVertex *,size_t,VehicleIndexedVertices *out);
void vehicle_index_free(VehicleIndexedVertices *);
#endif
