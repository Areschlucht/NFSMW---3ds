#include "mw_frontend_top.h"
#include <string.h>
static uint32_t word(const unsigned char *p){return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint16_t half(const unsigned char *p){return (uint16_t)(p[0]|(uint16_t)p[1]<<8);}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
bool mw_frontend_top_open(MwFrontendTop *out,const void *data,size_t bytes)
{
    if(!out||!data||bytes<96||bytes>400000)return false;
    const unsigned char *p=data;
    if(memcmp(p,"NUT1",4)||word(p+4)!=1||word(p+8)!=bytes||word(p+12)!=crc(p+96,bytes-96)||word(p+16)!=400||word(p+20)!=240)return false;
    uint32_t count=word(p+24),glyphs=word(p+28),font=word(p+32),logo=word(p+36),bg=word(p+40);
    if(!count||count>256||glyphs!=96||font!=96+count*12||logo!=font+65536||bg!=logo+65536||bytes!=(size_t)bg+MW_FRONTEND_TOP_BYTES)return false;
    for(unsigned i=44;i<64;i++)if(p[i])return false;
    MwFrontendTop next={.data=p,.bytes=bytes,.background=p+bg,.font=p+font,.logo=p+logo};
    unsigned char seen[8192]={0};
    for(uint32_t i=0;i<count;i++){
        const unsigned char *g=p+glyphs+i*12;unsigned ch=half(g),w=g[2],h=g[3],x=half(g+4),y=half(g+6),advance=half(g+10);
        if((seen[ch/8]&(1u<<(ch%8)))||x>=256||y>=256||w>48||h>48||x+w>256||y+h>256||!advance||advance>48||(int8_t)g[8]<-16||(int8_t)g[8]>16||g[9]>48)return false;
        seen[ch/8]|=(unsigned char)(1u<<(ch%8));
        if(ch<128)next.ascii[ch]=(MwFrontendGlyph){(uint16_t)x,(uint16_t)y,(uint16_t)advance,(uint8_t)w,(uint8_t)h,(int8_t)g[8],g[9]};
    }
    for(unsigned ch=32;ch<127;ch++)if(!(seen[ch/8]&(1u<<(ch%8))))return false;
    *out=next;return true;
}
static void blend(unsigned char *canvas,int x,int y,unsigned color,unsigned alpha)
{
    if((unsigned)x>=400||(unsigned)y>=240||!alpha)return;
    unsigned at=((unsigned)x*240+239-(unsigned)y)*2,old=half(canvas+at),inv=255-alpha;
    unsigned r=(((color>>11)*alpha+(old>>11)*inv+127)/255),g=((((color>>5)&63)*alpha+((old>>5)&63)*inv+127)/255),b=(((color&31)*alpha+(old&31)*inv+127)/255);
    unsigned pixel=(r<<11)|(g<<5)|b;canvas[at]=(unsigned char)pixel;canvas[at+1]=(unsigned char)(pixel>>8);
}
static void rect(unsigned char *canvas,int x,int y,int width,int height,unsigned color,unsigned alpha)
{ for(int py=0;py<height;py++)for(int px=0;px<width;px++)blend(canvas,x+px,y+py,color,alpha); }
static void text(const MwFrontendTop *a,unsigned char *canvas,int x,int y,int right,const char *s,unsigned color)
{
    if(!s)return;
    /* Strings are caller-owned; cap text work even if a malformed model lacks
       a short page/alias label. Source asset pointers remain validated above. */
    for(unsigned i=0;i<96&&s[i];i++){
        unsigned ch=(unsigned char)s[i];if(ch<32||ch>=127)ch='?';const MwFrontendGlyph *g=&a->ascii[ch];
        int width=(g->width+1)/2,height=(g->height+1)/2,advance=(g->advance+1)/2;
        if(x+advance>right)break;
        for(int py=0;py<height;py++)for(int px=0;px<width;px++){
            unsigned sx=(unsigned)px*2,sy=(unsigned)py*2,sx1=sx+1<g->width?sx+1:sx,sy1=sy+1<g->height?sy+1:sy;
            unsigned alpha=(a->font[(g->y+sy)*256+g->x+sx]+a->font[(g->y+sy)*256+g->x+sx1]+a->font[(g->y+sy1)*256+g->x+sx]+a->font[(g->y+sy1)*256+g->x+sx1]+2)/4;
            blend(canvas,x+px+g->left/2,y+py+g->top/2,color,alpha);
        }
        x+=advance;
    }
}
bool mw_frontend_top_render(const MwFrontendTop *a,unsigned char *canvas,size_t bytes,const MwFrontendTopModel *m)
{
    if(!a||!a->data||!canvas||bytes!=MW_FRONTEND_TOP_BYTES||!m)return false;
    memcpy(canvas,a->background,bytes);
    /* Selected-car space is deliberately free of controls. The caller draws
       its existing 3D car over the backdrop after this 2D quad. */
    rect(canvas,12,8,376,66,0x0000,72);
    rect(canvas,12,190,376,44,0x0000,150);
    for(unsigned y=0;y<52;y++)for(unsigned x=0;x<208;x++){
        const unsigned char *p=a->logo+((y*64/52)*256+x*256/208)*4;
        unsigned color=((unsigned)(p[0]>>3)<<11)|((unsigned)(p[1]>>2)<<5)|(p[2]>>3);
        blend(canvas,16+(int)x,12+(int)y,color,p[3]);
    }
    rect(canvas,14,73,372,1,0xef7b,140);
    text(a,canvas,278,18,384,"ALIAS",0x9cf3);
    text(a,canvas,278,33,384,m->alias?m->alias:"NO ALIAS",0xef7b);
    text(a,canvas,16,81,384,m->page?m->page:"MAIN MENU",0xef7b);
    text(a,canvas,16,199,384,m->selection?m->selection:"",0xef7b);
    text(a,canvas,16,218,384,m->detail?m->detail:"",0x9cf3);
    return true;
}
bool mw_frontend_top_pack(void *destination,size_t bytes,const unsigned char *canvas,size_t source_bytes)
{
    if(!destination||!canvas||bytes!=MW_FRONTEND_TOP_TEXTURE_BYTES||source_bytes!=MW_FRONTEND_TOP_BYTES)return false;
    unsigned char *out=destination;memset(out,0,bytes);
    for(unsigned i=0;i<512*256;i++)out[i*4]=255;
    static const unsigned morton[8]={0,1,4,5,16,17,20,21};
    for(unsigned y=0;y<240;y++)for(unsigned x=0;x<400;x++){
        unsigned color=half(canvas+(x*240+239-y)*2),at=(((y>>3)*64+(x>>3))*64+morton[x&7]+2*morton[y&7])*4;
        out[at+1]=(unsigned char)((color&31)*255/31);out[at+2]=(unsigned char)(((color>>5)&63)*255/63);out[at+3]=(unsigned char)((color>>11)*255/31);
    }
    return true;
}
