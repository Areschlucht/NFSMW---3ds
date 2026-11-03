#ifndef ROAD_CONTACT_H
#define ROAD_CONTACT_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "driving_controller.h"
typedef struct { float p[3][3],minx,maxx,minz,maxz,denominator; } RoadTriangle;
typedef struct {
    float minx,minz,cell;
    uint32_t columns,rows,references;
    uint32_t *offsets,*indices;
} RoadGrid;
typedef struct {
    uint32_t count;
    float scale,car_half_extent,origin[3],spawn[3],heading;
    RoadTriangle *triangles;
    RoadGrid *grid;
} RoadWorld;
bool road_build_grid(RoadWorld *world);
bool road_decode(const uint8_t *data,size_t size,RoadWorld *out);
void road_free(RoadWorld *world);
bool road_height(const RoadWorld *world,float x,float z,float reference,float *height);
bool road_surface(const RoadWorld *world,float x,float z,float reference,float *height,float normal[3]);
bool road_drive_step(const RoadWorld *world,DriveState *car,float *height,DriveInput input,float seconds);
#endif
