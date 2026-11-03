#ifndef STREAMED_WORLD_H
#define STREAMED_WORLD_H
#include <citro3d.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct StreamedWorld StreamedWorld;
typedef enum {
    STREAMED_WORLD_OK,STREAMED_WORLD_INVALID,STREAMED_WORLD_IO,
    STREAMED_WORLD_FORMAT,STREAMED_WORLD_BUDGET,STREAMED_WORLD_CAPACITY,
    STREAMED_WORLD_MISSING,STREAMED_WORLD_AMBIGUOUS,STREAMED_WORLD_NEAREST_REQUIRED
} StreamedWorldResult;
typedef enum { STREAMED_WORLD_MODEL=1,STREAMED_WORLD_SECTION=2,STREAMED_WORLD_TEXTURE=3 } StreamedWorldAssetKind;
/* Blocking bounded IO. Query required size with destinationNULL/capacity0;
   returnOK and set bytes. MODEL/SECTION archive keys ignore identity; backend
   still verifies model identity after reading. TEXTURE identity is mandatory.
   The provider must not retain destination or allocate an entire archive. */
typedef StreamedWorldResult (*StreamedWorldReadAsset)(void *context,StreamedWorldAssetKind kind,
    uint32_t id,const uint8_t identity[32],void *destination,size_t capacity,size_t *bytes);
typedef enum { STREAMED_WORLD_REFERENCE_SLOT0,STREAMED_WORLD_SOURCE_LOD_COMPONENTS } StreamedWorldLodMode;
typedef struct {
    const char *asset_root; /* Directory fallback; optional with read_asset. */
    const char *metadata_path; /* Separate WST1 file, never a whole game stream. */
    StreamedWorldReadAsset read_asset;
    void *read_context;
    uint32_t normal_bytes,linear_bytes,scratch_bytes;
    uint32_t cache_entries,object_capacity,run_capacity;
    float render_scale; /* Immutable for this renderer/GPU cache lifetime. */
    StreamedWorldLodMode lod_mode;
    uint8_t alpha_reference; /* Original initialized source value40. */
    bool comparison_zero_transparent_rgb; /* OFFLINE Tex3DS reference only; productionfalse. */
} StreamedWorldConfig;
typedef struct {
    double camera_viewer[3]; /* Absolute unscaled VIEWER=(sourceX,sourceZ,-sourceY). */
    float forward_viewer[3],up_viewer[3]; /* Unit camera basis; nonparallel. */
    float vertical_fov_radians,aspect,near_world,far_world;
    uint16_t original_fov_turn;
    int32_t original_view_state;
    uint32_t original_context_flags;
} StreamedWorldView;
typedef struct {
    uint32_t region,source_sections,visible_instances,draw_runs,triangles;
    uint32_t resident_models,resident_textures,normal_used,normal_budget;
    uint32_t linear_used,linear_budget,scratch_bytes;
    uint32_t asset_queries,asset_reads,model_uploads,texture_uploads,arena_allocations;
    StreamedWorldResult result;
    char detail[160];
} StreamedWorldStats;

/* Root owns C3D_Init/Fini, targets, shader and frame lifecycle. This constructor
   allocates one bounded normal arena and separate bounded scratch window. */
StreamedWorldResult streamed_world_create(const StreamedWorldConfig *,StreamedWorld **);
/* Call OUTSIDE any active C3D frame. Performs FrameSync, source-region selection,
   instancefrustum/LOD and blocking staged uploads. Failure retains the previous
   complete draw/section set. Root must roll camera/physics back coherently on
   failure; this first backend does not pretend blocking IO is asynchronous. */
StreamedWorldResult streamed_world_prepare(StreamedWorld *,float render_source_x,float render_source_y,const StreamedWorldView *);
/* Call INSIDE an active frame with the root's existing floatRGB36 world shader.
   It changes GPU bindings/state; root rebinds its car/UI program afterwards.
   Projection belongs to the same camera used for successful prepare. */
void streamed_world_draw(StreamedWorld *,shaderProgram_s *,int projection_location,int model_view_location,const C3D_Mtx *projection);
void streamed_world_stats(const StreamedWorld *,StreamedWorldStats *);
void streamed_world_destroy(StreamedWorld *); /* Outside frame, before C3D_Fini. */
#endif
