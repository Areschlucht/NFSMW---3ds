#include "mw_cinema.h"
#include <stdlib.h>
#include <string.h>
bool mw_cinema_start(MwCinema *c,const char *path)
{
    if(!c||c->active||!path)return false;
    memset(c,0,sizeof(*c));c->frame=UINT32_MAX;
    if(!mw_movie_open(&c->movie,path))return false;
    c->active=true;c->jpeg=malloc(MW_MOVIE_JPEG_CAPACITY);c->pixels=malloc(MW_MOVIE_PIXELS);
    if(!c->jpeg||!c->pixels||!C3D_TexInit(&c->texture,512,256,GPU_RGBA8))goto fail;
    c->texture_ready=true;C3D_TexSetFilter(&c->texture,GPU_LINEAR,GPU_LINEAR);
    C3D_TexSetWrap(&c->texture,GPU_CLAMP_TO_EDGE,GPU_CLAMP_TO_EDGE);
    if(!mw_movie_audio_start(&c->audio,&c->movie))goto fail;
    return true;
fail:mw_cinema_stop(c);return false;
}
int mw_cinema_update(MwCinema *c)
{
    if(!c||!c->active||c->failed)return -1;
    if(!mw_movie_audio_update(&c->audio))goto fail;
    uint64_t elapsed=mw_movie_audio_elapsed_us(&c->audio);
    if(elapsed>=mw_movie_duration_us(&c->movie))return 1;
    uint32_t frame=mw_movie_frame_at_us(&c->movie,elapsed);
    if(frame!=c->frame){
        size_t bytes;
        if(!mw_movie_frame_jpeg(&c->movie,frame,c->jpeg,MW_MOVIE_JPEG_CAPACITY,&bytes)||
           !mw_movie_decode_jpeg(c->jpeg,bytes,c->pixels,MW_MOVIE_PIXELS))goto fail;
        C3D_FrameSync();
        if(!mw_movie_texture_pack(c->texture.data,c->texture.size,c->pixels,MW_MOVIE_PIXELS))goto fail;
        C3D_TexFlush(&c->texture);
        if(c->frame!=UINT32_MAX&&frame>c->frame+1)c->dropped+=frame-c->frame-1;
        c->frame=frame;c->decoded++;
    }
    return 0;
fail:c->failed=true;return -1;
}
void mw_cinema_draw(MwCinema *c,C3D_RenderTarget *target)
{
    if(!c||!c->active||!target)return;
    C3D_RenderTargetClear(target,C3D_CLEAR_ALL,0x000000ff,0);
    C2D_Prepare();C2D_SceneBegin(target);C3D_DepthTest(false,GPU_ALWAYS,GPU_WRITE_COLOR);
    C3D_AlphaTest(false,GPU_ALWAYS,0);
    if(c->frame!=UINT32_MAX){
        static const Tex3DS_SubTexture sub={.width=320,.height=224,.left=0,.top=1,.right=320.f/512,.bottom=1-224.f/256};
        C2D_Image image={.tex=&c->texture,.subtex=&sub};C2D_DrawImageAt(image,40,8,0,NULL,1,1);C2D_Flush();
    }
}
void mw_cinema_stop(MwCinema *c)
{
    if(!c)return;
    mw_movie_audio_stop(&c->audio);C3D_FrameSync();
    if(c->texture_ready)C3D_TexDelete(&c->texture);
    mw_movie_close(&c->movie);free(c->jpeg);free(c->pixels);memset(c,0,sizeof(*c));
}
