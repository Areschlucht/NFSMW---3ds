#ifndef WORLD_COLLISION_QUERY_H
#define WORLD_COLLISION_QUERY_H
#include <stddef.h>
#include <stdint.h>
/* Narrow original 0x802EF290 local-space point/strip candidate query.
 * Not a ray cast, suspension solver, rigid-body response, or streaming manager.
 * Caller passes validated BE strip bytes (8 bytes/vertex) and node center.
 * Returns 1 hit, 0 no candidate, -1 malformed input. No allocation.
 */
typedef struct {
    float vertices[3][3];
    uint8_t material_index;
    uint8_t attributes;
    uint16_t triangle_index;
} WorldCollisionCandidate;
int world_collision_strip_candidate(const unsigned char *strip, size_t bytes,
    const float center[3], const float point[3], uint32_t exclusion_mask,
    WorldCollisionCandidate *result);
typedef struct {
    float point[3];
    uint16_t wall_index;
    uint8_t material_index;
    uint8_t flags;
} WorldCollisionWallHit;
/* Original wall-bank segment selection (0x802F3E6C through 0x802F4000),
 * in collision instance LOCAL coordinates. Closest intersected vertical wall,
 * strict interior height test. Does not return body forces or resolve materials.
 * Source CI transform/activation and load-time flag mutations belong to caller.
 */
int world_collision_wall_bank_segment(const unsigned char *asset, size_t bytes,
    const float start[3], const float end[3], uint32_t exclusion_mask,
    WorldCollisionWallHit *result);
typedef struct {
    WorldCollisionCandidate triangle;
    float height_gap;
    uint16_t node_index;
} WorldCollisionMeshHit;
/* Original mesh point-below query (0x802F0364), observed CI flags&3==0 path.
 * Local coordinates, source CI half extents, nearest strictly positive gap.
 * Uses the original functional Gekko two-refinement sqrt stage for normalization.
 * Caller handles CI transforms/activation and resolves original material hashes.
 */
int world_collision_mesh_point_below(const unsigned char *asset, size_t bytes,
    const float point[3], const float extents[3], uint32_t exclusion_mask,
    WorldCollisionMeshHit *result);
/* Upward query-plane normal, including original0.9999 Y clamp. This is the
 * ground query's normal producer; wheel-force normal linkage is separate.
 */
int world_collision_ground_query_normal(const float triangle[3][3],float normal[3]);
/* Original wheel ground-plane output80308C18..80308D88. Use WORLD triangle
 * floats and the WORLD query point: xyz=upward query-clamped normal,
 * w=dot(triangleA-query,xyz), negative when above an upward surface.
 * This is a query-relative signed projection, not an absolute plane D.
 */
int world_collision_ground_contact_plane(const float triangle_world[3][3],
    const float query_world[3],float plane[4]);
/* Original selected-wall normal assembly (0x802F4184..0x802F420C).
 * All points are native WORLD floats after original CI inverse transform.
 * Keep stored local inverse length: original code also uses it after transform.
 * Faces query start; no rigid-body impulse or velocity response is implied.
 */
int world_collision_wall_contact_normal(const float query_start[3],
    const float contact_point[3], const float wall_a[3], const float wall_b[3],
    float inverse_local_horizontal_length, float normal[3]);
#endif
