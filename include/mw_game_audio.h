#ifndef MW_GAME_AUDIO_H
#define MW_GAME_AUDIO_H
#include "mw_audio_stream.h"
#include "mw_movie_audio.h"
enum { MW_GAME_AUDIO_ENGINE_QUEUES=3,MW_GAME_AUDIO_ENGINE_FRAMES=512,MW_GAME_AUDIO_EFFECTS=8,MW_GAME_AUDIO_ENGINE_BYTES=2*1024*1024,MW_GAME_AUDIO_EFFECT_BYTES=512*1024 };
typedef struct {
    unsigned char *pcm;uint32_t frames,rate;MwAudioStreamInfo info;
    ndspWaveBuf wave;bool loaded;
} MwGameAudioClip;
/* Render runs only in the dedicated engine worker, never the main thread.
 * It must be bounded, allocation/fileIO-free and own its opaque synth state.
 * PCM is genuine decoded/source-granular mono audio, not generated tones. */
typedef bool (*MwGameAudioEngineRender)(void *,int16_t *,unsigned,float actual_rpm,float load);
typedef struct {
    Thread worker;LightLock lock;LightEvent wake;int16_t *pcm;
    ndspWaveBuf wave[MW_GAME_AUDIO_ENGINE_QUEUES];
    unsigned state[MW_GAME_AUDIO_ENGINE_QUEUES],serial[MW_GAME_AUDIO_ENGINE_QUEUES];
    unsigned next_render,next_queue,generation;uint32_t sample_rate;float rpm,load,rate_ratio;
    MwGameAudioEngineRender render;void *context;
    bool active,enabled,paused,stop,failed;
} MwGameAudioEngineQueue;
typedef struct {
    MwMovie music;MwMovieAudio stream;MwAudioStreamInfo music_info;
    MwGameAudioClip engine,effects[MW_GAME_AUDIO_EFFECTS];
    MwGameAudioEngineQueue engine_stream;
    bool active;
} MwGameAudio;
/* Zero initialize. Start owns NDSP/channel0 through the existing verified
 * three-buffer music worker. Channels1(engine) and2..9(effects) belong to this
 * owner only. Stop BEFORE starting movie or speech playback. No shared owner.
 * Music is an original segment, not an assertion about the PathFinder playlist.
 */
bool mw_game_audio_start(MwGameAudio *,const char *music_path);
/* Main-thread bounded queue work only, no filesystem reads. */
bool mw_game_audio_update(MwGameAudio *);
bool mw_game_audio_muted(const MwGameAudio *);
bool mw_game_audio_issued(const MwGameAudio *);
bool mw_game_audio_finished(MwGameAudio *);
void mw_game_audio_pause(MwGameAudio *,bool);
/* Releases ALL channels, waits worker completion, frees buffers and closes files.
 * Restart after yielding begins the selected source segment again. This native
 * policy must not be described as sample-exact original music resumption. */
void mw_game_audio_stop(MwGameAudio *);
/* Load at scene/model load time, never on per-frame events. Source CRCs are
 * checked before replacing a cached clip. No fake sound or resampling fallback.
 * Engine requires explicit original loop bounds and a source reference RPM;
 * an entire decoded GIN ramp is NOT a supported engine loop. */
bool mw_game_audio_load_engine(MwGameAudio *,const char *path);
bool mw_game_audio_load_effect(MwGameAudio *,unsigned slot,const char *path);
/* Siren/skid/ambience loops require actual source loop metadata; preview
 * whole-clip loops are refused. Selected loop frames are cached once. */
bool mw_game_audio_load_loop(MwGameAudio *,unsigned slot,const char *path);
void mw_game_audio_stop_effect(MwGameAudio *,unsigned slot);
/* Actual RPM must come from the engine simulation. Unknown calibration/RPM
 * refuses playback; current planar speed must not be converted to invented RPM.
 * Gain/load below is native presentation policy, not original attenuation. */
bool mw_game_audio_engine(MwGameAudio *,float actual_rpm,float gain,bool enabled);
/* Alternative channel1 owner for the original Ginsu packet renderer. A full
 * decoded RPM ramp is not looped. Input enables only genuine known engine RPM.
 * Three512-frame mono buffers bound worker/render latency and linear memory. */
bool mw_game_audio_engine_stream_start(MwGameAudio *,uint32_t sample_rate,MwGameAudioEngineRender,void *context);
bool mw_game_audio_engine_stream_input(MwGameAudio *,float actual_rpm,float load,bool enabled);
/* Main-thread source-calibrated pitch control, no I/O or allocation. */
bool mw_game_audio_engine_stream_rate(MwGameAudio *,float source_pitch_ratio);
void mw_game_audio_engine_stream_stop(MwGameAudio *);
bool mw_game_audio_effect(MwGameAudio *,unsigned slot,float gain);
#endif
