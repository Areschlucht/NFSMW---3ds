#ifndef MW_GINSU_H
#define MW_GINSU_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
enum { MW_GINSU_MAX_PACKET=1024 };
/* Original immutable LE Gnsu banks, not a loop over the decoded RPM sweep. */
typedef struct {
 const unsigned char *data,*frequency_positions,*cycle_positions,*samples;
 size_t bytes;uint32_t segments,cycles,sample_count,rate;
 float min_frequency,max_frequency,min_period;
} MwGinsuBank;
typedef struct {
 int32_t playback,current,target,countdown,no_jump_remaining;
 uint32_t packet_size,overlap_size,no_jump_size;
 int32_t cached_block;float decoded[32],current_cycle;
 int16_t packet[MW_GINSU_MAX_PACKET];uint32_t cursor,available;
 bool ready;
} MwGinsuState;
bool mw_ginsu_bank_open(MwGinsuBank *,const void *,size_t);
bool mw_ginsu_frequency_sample(const MwGinsuBank *,float,int32_t *);
bool mw_ginsu_cycle_sample(const MwGinsuBank *,float,int32_t *);
bool mw_ginsu_sample_cycle(const MwGinsuBank *,int32_t,float *);
bool mw_ginsu_cycle_period(const MwGinsuBank *,float,float *);
bool mw_ginsu_samples(MwGinsuState *,const MwGinsuBank *,int32_t,int16_t *,uint32_t);
/* Original HybridMotor RPM calibration then SingleGinsu low-end pitch split.
 * audio_rpm is SFXCTL_Engine.GetEngRPM, not an invented speed-to-RPM curve. */
bool mw_ginsu_engine_frequency(const MwGinsuBank *,float audio_rpm,float engine_min,float engine_max,float *grain_frequency,float *low_pitch_ratio);
bool mw_ginsu_start(MwGinsuState *,const MwGinsuBank *,float source_frequency);
bool mw_ginsu_frequency(MwGinsuState *,const MwGinsuBank *,float source_frequency,float transition_milliseconds);
/* One original source packet (264 samples at24kHz). Caller supplies capacity.
 * No allocations/I/O. Undefined original out-of-bank fetches instead refuse. */
bool mw_ginsu_packet(MwGinsuState *,const MwGinsuBank *,int16_t *,size_t capacity);
/* Queue adapter retains unconsumed source packet tails, no extra grain jumps. */
bool mw_ginsu_render(MwGinsuState *,const MwGinsuBank *,int16_t *,uint32_t frames);
#endif
