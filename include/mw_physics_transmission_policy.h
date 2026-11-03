#ifndef MW_PHYSICS_TRANSMISSION_POLICY_H
#define MW_PHYSICS_TRANSMISSION_POLICY_H
#include "mw_physics_transmission.h"
enum { MW_PHYSICS_TRANSMISSION_MAX_GEARS=10 };
typedef struct {
    float low_boost,high_boost,vacuum,spool;
} MwPhysicsTransmissionInduction;
typedef struct {
    float up[MW_PHYSICS_TRANSMISSION_MAX_GEARS];
    float down[MW_PHYSICS_TRANSMISSION_MAX_GEARS];
    size_t count;
} MwPhysicsTransmissionShiftTables;
/* Original80223DA8 with optional tuning/output argumentsNULL, not its timed
 * spool producer. Inputs are RPM and bounded induction amount, in that order. */
float mw_physics_transmission_induction_raw(const MwPhysicsEngineCurve *,
    const MwPhysicsTransmissionInduction *,float rpm,float amount);
/* Original80224CB8 startup gear-table generation. Caller passes real database
 * engine/induction/ratio data; no guessed optimal-shift RPM is introduced. */
bool mw_physics_transmission_shift_tables(const MwPhysicsEngineCurve *,
    const MwPhysicsTransmissionInduction *,const float *ratios,size_t count,
    MwPhysicsTransmissionShiftTables *);
/* Original80255DE0 gear request classification:0 none,1 down,2 up. This does
 * not perform its caller's manual-input/inhibit/airborne-policy gates. */
unsigned mw_physics_transmission_shift_request(const MwPhysicsTransmissionShiftTables *,
    const float *ratios,size_t count,unsigned gear_slot,float rpm,float throttle,float idle_rpm);
/* Original802247EC peak induction-adjusted TORQUE sample and its RPM.
 * Engine initialization stores this RPM at+194 for launch clutch attenuation.
 * This is not peak horsepower; ties retain the first sample. Optional original
 * tuning is NULL, matching EngineRacer startup80255A8C. */
bool mw_physics_transmission_peak_torque(const MwPhysicsEngineCurve *,
    const MwPhysicsTransmissionInduction *,float *raw_torque,float *rpm);
#endif
