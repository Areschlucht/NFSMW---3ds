#ifndef MW_AUDIO_STREAM_H
#define MW_AUDIO_STREAM_H
#include "mw_movie.h"
/* Authored native PCM container. Payload is losslessly expanded stereo PCM16;
 * mono original samples are duplicated, never resampled. CRC checked per4096
 * frames before publication. Original bank/segment identity stays in manifest. */
typedef struct {
    uint32_t original_channels,loop_start,loop_end,flags;
    float reference_rpm;
} MwAudioStreamInfo;
bool mw_audio_stream_open(MwMovie *,MwAudioStreamInfo *,const char *path);
#endif
