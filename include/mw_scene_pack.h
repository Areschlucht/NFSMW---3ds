#ifndef MW_SCENE_PACK_H
#define MW_SCENE_PACK_H
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
enum { MW_SCENE_PACK_MODEL=1,MW_SCENE_PACK_SECTION=2,MW_SCENE_PACK_TEXTURE=3,
       MW_SCENE_PACK_MAX_ENTRIES=32768,MW_SCENE_PACK_INDEX_STRIDE=64 };
typedef enum { MW_SCENE_PACK_OK=0,MW_SCENE_PACK_INVALID,MW_SCENE_PACK_IO,
    MW_SCENE_PACK_MEMORY,MW_SCENE_PACK_NOT_FOUND,MW_SCENE_PACK_CAPACITY,
    MW_SCENE_PACK_CRC } MwScenePackResult;
typedef struct {
    FILE *file;
    uint8_t *index;
    uint32_t count,file_bytes;
    uint8_t source_sha256[32],manifest_sha256[32];
} MwScenePack;
typedef struct {
    uint32_t kind,id,offset,bytes,crc32;
    uint8_t identity[32];
} MwScenePackEntry;
/* Open requires a zero/closed output. Owns one FILE and at most index_budget
   normal-heap bytes. Header/index validated before success; payload CRC is lazy.
   Source/manifest hashes bind provenance, not GPU allocation or readiness. */
MwScenePackResult mw_scene_pack_open(MwScenePack *,const char *path,size_t index_budget);
void mw_scene_pack_close(MwScenePack *);
/* MODEL/SECTION identity is ignored; TEXTURE requires all32 identity bytes. */
MwScenePackResult mw_scene_pack_find(const MwScenePack *,uint32_t kind,uint32_t id,
    const uint8_t identity[32],MwScenePackEntry *);
/* NULL destination with capacity0 queries size without loading/checking payload.
   Full read checks entry CRC; discard destination after any error. On success
   *bytes is payload size. This blocking FILE interface is single-thread owned. */
MwScenePackResult mw_scene_pack_read(MwScenePack *,uint32_t kind,uint32_t id,
    const uint8_t identity[32],void *destination,size_t capacity,size_t *bytes);
#endif
