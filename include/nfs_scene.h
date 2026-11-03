#ifndef NFS_SCENE_H
#define NFS_SCENE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define NFS_MAX_TEXTURES 128
typedef struct { float position[3],normal[3],uv[2],color[4]; } NfsVertex;
/* Texture flags: bit 0 blended pass, bit 1 alpha pixels, bit 2 SRCALPHA/ONE additive. */
typedef struct { uint32_t key,width,height,flags; } NfsTexture;
typedef struct { uint32_t first,count,texture,reserved; } NfsBatch;
typedef struct {
    uint32_t vertex_count,batch_count,texture_count;
    NfsVertex *vertices;
    NfsBatch *batches;
    NfsTexture *textures;
} NfsScene;
bool nfs_scene_decode(const uint8_t *data,size_t size,NfsScene *out);
void nfs_scene_free(NfsScene *scene);
#endif
