#ifndef MW_MOVIE_H
#define MW_MOVIE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

enum { MW_MOVIE_WIDTH=320, MW_MOVIE_HEIGHT=224,
    MW_MOVIE_PIXELS=320*224*2, MW_MOVIE_TEXTURE_BYTES=512*256*4,
    MW_MOVIE_JPEG_CAPACITY=65536, MW_MOVIE_AUDIO_BLOCK_FRAMES=4096,
    MW_MOVIE_AUDIO_BLOCK_BYTES=4096*2*2 };
typedef struct {
    FILE *video,*audio;
    uint32_t total_bytes,frames,rate_numerator,rate_denominator,
        audio_crc_at,audio_blocks,data_at,audio_at,audio_frames,
        sample_rate,max_jpeg_bytes;
    unsigned char source_sha256[32];
} MwMovie;
typedef struct { uint32_t offset,bytes,crc32; } MwMovieFrame;
/* Initialize to zero; close before reopening. Independent FILE positions avoid
   audio queue reads disturbing video seeks. Open validates all bounded indexes;
   frames/audio have individual CRCs checked before successful publication.
   A failing open leaves out unchanged. No movie payload is loaded into RAM. */
bool mw_movie_open(MwMovie *out,const char *path);
void mw_movie_close(MwMovie *movie);
bool mw_movie_frame_info(MwMovie *,uint32_t index,MwMovieFrame *out);
/* On failure caller scratch bytes may have changed; do not upload/queue them.
   Successful JPEG read writes its byte count to out_bytes. */
bool mw_movie_frame_jpeg(MwMovie *,uint32_t index,void *scratch,size_t capacity,size_t *out_bytes);
bool mw_movie_audio_block(MwMovie *,uint32_t block,void *pcm,size_t capacity,uint32_t *out_frames);
uint64_t mw_movie_video_duration_us(const MwMovie *);
uint64_t mw_movie_duration_us(const MwMovie *);
uint32_t mw_movie_frame_at_us(const MwMovie *,uint64_t elapsed_us);
uint32_t mw_movie_frame_at_audio_sample(const MwMovie *,uint64_t played_samples);
/* Requires cached libjpeg on target (-ljpeg). Strict baseline320x224 RGB output.
   Output is linear row-major RGB565 little-endian, not a displayed framebuffer.
   Caller must stage/finish before texture upload; malformed decode may dirty
   scratch output. Define MW_MOVIE_NO_JPEG only for reader-only host tests. */
bool mw_movie_decode_jpeg(const void *,size_t,unsigned char *rgb565,size_t);
/* Opaque active image in512x256 tiled RGBA8, origin(0,0); padding is transparent.
   Suggested C2D image320x224 at(40,8) on400x240 preserves stored aspect ratio. */
bool mw_movie_texture_pack(void *texture,size_t texture_bytes,const unsigned char *rgb565,size_t source_bytes);
#endif
