#include "mw_menu_icons.h"
#include <string.h>
static uint32_t word(const unsigned char *p){return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint16_t half(const unsigned char *p){return (uint16_t)(p[0]|(uint16_t)p[1]<<8);}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
bool mw_menu_icons_open(MwMenuIcons *out,const void *data,size_t bytes)
{
    if(!out||!data||bytes!=198176)return false;
    const unsigned char *p=data;
    if(memcmp(p,"NMI1",4)||word(p+4)!=1||word(p+8)!=bytes||word(p+12)!=crc(p+16,bytes-16)||word(p+16)!=13||word(p+20)!=128||word(p+24)!=544||word(p+28)!=32)return false;
    static const unsigned char front_sha[32]={0xbc,0x3c,0x7c,0x33,0xd8,0xb2,0x62,0x0d,0xea,0xa5,0x50,0x6d,0xa8,0xc4,0x3c,0x7c,0xec,0xd6,0xfa,0x5e,0xa3,0xd3,0xf3,0x69,0xd8,0xba,0xf4,0xbb,0xee,0x75,0x39,0x20};
    static const unsigned char dol_sha[32]={0x33,0xc5,0xea,0xe6,0x99,0xf8,0x71,0xbe,0xac,0x05,0x9b,0x69,0x32,0x47,0x5c,0xad,0x5e,0x9f,0x61,0x0b,0xb2,0xb2,0x29,0x8e,0x04,0x6d,0x04,0x37,0x57,0xb9,0x41,0x66};
    if(memcmp(p+32,front_sha,32)||memcmp(p+64,dol_sha,32))return false;
    for(unsigned i=96;i<128;i++)if(p[i])return false;
    static const uint32_t hashes[]={0x03704f3d,0x4e6fbb02,0xc6a1a6e0,0x9a962438,0x6b303856,0x3058fe37,0xc1c089ce,0xe7353be7,0x12bb5ea2,0x73272ed2,0xc61c8d3a,0xe69d4f7c,0x02716e8a};
    uint32_t at=544;
    for(unsigned i=0;i<13;i++){
        const unsigned char *r=p+128+i*32;unsigned side=i==12?16:64;
        if(word(r)!=i+1||word(r+4)!=hashes[i]||word(r+8)!=side||word(r+12)!=side||word(r+16)!=at||word(r+20)!=side*side*4||word(r+24)||word(r+28))return false;
        at+=side*side*4;
    }
    if(at!=bytes)return false;
    *out=(MwMenuIcons){.data=p,.bytes=bytes};return true;
}
bool mw_menu_icon_find(const MwMenuIcons *icons,MwMenuAction action,MwMenuIcon *out)
{
    if(!icons||!icons->data||icons->bytes!=198176||!out||action<1||action>13)return false;
    const unsigned char *r=icons->data+128+((unsigned)action-1)*32;
    *out=(MwMenuIcon){.rgba=icons->data+word(r+16),.width=word(r+8),.height=word(r+12),.source_hash=word(r+4)};return true;
}
static void pixel(unsigned char *p,int x,int y,unsigned color)
{
    if((unsigned)x>=320||(unsigned)y>=240)return;
    size_t at=((unsigned)x*240+239-(unsigned)y)*2;p[at]=(unsigned char)color;p[at+1]=(unsigned char)(color>>8);
}
static void rectangle(unsigned char *p,int x,int y,int width,int height,unsigned color)
{for(int py=0;py<height;py++)for(int px=0;px<width;px++)pixel(p,x+px,y+py,color);}
static void blend(unsigned char *p,int x,int y,const unsigned char *s)
{
    if((unsigned)x>=320||(unsigned)y>=240||!s[3])return;
    size_t at=((unsigned)x*240+239-(unsigned)y)*2;unsigned old=half(p+at),a=s[3],inv=255-a;
    unsigned r=(((s[0]>>3)*a+(old>>11)*inv+127)/255),g=(((s[1]>>2)*a+((old>>5)&63)*inv+127)/255),b=(((s[2]>>3)*a+(old&31)*inv+127)/255);
    pixel(p,x,y,(r<<11)|(g<<5)|b);
}
static void arrow(unsigned char *p,int x,int y,bool right,unsigned color)
{
    for(int row=-6;row<=6;row++){int n=row<0?-row:row;for(int w=0;w<3;w++)pixel(p,x+(right?-n:n)+w,y+row,color);}
}
bool mw_menu_icons_render(const MwMenuIcons *icons,const MwMenuLayout *m,unsigned char *p,size_t bytes)
{
    if(!icons||!icons->data||icons->bytes!=198176||!p||bytes!=320*240*2||!mw_menu_layout_visible(m))return false;
    /* Validate all visible IDs before writing, even for caller-owned models. */
    for(unsigned i=0;i<mw_menu_layout_visible(m);i++){
        MwMenuButton b;if(!mw_menu_layout_button(m,i,&b)||b.action<MW_MENU_CAREER||b.action>MW_MENU_JUMP_SAFEHOUSE)return false;
    }
    for(unsigned i=0;i<mw_menu_layout_visible(m);i++){
        MwMenuButton b;mw_menu_layout_button(m,i,&b);int y=b.selected?70:78,height=b.selected?92:84;
        rectangle(p,b.x,y,b.width,height,b.selected?0xe71a:0x738e);
        rectangle(p,b.x+2,y+2,b.width-4,height-4,b.selected?0x2123:0x1082);
        /* The slanted lower edge is ordinary port UI geometry, not invented art. */
        for(int edge=0;edge<7;edge++)rectangle(p,b.x+edge,y+height-edge-1,b.width-edge,1,0x0000);
        MwMenuIcon icon;
        if(mw_menu_icon_find(icons,b.action,&icon)){
            unsigned side=b.selected?56:48;int left=b.x+(b.width-(int)side)/2,top=y+(height-(int)side)/2-1;
            for(unsigned py=0;py<side;py++)for(unsigned px=0;px<side;px++){
                unsigned sx=px*icon.width/side,sy=py*icon.height/side;
                blend(p,left+(int)px,top+(int)py,icon.rgba+((size_t)sy*icon.width+sx)*4);
            }
        }
    }
    rectangle(p,4,177,25,30,0x1082);rectangle(p,291,177,25,30,0x1082);
    arrow(p,13,192,false,0xe71a);arrow(p,306,192,true,0xe71a);
    for(unsigned i=0;i<m->count;i++)rectangle(p,160-(int)m->count*4+(int)i*8,211,5,2,i==m->selected?0xe71a:0x738e);
    return true;
}
