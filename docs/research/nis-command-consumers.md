# Opening NIS command meanings and original consumers

Original matching-debug DWARF event layouts identify the fields below; source
constructors supply the consumer evidence. `MwNisActionCommand.arguments_be`
starts at the first listed field, after the event hash. Values are original
big-endian words, not host structs. Extra words in CARPX argument blocks may be
padding; do not interpret them as extra parameters. The callback's source system
name identifies the CARPX actor context; actual hSimable resolution remains the
application's registry/dynamic-data job.

| Original event/hash | Initial payload fields | Original destination |
|---|---|---|
| ENISLights /5e565165 | u32 copLights, u32 headLights, u32 hSimable | IVehicle::GlareOn/GlareOff |
| ENISBrakelock /a01a259b | u32 front, u32 rear, u32 hSimable | INISCarControl::SetBrakeLock |
| ENISBurnout /6a5265b2 | float speed, u32 hSimable | INISCarControl::SetBurnout |
| ENISNitro /eb348f62 | u32 on, u32 hSimable | INISCarEngine nitro control |
| ENISNeutralRev /00eb198b | u32 on, float throttle, float speed, u32 hSimable | original engine control; complete effect consumer not yet connected |
| ENISCarPitch /a18e1896 | float pitch, float time, u32 hSimable | original animated suspension pitch |
| ENISCarRoll /3081837d | float roll, float time, u32 hSimable | original animated suspension roll |
| ENISCarShake /fb3dad79 | float shake, float rate, float ramp, float time, u32 hSimable | original animated suspension shake |
| ENISPlayEffect /58aae7a8 | u32 effect, float positionX/Y/Z, float magnitudeX/Y/Z | original named effect request; not a generic smoke count |
| ENISTimeOfDay | float timeOfDay, float updateRate, float sunAzimuth, float timeOfDayOvercast | original world lighting request; complete native effect not yet connected |
| EDDaySpeech /a67e8286 | no declared fields | story speech event; this name alone does not identify a decoded audio stream |

ENISLights constructor801DC66C searches the target, gets IVehicle through
interface handle80042A2C, then turns **mask0x7000** on/off for cop lights and
**mask7** on/off for headlights. Actual virtual slots148/150 map through
`_vt.8PVehicle.8IVehicle` to `PVehicle::GlareOn`80215354 and
`PVehicle::GlareOff`80215364. This proves glare/effects flags; it does not prove
that missing lamp geometry/materials are restored by a boolean alone.

Actual IntroNisDD `ActionCar1` and `ActionCar2` begin with copLights0/headLights1;
`ActionCop1` and `ActionCop2` begin with copLights1/headLights0. These are genuine
source timed0 commands, suitable for a stateful native glare renderer once the
matching actor/model binding exists.

ENISBurnout constructor801DB058 gets INISCarControl through handle80050110 and
passes the source float to its SetBurnout method. Concrete
`SuspensionSpline::SetBurnout`802694D0 stores this in mBurnout. Thus the source
value30 seen in opening scenes is a suspension/burnout parameter; it is not a
particle-emitter count. ENISBrakelock801DADF4 resolves the same interface and
passes each source integer as a boolean to SetBrakeLock. ENISNitro801DCC90 gets
INISCarEngine through handle801F21C8 and passes boolean on to its method+20.

These are documented source contracts, not claims that sound, smoke, glare,
animated suspension, nitrous or named particle assets have already been rendered
by the native application. The cached cinema callback delivers these original
commands for their actual consumers rather than inventing substitutes.
