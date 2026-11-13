#ifndef WORLD_STREAMING_SCENE_H
#define WORLD_STREAMING_SCENE_H
#include "world_vertex.h"
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef enum {
    WORLD_SCENE_OK,WORLD_SCENE_INVALID,WORLD_SCENE_CAPACITY,WORLD_SCENE_BUDGET,
    WORLD_SCENE_MISSING,WORLD_SCENE_AMBIGUOUS,WORLD_SCENE_STATE
} WorldStreamingSceneResult;
typedef struct {
    const uint8_t *data;size_t size;
    uint32_t hash,vertex_count,index_count,batch_count;
    uint32_t vertices,indices,batches,night_alpha,source_header;
    uint32_t declared_triangles,emitted_triangles;
    float bounds[6],header_matrix[16];
} WorldStreamingSceneModel;
typedef struct {
    uint32_t first_index,index_count,texture_hash;
    const uint8_t *original_descriptor,*original_material_reference;
} WorldStreamingSceneBatch;
typedef struct {
    const uint8_t *data,*rgba;size_t size;
    uint32_t hash,width,height,rgba_bytes,quality,alpha_test,blend,native_format;
    uint32_t source_width,source_height;
    const uint8_t *identity;
} WorldStreamingSceneTexture;
typedef struct {
    const uint8_t *data;size_t size;
    uint32_t id,model_count,texture_count,instance_count,models,textures,instances;
} WorldStreamingSceneSection;
typedef struct {
    uint32_t hash;const uint8_t *identity;
} WorldStreamingSceneBinding;
typedef struct {
    uint32_t source_instance_offset,source_object_offset;
    uint32_t original_slots[4],bound_slots[4];
    float bounds[6],translation[3],matrix[9];
    const uint8_t *original_instance,*original_object;
} WorldStreamingSceneInstance;

/* All views borrow caller-owned bytes. No heap allocation or GPU calls occur.
   A WSM1 disk20 vertex is NOT a GPU20 vertex: expand it to WorldVertex36 below.
   Source coordinates and header matrix remain unmodified. Header matrix is not
   implicitly applied: original TRN geometry is already baked. Explicit source
   emptyflag1 models have allcounts0 and retain authored FLT_MAX/-FLT_MAX empty
   bounds and original LOD header; they allocate no GPU geometry. */
WorldStreamingSceneResult world_streaming_scene_model_open(const void *,size_t,WorldStreamingSceneModel *);
WorldStreamingSceneResult world_streaming_scene_model_expand(const WorldStreamingSceneModel *,WorldVertex *,size_t,uint16_t *,size_t);
/* Explicit render-only local rebase. Physics/WST/instance metadata stay absolute
   unscaled. Root composes CPU camera-relative instance translation; never ask
   PICA to subtract two city-sized coordinates. UV/RGB expansion stays identical. */
WorldStreamingSceneResult world_streaming_scene_model_expand_rebased(const WorldStreamingSceneModel *,const float origin[3],float scale,WorldVertex *,size_t,uint16_t *,size_t);
bool world_streaming_scene_model_batch(const WorldStreamingSceneModel *,uint32_t,WorldStreamingSceneBatch *);
WorldStreamingSceneResult world_streaming_scene_texture_open(const void *,size_t,WorldStreamingSceneTexture *);
/* Raw source RGBA is retained. Alpha test/blend are source state, not inferred
   from pixel alpha; original fourth VERTEX byte is a separate model sidecar. */
WorldStreamingSceneResult world_streaming_scene_section_open(const void *,size_t,WorldStreamingSceneSection *);
bool world_streaming_scene_model_binding(const WorldStreamingSceneSection *,uint32_t,WorldStreamingSceneBinding *);
bool world_streaming_scene_texture_binding(const WorldStreamingSceneSection *,uint32_t,WorldStreamingSceneBinding *);
bool world_streaming_scene_instance(const WorldStreamingSceneSection *,uint32_t,WorldStreamingSceneInstance *);
/* Apply source absolute flag transition to a DECODED COPY. Source bytes and
   bounds/translation remain immutable. Eligible0x400 flips wrap int16 lanes. */
bool world_streaming_scene_instance_transform(WorldStreamingSceneInstance *,uint32_t effective_flags);

typedef enum { WORLD_SCENE_MODEL=1,WORLD_SCENE_TEXTURE=2 } WorldStreamingSceneKind;
typedef struct {
    uint32_t hash,normal_bytes,linear_bytes,generation;
    uint32_t references,pins;
    uint8_t identity[32],kind,state;
    void *resource;
} WorldStreamingSceneCacheEntry;
typedef struct {
    WorldStreamingSceneCacheEntry *entries;size_t capacity;
    uint32_t normal_budget,linear_budget,normal_used,linear_used,next_generation;
} WorldStreamingSceneCache;
/* Caller supplies the bounded table (512 textures supported; no fixed128 cap).
   Costs are ACTUAL padded allocations including retained CPU assets, not raw
   file size guesses. Unknown all-zero costs are rejected. Resource ownership,
   uploads/fences and serialized completion calls remain with the caller. */
void world_streaming_scene_cache_init(WorldStreamingSceneCache *,WorldStreamingSceneCacheEntry *,size_t,uint32_t,uint32_t);
WorldStreamingSceneResult world_streaming_scene_cache_acquire(WorldStreamingSceneCache *,WorldStreamingSceneKind,uint32_t,const uint8_t[32],uint32_t,uint32_t,size_t *,uint32_t *generation);
/* Completion must present the acquire generation. Pin while IO/upload is in
   flight; cancellation releases that pin only after the producer has stopped. */
WorldStreamingSceneResult world_streaming_scene_cache_ready(WorldStreamingSceneCache *,size_t,uint32_t generation,void *);
WorldStreamingSceneResult world_streaming_scene_cache_release(WorldStreamingSceneCache *,size_t);
/* O(1) retain after an exact, generation-checked immutable resource lookup. */
WorldStreamingSceneResult world_streaming_scene_cache_retain(WorldStreamingSceneCache *,size_t,uint32_t generation);
WorldStreamingSceneResult world_streaming_scene_cache_pin(WorldStreamingSceneCache *,size_t,bool);
/* No implicit eviction. Caller frees the returned resource after ensuring GPU
   ownership is released. Eviction is legal only with zero references AND pins. */
WorldStreamingSceneResult world_streaming_scene_cache_evict(WorldStreamingSceneCache *,size_t,void **);
/* Hash-only binding must fail if two active texture identities differ. Model
   immutable sharing does NOT imply globally identical texture/material state. */
WorldStreamingSceneResult world_streaming_scene_cache_find(const WorldStreamingSceneCache *,WorldStreamingSceneKind,uint32_t,size_t *);
#endif
