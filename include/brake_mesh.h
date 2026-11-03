#ifndef BRAKE_MESH_H
#define BRAKE_MESH_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum { BRAKE_VERTICES = 64, BRAKE_MAX_FACES = 64, BRAKE_MODELS = 4, BRAKE_SAMPLE_BYTES = 6080 };
typedef struct {
    char name[32];
    float positions[BRAKE_VERTICES][3];
    uint8_t faces[BRAKE_MAX_FACES][3];
    size_t vertex_count;
    size_t face_count;
} BrakeMesh;

typedef struct {
    BrakeMesh models[BRAKE_MODELS];
    size_t model_count;
} BrakePackage;

/* Chunk-driven decoder for supported format-0x16 brake models, not all BINs. */
bool brake_package_decode(const uint8_t *data, size_t size, BrakePackage *package);
#endif
