#include "streamed_world_texture.h"

bool streamed_world_texture_rgba8(uint8_t *out,size_t capacity,const uint8_t *rgba,
    unsigned width,unsigned height,unsigned alpha_test,unsigned blend,bool zero_rgb){
    if(!out||!rgba||width<8||height<8||width>1024||height>1024||
       (width&(width-1))||(height&(height-1))||blend>2||capacity<(size_t)width*height*4)return false;
    bool opaque=blend==0&&alpha_test!=1;
    for(unsigned y=0;y<height;y++)for(unsigned x=0;x<width;x++){
        unsigned morton=(x&1)|((y&1)<<1)|((x&2)<<1)|((y&2)<<2)|((x&4)<<2)|((y&4)<<3);
        size_t destination=(((size_t)(y>>3)*(width>>3)+(x>>3))*64+morton)*4;
        const uint8_t *source=rgba+((size_t)y*width+x)*4;
        uint8_t alpha=opaque?255:source[3];
        out[destination]=alpha;
        out[destination+1]=zero_rgb&&!alpha?0:source[2];
        out[destination+2]=zero_rgb&&!alpha?0:source[1];
        out[destination+3]=zero_rgb&&!alpha?0:source[0];
    }
    return true;
}
