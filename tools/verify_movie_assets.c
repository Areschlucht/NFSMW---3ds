#include "mw_movie.h"
#include <stdio.h>
#include <stdlib.h>

int main(int argc,char **argv)
{
    if(argc<2){fprintf(stderr,"Usage: verify_movie_assets movie.nvm [...]\n");return 2;}
    unsigned char *jpeg=malloc(MW_MOVIE_JPEG_CAPACITY),*pixels=malloc(MW_MOVIE_PIXELS),*pcm=malloc(MW_MOVIE_AUDIO_BLOCK_BYTES);
    if(!jpeg||!pixels||!pcm)return 1;
    for(int i=1;i<argc;i++){
        MwMovie m={0};if(!mw_movie_open(&m,argv[i])){fprintf(stderr,"Movie index rejected: %s\n",argv[i]);return 1;}
        unsigned decodes=0;
        for(uint32_t j=0;j<m.frames;j++){
            size_t bytes;if(!mw_movie_frame_jpeg(&m,j,jpeg,MW_MOVIE_JPEG_CAPACITY,&bytes))return 1;
            if(!(j%37)||j+1==m.frames){if(!mw_movie_decode_jpeg(jpeg,bytes,pixels,MW_MOVIE_PIXELS))return 1;++decodes;}
        }
        uint64_t samples=0;
        for(uint32_t j=0;j<m.audio_blocks;j++){
            uint32_t frames;if(!mw_movie_audio_block(&m,j,pcm,MW_MOVIE_AUDIO_BLOCK_BYTES,&frames))return 1;samples+=frames;
        }
        if(samples!=m.audio_frames)return 1;
        printf("%s: %u video frames/%u sampled JPEG decodes, %llu PCM frames, %llu us; CRC/index checks pass\n",argv[i],m.frames,decodes,(unsigned long long)samples,(unsigned long long)mw_movie_duration_us(&m));
        mw_movie_close(&m);
    }
    free(jpeg);free(pixels);free(pcm);return 0;
}
