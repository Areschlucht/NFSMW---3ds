#ifndef BRAKE_GPU_H
#define BRAKE_GPU_H
#include "brake_mesh.h"
bool brake_gpu_init(void);
void brake_gpu_shutdown(void);
bool brake_gpu_set_mesh(const BrakeMesh *mesh, bool wireframe);
void brake_gpu_draw(float yaw, float pitch, float zoom);
#endif
