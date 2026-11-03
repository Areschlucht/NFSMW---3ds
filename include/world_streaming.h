#ifndef WORLD_STREAMING_H
#define WORLD_STREAMING_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define WORLD_STREAMING_MAX_SECTIONS 1024
#define WORLD_STREAMING_MAX_DEPENDENCIES 512

typedef enum {
    WORLD_STREAMING_OK, WORLD_STREAMING_INVALID, WORLD_STREAMING_CAPACITY,
    WORLD_STREAMING_NEAREST_REQUIRED, WORLD_STREAMING_BUDGET,
    WORLD_STREAMING_NOT_READY
} WorldStreamingResult;

/* Borrowed immutable WST1 bytes: caller owns their lifetime. Metadata is ~100KB,
   not the complete original stream, and contains no decoded vertex arrays. */
typedef struct {
    const uint8_t *data;
    size_t size;
    uint32_t section_count,polygon_count,dependency_count,point_count,ref_count;
    uint32_t sections,polygons,dependencies,points,refs,stream_bytes;
    uint16_t span;
} WorldStreamingDatabase;
typedef struct {
    uint16_t order[WORLD_STREAMING_MAX_DEPENDENCIES];
    uint16_t count;
} WorldStreamingSelector;
typedef struct { uint16_t id; uint32_t offset,bytes; } WorldStreamingSection;

WorldStreamingResult world_streaming_open(const void *bytes,size_t size,WorldStreamingDatabase *db);
void world_streaming_selector_init(const WorldStreamingDatabase *db,WorldStreamingSelector *selector);
/* Original RENDER-SOURCE horizontal(X,Y), not collision-native(x,z), not
   scene-normalized/navigation coordinates. Inputs=(viewerWorld.x,-viewerWorld.z)
   =(collisionNative.z,-collisionNative.x), before scene origin/scale.
   Stateful original contained-region branch only. Outside all dependency polygons
   returns NEAREST_REQUIRED; retain the last complete resident set in that case. */
WorldStreamingResult world_streaming_select(const WorldStreamingDatabase *db,
    WorldStreamingSelector *selector,float render_source_x,float render_source_y,uint16_t *dependency_index);
bool world_streaming_section(const WorldStreamingDatabase *db,uint16_t id,WorldStreamingSection *section);
/* Exact-index request gather in normal mode, not a visibility mask. Original base
   banks2500,2400,2600 precede up to two viewpoint dependency lists. Absent logical
   IDs are skipped, as in original802BACA4. Dynamic special-group changes and the
   original optional ID-remap mode are not applied. No partial output on capacity
   failure; output_count reports the required count. */
WorldStreamingResult world_streaming_plan(const WorldStreamingDatabase *db,
    const uint16_t *dependency_indices,size_t viewpoint_count,
    uint16_t *source_section_ids,size_t capacity,size_t *output_count);

typedef enum { WORLD_STREAMING_UNLOADED,WORLD_STREAMING_LOADING,WORLD_STREAMING_READY }
    WorldStreamingReadiness;
typedef struct {
    uint32_t charged_bytes[WORLD_STREAMING_MAX_SECTIONS];
    uint8_t state[WORLD_STREAMING_MAX_SECTIONS];
    uint32_t used_bytes,budget_bytes;
} WorldStreamingResidency;
/* Explicit application budget, AFTER graphics/car/UI reservations. Raw source
   bytes are NOT the converted allocation cost or a proxy for linear RAM space.
   This tracks one application-defined pool; create separate instances for normal
   and linear pools if both are needed. No allocation, IO, implicit eviction, or
   clock/cache changes occur in this module. Calls and asynchronous IO completion
   notifications must be serialized by the caller (normally on the main thread). */
void world_streaming_residency_init(WorldStreamingResidency *state,uint32_t budget_bytes);
WorldStreamingResult world_streaming_begin(const WorldStreamingDatabase *db,
    WorldStreamingResidency *state,uint16_t id,uint32_t actual_allocation_bytes);
WorldStreamingResult world_streaming_ready(const WorldStreamingDatabase *db,
    WorldStreamingResidency *state,uint16_t id);
/* Caller must release GPU, collision and texture references before this bookkeeping
   release; cancellation/failed decode also releases reserved loading bytes here. */
WorldStreamingResult world_streaming_release(const WorldStreamingDatabase *db,
    WorldStreamingResidency *state,uint16_t id);
bool world_streaming_is_ready(const WorldStreamingDatabase *db,
    const WorldStreamingResidency *state,uint16_t id);
#endif
