/* Explicit physical pvehicle key0x39dae0f8; tires=0x39dae0f8[0] brakes=0x39dae0f8[0] chassis=0x39dae0f8[0]. */
/* ATTRIBUTES SHA256 5b69c44ffcfc7013a3f24900b33617002b1f68f2484a9108daa5bfe5d72ad20c; no gameplay/spawn-selection claim. */
#include "mw_physics_contact.h"
static const MwPhysicsContactParameters mw_exported_contact_parameters={
.static_grip={0x1.0000000000000p+1f,0x1.0000000000000p+1f},
.dynamic_grip={0x1.cccccc0000000p+0f,0x1.cccccc0000000p+0f},
.grip_scale={0x1.2666660000000p+0f,0x1.3333340000000p+0f},
.brakes={{0x1.db00000000000p+8f,0x1.2c00000000000p+9f},0x1.4500000000000p+9f,{0x1.0000000000000p+0f,0x1.8000000000000p+1f}},
.calibration={0x1.0000000000000p+2f,0x1.4000000000000p+3f,0x1.3333340000000p+0f,0x1.9000000000000p+6f,0x1.4000000000000p+3f},
.lateral_curves=&mw_physics_original_lateral_curves,
.surface_lateral_grip=0x1.0000000000000p+0f,
.surface_drive_grip=0x1.0000000000000p+0f,
.surface_rolling_resistance=0x1.0000000000000p+0f,
};
