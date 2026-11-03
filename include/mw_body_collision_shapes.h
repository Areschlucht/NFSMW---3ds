#ifndef MW_BODY_COLLISION_SHAPES_H
#define MW_BODY_COLLISION_SHAPES_H
#include <stddef.h>
#include <stdint.h>
#define MW_BODY_COLLISION_MAX_MESHES 128
/* Borrowed original aligned0x3B901 payload, still source little endian and
 * unfixed. No allocation/pointer relocation/quat normalization is performed.
 */
typedef struct {
    const unsigned char *data;
    size_t bytes;
    uint32_t model_key,bound_count,mesh_count;
    uint32_t mesh_offsets[MW_BODY_COLLISION_MAX_MESHES];
} MwBodyCollisionCompound;
typedef struct {
    float quaternion[4],center[3],half_extents[3],radius;
    uint32_t material_key,token;
    uint16_t source_flags;
    int16_t first_child;
    int8_t mesh_index;
    uint8_t child_count;
} MwBodyCollisionBound;
typedef struct {
    float quaternion[4],center[3],half_extents[3],radius;
    uint32_t material_key,token;
    uint16_t source_flags,runtime_flags,bound_index;
    uint8_t kind; /* Original1 box,2 sphere; convexmesh accessed separately. */
} MwBodyCollisionShape;
enum { MW_BODY_SHAPE_INVALID=-1,MW_BODY_SHAPE_ROOT_PATH_REQUIRED=-2,MW_BODY_SHAPE_CAPACITY=-3 };
int mw_body_collision_compound_open(const void *data,size_t bytes,uint32_t expected_model_key,MwBodyCollisionCompound *compound);
int mw_body_collision_bound(const MwBodyCollisionCompound *compound,unsigned index,MwBodyCollisionBound *bound);
int mw_body_collision_mesh_vertex(const MwBodyCollisionCompound *compound,unsigned mesh,unsigned vertex,float out[4]);
unsigned mw_body_collision_mesh_count(const MwBodyCollisionCompound *compound,unsigned mesh);
/* Original8023446C primitive dispatch and80238EF8/80238F5C argument producer.
 * Returns1 produced,0 not a primitive,negative invalid. Sphere uses exact
 * source float radius and identity quaternion; box adds original padding.
 */
int mw_body_collision_primitive(const MwBodyCollisionBound *bound,const float original_box_pad[3],MwBodyCollisionShape *shape);
/* Original detailed-child path8021E360/E430 plus body static-wall loop filtering
 *80238890..A4. Mesh pointcloud is preserved separately; it belongs to original
 *body+130 list, not body+120 box/sphere static-world traversal.
 * No partial writes on capacity failure. ROOT_PATH_REQUIRED means the detailed-child path is unavailable; original
 *root-only selection must still execute and may itself produce custom geometry.
 *This API does not silently replace that path with a car box.
 */
int mw_body_collision_static_children(const MwBodyCollisionCompound *compound,unsigned root,
    const float original_box_pad[3],MwBodyCollisionShape *shapes,size_t capacity,size_t *count);
#endif
