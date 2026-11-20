#ifndef MW_ORIGINAL_RIGID_BODY_H
#define MW_ORIGINAL_RIGID_BODY_H
#include <stdbool.h>
#include <stdint.h>
/* Explicit state for original802352E4 integration and80235220 force routing.
   Original Y-up native basis, never the viewer's X/Z exchange. Orientation and
   inverse inertia are row-major4x4; local_cg belongs to the owning body wrapper.
   Mass/inertia/basis and tick producers must be supplied from original data. */
typedef struct {
    float quaternion[4],position[3],velocity[3],angular_velocity[3];
    float orientation[16],world_inverse_inertia[16];
    float force[3],torque[3],local_cg[3],inertia[3],inverse_mass;
    uint32_t status,flags;
} MwOriginalRigidBody;
/* Original PVehicle 80212DE0 source parameters, before body construction.
   Physical extent comes from the compound collision root, never mesh bounds. */
typedef struct {
    float mass,inverse_mass,halfextent[3],inertia[3];
} MwOriginalRigidBodyParameters;
bool mw_original_rigid_body_parameters(float mass,const int16_t halfextent_mm[3],
    const float tensor_scale[3],MwOriginalRigidBodyParameters *output);
/* Original 802337F0 orientation setter, including original 80193814 matrix
   conversion and Gekko reciprocal-estimate square-root stage. */
bool mw_original_rigid_body_set_orientation(MwOriginalRigidBody *,const float matrix[16]);
/* Input torque is multiplied bydt and by the PREVIOUS inverse-inertia tensor
   in place, as the original does. Force is not cleared. The caller owns the
   separate force-reset and collision phases. Nonzero status freezes velocities.
   Failure rejects nonfinite/unsupported state without mutation. */
bool mw_original_rigid_body_integrate(MwOriginalRigidBody *,float seconds);
/* Original world point and force. Status2 refuses force. Other bodies wake;
   wake_event reports the original flags2 notification path, without calling
   the original object's external registry/event implementation. */
bool mw_original_rigid_body_add_force(MwOriginalRigidBody *,const float force[3],
    const float world_point[3],bool *wake_event);
/* Original 802350A8 / body slot 124. Adds torque before dt/inertia integration. */
bool mw_original_rigid_body_add_torque(MwOriginalRigidBody *,const float torque[3],bool *wake_event);
/* Original 80235030 / slot 114: r5 is world torque, not a world point. */
bool mw_original_rigid_body_add_wrench(MwOriginalRigidBody *,const float force[3],
    const float torque[3],bool *wake_event);
/* Original 8026724C / slot 104: direct Y position correction, no wake. */
bool mw_original_rigid_body_raise_position(MwOriginalRigidBody *,float amount);
#endif
