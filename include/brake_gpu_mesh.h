#ifndef BRAKE_GPU_MESH_H
#define BRAKE_GPU_MESH_H
#include "brake_mesh.h"
enum { BRAKE_GPU_MAX_VERTICES=BRAKE_MAX_FACES*18 };
typedef struct { float position[3]; float normal[3]; } BrakeGpuVertex;
/* Prepare normalized, expanded triangle/line vertices without graphics APIs. */
size_t brake_gpu_mesh(const BrakeMesh *mesh, bool wireframe, BrakeGpuVertex *vertices, size_t capacity);
#endif
