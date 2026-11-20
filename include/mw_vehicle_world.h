#ifndef MW_VEHICLE_WORLD_H
#define MW_VEHICLE_WORLD_H
#include <stdbool.h>
#include "mw_original_rigid_body.h"
#include "mw_body_collision_shapes.h"
#include "mw_body_collision_response.h"
#include "world_collision_runtime.h"
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
/* Original WCollisionMgr::Collide one-barrier construction/filter/packet.
   The caller supplies an original transformed barrier, not a line hit. Input
   geometry is updated by FindIntersection even when its orientation is rejected.
   This does not apply callback translation or rigid-body response. A flag0x10
   wall bypasses orientation rejection only when force_orientation_test=false.
   Return1 admitted contact,0 no contact,-1 invalid. Transactional on error. */
typedef struct {
    float point[3],normal[3],penetration,translation[3];
    uint32_t material_key,source_ci_offset,source_asset_offset;
    uint16_t wall_index,section_id;
} MwVehicleWorldContact;
int mw_vehicle_world_wall_contact(MwVehicleWorldGeometry *,
    const WorldCollisionBarrier *,uint32_t exclusion_mask,
    bool force_orientation_test,MwVehicleWorldContact *);
/* Original RBVehicle::ModifyCollision(SimSurface,Plane,Moment)8023C33C.
   forward and velocity are actual IRigidBody getters. The source state inertia
   is diagonal inertia, not its reciprocal. Both player/nonplayer wall branches
   zero the Y component of local CG; player branch scales inertiaY and clears
   elasticity using exact original approaching-speed/forward-normal arithmetic.
   This does not substitute OBJ_ELASTICITY for the wall branch. */
bool mw_vehicle_world_modify_collision(MwBodyCollisionState *,bool is_player,
    const float forward[3],const float velocity[3],const float normal[3],
    const float world_moment_scale[3]);
#endif
