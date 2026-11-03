#ifndef BRAKE_RENDER_H
#define BRAKE_RENDER_H
#include "brake_mesh.h"
enum { VIEW_WIDTH=400, VIEW_HEIGHT=240, VIEW_PIXELS=400*240, VIEW_BYTES=400*240*3 };
/* Framebuffer uses libctru's rotated, column-major BGR8 layout. */
void brake_render(const BrakeMesh *mesh, uint8_t framebuffer[VIEW_BYTES],
                  float depth[VIEW_PIXELS], float yaw, float pitch, float zoom, bool wireframe);
#endif
