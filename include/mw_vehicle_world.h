#ifndef MW_VEHICLE_WORLD_H
#define MW_VEHICLE_WORLD_H
#include <stdbool.h>
#include "mw_original_rigid_body.h"
#include "mw_body_collision_shapes.h"
#define MW_VEHICLE_WORLD_MAX_PRIMITIVES 32
/* Matching original Dynamics::Collision::Geometry layout, 176 bytes.
   Native Y-up world; position/normal/extent rows retain original homogeneous W. */
typedef struct {
    float position[4],normal[3][4],extent[3][4];
    float collision_point[4],collision_normal[4],dimension[3];
    uint16_t shape,penetrates_other;
    float delta[3],overlap;
} MwVehicleWorldGeometry;
typedef struct {
    MwBodyCollisionCompound compound;
    MwBodyCollisionShape primitives[MW_VEHICLE_WORLD_MAX_PRIMITIVES];
    float previous_position[MW_VEHICLE_WORLD_MAX_PRIMITIVES][3];
    unsigned count;
    bool prepared;
} MwVehicleWorldActor;
/* Borrowed original .bnd package and source COLLISION_BOX_PAD. Native caller
   must keep data alive. Rejects an unavailable root dispatch instead of making
   a visual-bounds substitute. No output mutation on failure. */
int mw_vehicle_world_actor_open(const void *data,size_t bytes,uint32_t model_key,
    const float source_box_pad[3],MwVehicleWorldActor *actor);
/* Original Primitive::Prepare, run BEFORE body integration each SimStart. */
bool mw_vehicle_world_prepare(MwVehicleWorldActor *,const MwOriginalRigidBody *);
/* Original Primitive::SetCollision and Geometry constructor. This produces
   geometry, not a world intersection or response. Original unwritten padding
   starts at zero in this API and is not an independent physical field. */
bool mw_vehicle_world_geometry(const MwVehicleWorldActor *,unsigned primitive,
    const MwOriginalRigidBody *,MwVehicleWorldGeometry *);
/* Exact source box/box and sphere/box narrow phase. The output may alias an
   input; alias identity affects original normal orientation. Returns 0/1 or
   -1 for unsupported inputs, preserving output on error. */
int mw_vehicle_world_intersection(const MwVehicleWorldGeometry *,
    const MwVehicleWorldGeometry *,MwVehicleWorldGeometry *);
#endif
