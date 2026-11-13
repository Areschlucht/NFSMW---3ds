#ifndef MW_CINEMA_H
#define MW_CINEMA_H
#include <citro2d.h>
#include "mw_movie_audio.h"
typedef struct {
    MwMovie movie;MwMovieAudio audio;C3D_Tex texture;
    unsigned char *jpeg,*pixels;uint32_t frame,decoded,dropped;
    bool active,texture_ready,failed;
} MwCinema;
bool mw_cinema_start(MwCinema *,const char *path);
/* Outside a GPU frame. -1 decode/IO failure,0 playing,1 complete. */
int mw_cinema_update(MwCinema *);
void mw_cinema_draw(MwCinema *,C3D_RenderTarget *);
void mw_cinema_stop(MwCinema *);
#endif
