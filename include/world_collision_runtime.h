#ifndef WORLD_COLLISION_RUNTIME_H
#define WORLD_COLLISION_RUNTIME_H
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include "world_collision_query.h"
#define WORLD_COLLISION_MAX_PACKAGES 512
#define WORLD_COLLISION_MAX_ASSOCIATIONS 1024
/* Caller owns context and geometry/cache arena; queries allocate nothing and
 * perform no I/O. libc stdio owns its ordinary FILE/buffering state.
 * Zero-initialize before first open; close before reopening.
 * Keep context static/heap: directory arrays are about29KiB.
 */
enum { WORLD_COLLISION_CORRUPT=-1,WORLD_COLLISION_IO=-2,WORLD_COLLISION_BUDGET=-3,
       WORLD_COLLISION_NOT_READY=-4,WORLD_COLLISION_INVALID=-5 };
typedef struct { uint32_t id,offset,bytes,instances,crc,source_offset,source_bytes; } WorldCollisionPackageIndex;
typedef struct { uint16_t section,index;uint32_t source_offset; } WorldCollisionAssociation;
typedef struct { uint16_t index,section;uint32_t arena_offset,source_offset; } WorldCollisionLoaded;
typedef struct {
    FILE *file;
    unsigned char *arena;
    size_t arena_capacity,arena_used;
    uint32_t file_bytes,package_count,association_count,active_count;
    int ready;
    unsigned char source_sha256[32];
    WorldCollisionPackageIndex packages[WORLD_COLLISION_MAX_PACKAGES];
    WorldCollisionAssociation associations[WORLD_COLLISION_MAX_ASSOCIATIONS];
    WorldCollisionLoaded active[WORLD_COLLISION_MAX_PACKAGES];
} WorldCollisionRuntime;
typedef struct {
    size_t required_bytes,required_read_bytes;
    uint32_t unique_packages,sections_without_collision,retained_packages;
} WorldCollisionAdmission;
typedef struct {
    float point_native[3],normal_native[3];
    float triangle_native[3][3]; /* ground only; wall leaves zero */
    float height_gap,distance_squared;
    uint32_t material_key,source_ci_offset,source_asset_offset;
    uint16_t section_id,collision_id,asset_index,primitive_index,node_index,instance_flags;
    uint8_t material_index,primitive_flags,strip_flags,kind; /* kind1 ground,2 wall */
} WorldCollisionContact;
/* Open validates version, finite counts/ranges and exact file length.
 * Arena must be writable and remain alive until close; source asset bytes are
 * checked and original load-time0xC0 mutations applied during activation.
 */
int world_collision_runtime_open(WorldCollisionRuntime *world,const char *path,void *arena,size_t capacity);
void world_collision_runtime_close(WorldCollisionRuntime *world);
/* Pure admission leaves old ready set untouched. Unknown/noncollision stream
 * IDs have no collision association and are counted, not mapped by arithmetic.
 */
int world_collision_runtime_admit(const WorldCollisionRuntime *world,const uint16_t *source_sections,size_t count,WorldCollisionAdmission *admission);
/* Blocking load, for loading/admission phase. Unchanged packages are retained
 * with zero I/O and compacted in-place; reads only newly activated packages.
 * Budget/argument rejection preserves
 * old set; I/O/corruption failure clears readiness so stale partial data cannot
 * be queried. Root must publish render+texture+collision readiness atomically.
 * Preserve input order; duplicate collision content activates once.
 */
int world_collision_runtime_activate(WorldCollisionRuntime *world,const uint16_t *source_sections,size_t count,WorldCollisionAdmission *admission);
/* Native game world, Y up. Return1 contact,0 none,negative error. Ground is the
 * nearest STRICTLY BELOW point query. normal_native uses original query's upward
 * Y clamp (0.9999), not a proved wheel-force normal producer. Material key is
 * original on-disc hash: caller resolves actual simsurface, never invent grip.
 */
int world_collision_runtime_ground(const WorldCollisionRuntime *world,const float native_point[3],uint32_t exclusion_mask,WorldCollisionContact *contact);
int world_collision_runtime_wall(const WorldCollisionRuntime *world,const float native_start[3],const float native_end[3],uint32_t exclusion_mask,WorldCollisionContact *contact);
/* NRD1 origin is viewer WORLD=(nativeZ,nativeY,nativeX), before local subtraction.
 * Position conversion includes that origin; vectors use the same axis swap only.
 */
void world_collision_native_to_viewer(const float native[3],const float viewer_origin[3],float viewer[3]);
void world_collision_viewer_to_native(const float viewer[3],const float viewer_origin[3],float native[3]);
void world_collision_native_vector_to_viewer(const float native[3],float viewer[3]);
#endif
