#include "mw_ui_texture.h"
#include "mw_ui.h"
#include <stdint.h>
#include <string.h>
bool mw_ui_texture_pack(void *destination,size_t bytes,const unsigned char *canvas,size_t canvas_bytes)
{
    if(!destination||!canvas||bytes!=MW_UI_TEXTURE_BYTES||canvas_bytes!=MW_UI_BYTES)return false;
    uint8_t *out=destination;memset(out,0,bytes);
    for(unsigned i=0;i<MW_UI_TEXTURE_WIDTH*MW_UI_TEXTURE_HEIGHT;i++)out[i*4]=255;
    static const unsigned morton[8]={0,1,4,5,16,17,20,21};
    for(unsigned y=0;y<MW_UI_HEIGHT;y++)for(unsigned x=0;x<MW_UI_WIDTH;x++){
        unsigned input=(x*MW_UI_HEIGHT+MW_UI_HEIGHT-1-y)*2;
        unsigned color=canvas[input]|(unsigned)canvas[input+1]<<8;
        unsigned output=(((y>>3)*(MW_UI_TEXTURE_WIDTH>>3)+(x>>3))*64+morton[x&7]+2*morton[y&7])*4;
        out[output+1]=(uint8_t)((color&31)*255/31);
        out[output+2]=(uint8_t)(((color>>5)&63)*255/63);
        out[output+3]=(uint8_t)((color>>11)*255/31);
    }
    return true;
}
