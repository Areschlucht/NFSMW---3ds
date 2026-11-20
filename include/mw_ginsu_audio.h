#ifndef MW_GINSU_AUDIO_H
#define MW_GINSU_AUDIO_H
#include "mw_ginsu.h"
/* Caller-owned, normal-RAM cached original GIN bank. No files in render. */
typedef struct {
 unsigned char *bytes;MwGinsuBank bank;MwGinsuState synth;
 float last_rpm,last_load,source_min_rpm,source_max_rpm;bool loaded,calibrated,started,failed;
} MwGinsuAudio;
/* Initialize zero; close only AFTER the game-audio engine worker has stopped.
 * Optional expected SHA binds the wrapper header to the selected original bank;
 * header and raw-payload CRCs are always validated. */
bool mw_ginsu_audio_open(MwGinsuAudio *,const char *native_ngi_path,const unsigned char expected_source_sha256[32]);
void mw_ginsu_audio_close(MwGinsuAudio *);
/* Source engineaudio MinRPM/MaxRPM from the actual selected car binding. Set
 * before starting the worker. Raw physical RPM is not GIN frequency. */
bool mw_ginsu_audio_calibrate(MwGinsuAudio *,float source_min_rpm,float source_max_rpm);
bool mw_ginsu_audio_frequency(const MwGinsuAudio *,float source_audio_rpm,float *grain_frequency,float *pitch_ratio);
/* Compatible with MwGameAudioEngineRender. Requires actual known EngineRacer
 * audio-RPM provider and calibrated source engineaudio MinRPM/MaxRPM.
 * Uses original60ms UpdateFrequency argument and source packet renderer.
 * Selected-bank/source load/deceleration selection is a separate caller gate;
 * load is retained for diagnostics, never used to invent a second audio layer.
 * Queue input cadence is native transport policy, not complete original audio
 * manager UpdateVehicleSFX timing parity. */
bool mw_ginsu_audio_render(void *,int16_t *,unsigned frames,float actual_rpm,float load);
#endif
