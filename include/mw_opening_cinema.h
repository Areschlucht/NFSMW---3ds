#ifndef MW_OPENING_CINEMA_H
#define MW_OPENING_CINEMA_H
#include "mw_nis_director.h"
#include "mw_nis_actor.h"
#include "mw_nis_actions.h"
/* Cached original opening NIS director. Source XYZ/matrix layout throughout.
 * Slot0..7 are original VEHICLE_RACERS iteration;8..15 original police registry.
 * A slot is deliberately not labelled local player. Application supplies that
 * binding and uses its actual current IPlayer-equivalent transform for camera.
 */
enum { MW_OPENING_NIS_ACTORS=16, MW_OPENING_NIS_SYSTEMS=16 };
typedef struct {
    bool present,has_scale;
    MwNisActorCurve translation,quaternion,scale;
    float source_world[16],bond[16];
} MwOpeningNisActor;
typedef struct {
    MwNisActionSystem source;
    MwNisAction action;
    uint32_t state;
    float elapsed;
    bool running,ended;
} MwOpeningNisSystem;
typedef void (*MwOpeningNisCommand)(void *context,const char *source_system,
    const MwNisActionCommand *command);
typedef struct {
    MwNisPack cameras;
    unsigned char *camera_bytes;
    MwNisActorBank curves;
    MwNisActions actions;
    MwNisScene scene;
    MwNisTrack track;
    MwNisActionScene timing;
    MwNisDirector director;
    MwOpeningNisActor actors[MW_OPENING_NIS_ACTORS];
    MwOpeningNisSystem systems[MW_OPENING_NIS_SYSTEMS];
    float rotation[16],translation[16];
    float elapsed,previous_step,actor_frame;
    uint32_t selected_track,system_count;
    bool ready,playing,finished,failed;
} MwOpeningCinema;
/* Initialize zero; close before reuse. Performs bounded cached file loads;
 * begin/step/camera do not allocate or access files. */
bool mw_opening_cinema_open(MwOpeningCinema *,const char *camera_path,
    const char *actor_path,const char *action_path);
void mw_opening_cinema_close(MwOpeningCinema *);
/* corrected_scene_origin is actual source CAnimLocator ground-corrected origin,
 * not actor animation origin. No guessed origin or renderer axis conversion.
 * Callback receives source start-tag/timed0 commands only after all preparation
 * validates. A NULL callback leaves original effect dispatch to another owner.
 */
bool mw_opening_cinema_begin(MwOpeningCinema *,const char *scene_name,
    const float local_player_source[16],const float corrected_scene_origin[3],
    uint16_t source_heading,MwNisGround,void *ground_context,
    MwOpeningNisCommand,void *command_context);
/* Original scene/action clocks consume previous delta; actors current delta.
 * Positive, finite dt <=1 second. Pause by not stepping. Current raw source
 * poses remain separate from INISCarControl's terrain/suspension consumer:
 * do NOT render a ground+5 Bond transform as though that were final chassis.
 */
bool mw_opening_cinema_step(MwOpeningCinema *,float dt,
    MwOpeningNisCommand,void *command_context);
/* Call after advancing/applying actor transforms so LOCALplayer source matrix
 * is current. Correct source track chosen once on begin; all reference modes,
 * source FOV quantization and source roll-turn value retained. */
bool mw_opening_cinema_camera(MwOpeningCinema *,const float local_player_source[16],MwNisCamera *);
void mw_opening_cinema_invalidate_ground(MwOpeningCinema *);
#endif
