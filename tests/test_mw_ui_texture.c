#include "mw_ui_texture.h"
#include "mw_ui.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
static unsigned interleave(unsigned x,unsigned y)
{
    unsigned n=0;for(unsigned b=0;b<3;b++){n|=((x>>b)&1)<<(b*2);n|=((y>>b)&1)<<(b*2+1);}return n;
}
int main(void)
{
    uint8_t *canvas=malloc(MW_UI_BYTES),*texture=malloc(MW_UI_TEXTURE_BYTES+16);assert(canvas&&texture);
    for(unsigned i=0;i<MW_UI_BYTES;i++)canvas[i]=(uint8_t)(i*37+i/19);
    for(unsigned i=0;i<16;i++)texture[MW_UI_TEXTURE_BYTES+i]=0xa5;
    assert(!mw_ui_texture_pack(texture,MW_UI_TEXTURE_BYTES-1,canvas,MW_UI_BYTES));
    assert(mw_ui_texture_pack(texture,MW_UI_TEXTURE_BYTES,canvas,MW_UI_BYTES));
    for(unsigned y=0;y<MW_UI_TEXTURE_HEIGHT;y++)for(unsigned x=0;x<MW_UI_TEXTURE_WIDTH;x++){
        unsigned at=(((y/8)*64+x/8)*64+interleave(x%8,y%8))*4;unsigned c=0;
        if(x<320&&y<240){unsigned in=(x*240+239-y)*2;c=canvas[in]|(unsigned)canvas[in+1]<<8;}
        assert(texture[at]==255&&texture[at+1]==(c&31)*255/31);
        assert(texture[at+2]==((c>>5)&63)*255/63&&texture[at+3]==(c>>11)*255/31);
    }
    for(unsigned i=0;i<16;i++)assert(texture[MW_UI_TEXTURE_BYTES+i]==0xa5);
    free(canvas);free(texture);puts("HUD texture: all131072 tiled texels, orientation, RGB565 channels and bounds PASS");
}
