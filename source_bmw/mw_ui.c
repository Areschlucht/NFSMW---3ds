#include "mw_ui.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { uint16_t x,y,advance;uint8_t w,h;int8_t left;uint8_t top; } UiGlyph;
struct MwUiAssets {
    const unsigned char *font,*title,*logo,*background;
    UiGlyph ascii[128],title_ascii[128];
};
typedef struct { unsigned char *fb;const MwUiAssets *assets;bool title; } UiCanvas;
static uint32_t little32(const unsigned char *p)
{ return p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }
static unsigned little16(const unsigned char *p)
{ return p[0]|((unsigned)p[1]<<8); }
static uint32_t crc32(const unsigned char *p,size_t n)
{
    uint32_t crc=~0u;
    while (n--) {
        crc^=*p++;
        for (unsigned b=0;b<8;++b) crc=(crc>>1)^(0xedb88320u&(0u-(crc&1)));
    }
    return ~crc;
}
MwUiAssets *mw_ui_assets_decode(const void *data,size_t bytes)
{
    const unsigned char *p=data;
    if (!p || bytes<48 || bytes>400000 || memcmp(p,"NUI2",4) ||
        little32(p+4)!=2 || little32(p+8)!=bytes) return NULL;
    unsigned count=little32(p+16),tc=little32(p+20),font=little32(p+24),title=little32(p+28);
    unsigned logo=little32(p+32),bg=little32(p+36);
    if (!count || count>256 || tc!=37 || little32(p+40)!=256 || little32(p+44)!=160 ||
        font!=48+(count+tc)*12 || title!=font+65536 || logo!=title+40960 ||
        bg!=logo+65536 || bytes!=(size_t)bg+MW_UI_BYTES ||
        crc32(p+48,bytes-48)!=little32(p+12)) return NULL;
    unsigned char seen[8192]={0};
    for (unsigned bank=0;bank<2;++bank) {
        memset(seen,0,sizeof(seen));unsigned n=bank?tc:count,base=48+(bank?count*12:0);
        for (unsigned i=0;i<n;++i) {
            const unsigned char *g=p+base+i*12;unsigned code=little16(g),w=g[2],h=g[3];
            unsigned x=little16(g+4),y=little16(g+6),advance=little16(g+10),max_h=bank?160:256;
            if ((seen[code/8]&(1u<<(code%8))) || x>=256 || y>=max_h || w>48 || h>48 || x+w>256 || y+h>max_h ||
                !advance || advance>48 || g[9]>48 || (int8_t)g[8]<-16 || (int8_t)g[8]>16) return NULL;
            seen[code/8]|=(unsigned char)(1u<<(code%8));
        }
        /* Every character required by this bank must exist. */
        for (unsigned ch=32;ch<127;++ch) {
            bool required=!bank || ch==' ' || (ch>='A' && ch<='Z') || (ch>='0' && ch<='9');
            if (required && !(seen[ch/8]&(1u<<(ch%8)))) return NULL;
        }
    }
    MwUiAssets *a=calloc(1,sizeof(*a)+bytes-48);if (!a) return NULL;
    unsigned char *copy=(unsigned char *)(a+1);memcpy(copy,p+48,bytes-48);
    a->font=copy+font-48;a->title=copy+title-48;a->logo=copy+logo-48;a->background=copy+bg-48;
    for (unsigned i=0;i<count+tc;++i) {
        const unsigned char *g=copy+i*12;unsigned ch=little16(g);if (ch>=128) continue;
        UiGlyph *out=i<count?&a->ascii[ch]:&a->title_ascii[ch];
        *out=(UiGlyph){.x=(uint16_t)little16(g+4),.y=(uint16_t)little16(g+6),
            .advance=(uint16_t)little16(g+10),.w=g[2],.h=g[3],.left=(int8_t)g[8],.top=g[9]};
    }
    return a;
}
void mw_ui_assets_free(MwUiAssets *assets) { free(assets); }

/* Original generic 5x7 UI font. These are not extracted game graphics. */
static const char alphabet[]="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789:./+-?";
static const unsigned char glyphs[][5]={
 {126,17,17,17,126},{127,73,73,73,54},{62,65,65,65,34},{127,65,65,34,28},
 {127,73,73,73,65},{127,9,9,9,1},{62,65,73,73,122},{127,8,8,8,127},
 {65,65,127,65,65},{32,64,65,63,1},{127,8,20,34,65},{127,64,64,64,64},
 {127,2,12,2,127},{127,4,8,16,127},{62,65,65,65,62},{127,9,9,9,6},
 {62,65,81,33,94},{127,9,25,41,70},{38,73,73,73,50},{1,1,127,1,1},
 {63,64,64,64,63},{31,32,64,32,31},{63,64,56,64,63},{99,20,8,20,99},
 {3,4,120,4,3},{97,81,73,69,67},
 {62,81,73,69,62},{0,66,127,64,0},{98,81,73,73,70},{34,65,73,73,54},
 {24,20,18,127,16},{39,69,69,69,57},{60,74,73,73,48},{1,113,9,5,3},
 {54,73,73,73,54},{6,73,73,41,30},
 {0,54,54,0,0},{0,96,96,0,0},{32,16,8,4,2},{8,8,62,8,8},
 {8,8,8,8,8},{2,1,81,9,6}
};
enum { BG=0x1082, PANEL=0x18c3, LINE=0x4208, TEXT=0xef7b,
       MUTED=0x9cf3, ACCENT=0xef5b, ALERT=0xfba8 };
static void pixel(unsigned char *fb,int x,int y,unsigned color)
{
    if ((unsigned)x>=MW_UI_WIDTH || (unsigned)y>=MW_UI_HEIGHT) return;
    unsigned i=((unsigned)x*240+239-(unsigned)y)*2;
    fb[i]=(unsigned char)color;fb[i+1]=(unsigned char)(color>>8);
}
static void rect(unsigned char *fb,int x,int y,int w,int h,unsigned color)
{
    /* Columns are contiguous in the rotated framebuffer. Clip once rather
       than checking bounds/recomputing a multiply for each filled pixel. */
    int right=x+w,bottom=y+h;
    if (x<0) x=0;
    if (y<0) y=0;
    if (right>MW_UI_WIDTH) right=MW_UI_WIDTH;
    if (bottom>MW_UI_HEIGHT) bottom=MW_UI_HEIGHT;
    if (x>=right || y>=bottom) return;
    for (int px=x;px<right;++px) {
        unsigned char *p=fb+((unsigned)px*240+240-(unsigned)bottom)*2;
        for (int py=y;py<bottom;++py,p+=2) {
            p[0]=(unsigned char)color;p[1]=(unsigned char)(color>>8);
        }
    }
}
static void blend(unsigned char *fb,int x,int y,unsigned color,unsigned alpha)
{
    if (!alpha || (unsigned)x>=320 || (unsigned)y>=240) return;
    unsigned i=((unsigned)x*240+239-(unsigned)y)*2;
    unsigned old=fb[i]|((unsigned)fb[i+1]<<8),inv=255-alpha;
    unsigned r=(((color>>11)*alpha+(old>>11)*inv+127)/255);
    unsigned g=((((color>>5)&63)*alpha+((old>>5)&63)*inv+127)/255);
    unsigned b=(((color&31)*alpha+(old&31)*inv+127)/255);
    pixel(fb,x,y,(r<<11)|(g<<5)|b);
}
static int text_width(const UiCanvas *c,const char *s,unsigned scale)
{
    int width=0;
    for (;*s;++s) {
        unsigned ch=(unsigned char)*s;
        const UiGlyph *g=c->assets && ch<128?(c->title?&c->assets->title_ascii[ch]:&c->assets->ascii[ch]):NULL;
        unsigned divisor=c->title?4:2;
        width+=g?(int)((g->advance*scale+divisor-1)/divisor):(int)(6*scale);
    }
    return width;
}
static void logo(UiCanvas *c,int x,int y,unsigned width)
{
    unsigned height=width/4;
    for (unsigned py=0;py<height;++py) for (unsigned px=0;px<width;++px) {
        const unsigned char *p=c->assets->logo+((py*64/height)*256+px*256/width)*4;
        unsigned color=((unsigned)(p[0]>>3)<<11)|((unsigned)(p[1]>>2)<<5)|(p[2]>>3);
        blend(c->fb,x+(int)px,y+(int)py,color,p[3]);
    }
}
static void angled(unsigned char *fb,int x,int y,int width,int height,unsigned color)
{
    for (int row=0;row<height;++row) {
        int shift=(height-1-row)/3;
        rect(fb,x+shift,y+row,width-height/3,1,color);
    }
}
static void text(UiCanvas *c,int x,int y,const char *s,unsigned scale,unsigned color)
{
    unsigned char *fb=c->fb;
    if (c->assets) {
        for (;*s;++s) {
            unsigned ch=(unsigned char)*s;if (ch>=128) ch='?';
            const UiGlyph *g=c->title?&c->assets->title_ascii[ch]:&c->assets->ascii[ch];
            if (!g->advance) { x+=(int)(6*scale);continue; }
            unsigned divisor=c->title?4:2;
            unsigned w=(g->w*scale+divisor-1)/divisor,h=(g->h*scale+divisor-1)/divisor;
            const unsigned char *font=c->title?c->assets->title:c->assets->font;
            for (unsigned py=0;py<h;++py) for (unsigned px=0;px<w;++px) {
                unsigned sx=px*divisor/scale,sy=py*divisor/scale;
                unsigned a=font[(g->y+sy)*256+g->x+sx];
                if (scale<divisor) {
                    unsigned sx1=sx+1<g->w?sx+1:sx,sy1=sy+1<g->h?sy+1:sy;
                    a=(a+font[(g->y+sy)*256+g->x+sx1]+
                        font[(g->y+sy1)*256+g->x+sx]+
                        font[(g->y+sy1)*256+g->x+sx1]+2)/4;
                }
                blend(fb,x+(int)px+g->left*(int)scale/(int)divisor,y+(int)py+(int)(g->top*scale/divisor),color,a);
            }
            x+=(int)((g->advance*scale+divisor-1)/divisor);
        }
        return;
    }
    for (;*s;++s,x+=(int)(6*scale)) {
        const char *g=strchr(alphabet,*s);
        if (!g) continue;
        const unsigned char *columns=glyphs[g-alphabet];
        for (unsigned a=0;a<5;++a) for (unsigned b=0;b<7;++b)
            if (columns[a]&(1u<<b)) rect(fb,x+(int)(a*scale),y+(int)(b*scale),(int)scale,(int)scale,color);
    }
}
static void title_text(UiCanvas *c,int x,int y,const char *s,unsigned scale,unsigned color)
{
    c->title=c->assets!=NULL;text(c,x,y,s,scale,color);c->title=false;
}
static bool valid(const MwUiModel *m)
{
    return m && (unsigned)m->mode<=MW_UI_DISPLAY &&
        (unsigned)m->panel<=MW_UI_DIAGNOSTICS &&
        (unsigned)m->road_status<=MW_UI_MAP_LOADING;
}
static void button(UiCanvas *c,int x,int width,const char *label,bool active)
{
    if (c->assets) angled(c->fb,x,208,width,28,active?ACCENT:PANEL);
    else rect(c->fb,x,208,width,28,active?ACCENT:PANEL);
    text(c,x+(width-text_width(c,label,1))/2,216,label,1,active?BG:TEXT);
}
static void binding(UiCanvas *c,int x,int y,const char *key,const char *label)
{
    text(c,x,y,key,1,ACCENT);text(c,x+24,y,label,1,TEXT);
}
static void help(UiCanvas *c,int x,int y)
{
    binding(c,x,y,"A","ACCELERATE");binding(c,x,y+16,"B","BRAKE");
    binding(c,x,y+32,"Y","REVERSE");binding(c,x,y+48,"R","HANDBRAKE");
    binding(c,x,y+64,"PAD","STEER");binding(c,x,y+80,"X","RESET CAR");
    text(c,x,y+104,"STEER AND TAP R AT SPEED",1,MUTED);
    text(c,x,y+116,"RELEASE AND COUNTERSTEER",1,MUTED);
}
static void stat(UiCanvas *c,int y,const char *label,float number)
{
    char s[32];
    if (!isfinite(number) || number<0 || number>9999) snprintf(s,sizeof(s),"%s --",label);
    else snprintf(s,sizeof(s),"%s %.1F MS",label,(double)number);
    /* Keep the whole reading within the panel with the proportional font. */
    text(c,118,y,s,text_width(c,s,2)>188?1:2,TEXT);
}
bool mw_ui_render(unsigned char *fb,size_t bytes,const MwUiModel *m,const unsigned char *map)
{
    if (!fb || bytes<MW_UI_BYTES || !valid(m)) return false;
    UiCanvas canvas={.fb=fb,.assets=m->assets};UiCanvas *c=&canvas;
    if (m->assets) memcpy(fb,m->assets->background,MW_UI_BYTES);
    else rect(fb,0,0,320,240,BG);
    if (m->assets && m->mode==MW_UI_MENU) {
        logo(c,12,0,192);text(c,224,12,"3DS",1,TEXT);text(c,224,25,"PROTOTYPE",1,MUTED);
    } else {
        rect(fb,0,0,320,24,PANEL);rect(fb,0,23,320,1,ACCENT);
        if (m->assets) logo(c,6,0,96);
        else text(c,8,8,"NFS MOST WANTED",1,TEXT);
        text(c,206,8,"3DS PROTOTYPE",1,MUTED);
    }
    if (m->mode==MW_UI_DRIVE) {
        rect(fb,6,30,96,140,PANEL);rect(fb,108,30,206,140,PANEL);
        text(c,14,38,"SPEED",1,MUTED);
        float speed=isfinite(m->speed_mps)?fabsf(m->speed_mps)*3.6f:0;
        unsigned kmh=speed>=999?999:(unsigned)speed;char s[40];snprintf(s,sizeof(s),"%03u",kmh);
        text(c,14,56,s,3,TEXT);text(c,14,84,"KM/H",1,MUTED);
        text(c,14,106,m->speed_mps<-.5f?"REVERSE":"FORWARD",1,TEXT);
        text(c,14,125,m->handbrake?"HANDBRAKE":"",1,ACCENT);
        snprintf(s,sizeof(s),"FPS %u",m->fps>999?999:m->fps);text(c,14,151,s,1,MUTED);
        if (m->panel==MW_UI_HELP) help(c,118,39);
        else if (m->panel==MW_UI_DIAGNOSTICS) {
            text(c,118,39,"PERFORMANCE",1,ACCENT);
            stat(c,59,"GPU",m->gpu_ms);stat(c,75,"DRAW",m->draw_ms);stat(c,91,"LOGIC",m->logic_ms);
            snprintf(s,sizeof(s),"WORLD TRIS %u",m->triangles);text(c,118,111,s,1,TEXT);
            snprintf(s,sizeof(s),"DRAW CALLS %u",m->draw_calls);text(c,118,127,s,1,TEXT);
            int slip=isfinite(m->slip_degrees)?(int)fminf(180,fmaxf(-180,m->slip_degrees)):0;
            snprintf(s,sizeof(s),"SLIP %+d DEG",slip);text(c,118,147,s,1,MUTED);
        } else if (map) {
            for (unsigned y=0;y<MW_UI_MAP_HEIGHT;++y) for (unsigned x=0;x<MW_UI_MAP_WIDTH;++x) {
                const unsigned char *p=map+(y*MW_UI_MAP_WIDTH+x)*3;
                unsigned c=((unsigned)(p[0]>>3)<<11)|((unsigned)(p[1]>>2)<<5)|(p[2]>>3);
                pixel(fb,(int)x+135,(int)y+36,c);
            }
        } else text(c,140,94,"MAP UNAVAILABLE",1,MUTED);
        static const char *messages[]={"COLONIAL - LOADED ROAD","ROAD EDGE AHEAD","ROAD EDGE BEHIND","EDGE REACHED - REVERSE OR RESET","MAP LOAD FAILED - X RESET","LOADING ORIGINAL ROCKPORT"};
        const char *status=m->road_status==MW_UI_ROAD_LOADED&&m->streamed_map?"ROCKPORT - ORIGINAL COLLISION":messages[m->road_status];
        text(c,8,179,status,1,m->road_status?ALERT:TEXT);
        text(c,8,194,m->streamed_map?"COLONIAL MINIMAP / PROTOTYPE PHYSICS":"PARTIAL MAP / PROTOTYPE PHYSICS",1,MUTED);
        button(c,6,96,"MENU",false);button(c,108,100,"HELP",m->panel==MW_UI_HELP);
        button(c,214,100,"STATS",m->panel==MW_UI_DIAGNOSTICS);
    } else if (m->mode==MW_UI_MENU) {
        const char *items[]={"DRIVE COLONIAL","GARAGE","CONTROLS","DISPLAY","QUIT"};
        for (unsigned i=0;i<5;++i) {
            bool selected=i==m->selected;
            if (m->assets) angled(fb,12,54+(int)i*24,296,21,selected?ACCENT:PANEL);
            else rect(fb,12,54+(int)i*24,296,21,selected?ACCENT:PANEL);
            title_text(c,24,54+(int)i*24,i==0&&m->streamed_map?"DRIVE ROCKPORT":items[i],m->assets?2:1,selected?BG:TEXT);
        }
        text(c,12,178,m->streamed_map?"ORIGINAL ROCKPORT / COLONIAL START":"ORIGINAL ROCKPORT / COLONIAL SAMPLE",1,MUTED);
        text(c,12,194,m->streamed_map?"STREAMED MAP / PROTOTYPE PHYSICS":"PARTIAL MAP / PROTOTYPE PHYSICS",1,MUTED);
        text(c,12,218,"TOUCH OR PAD + A TO SELECT",1,TEXT);
    } else if (m->mode==MW_UI_CONTROLS) {
        title_text(c,12,36,"DRIVING CONTROLS",2,TEXT);help(c,16,62);
        button(c,6,308,"BACK TO MENU",false);
    } else if (m->mode==MW_UI_DISPLAY) {
        title_text(c,12,36,"DISPLAY",2,TEXT);
        rect(fb,12,70,296,52,PANEL);
        text(c,24,89,"PISS FILTER",2,TEXT);
        text(c,248,89,m->piss_filter?"ON":"OFF",2,ACCENT);
        text(c,16,140,m->piss_filter?"ON: OPTIONAL WARM GRADE":"OFF: NEUTRAL COLOURS",1,TEXT);
        text(c,16,158,"TOUCH THE ROW OR PRESS A TO TOGGLE",1,MUTED);
        text(c,16,180,"B / START: BACK TO MENU",1,MUTED);
        button(c,6,308,"BACK TO MENU",false);
    } else {
        title_text(c,12,36,"BMW M3 GTR",2,TEXT);
        binding(c,16,66,"A","ROLL WHEELS");binding(c,16,86,"PAD","STEER WHEELS");
        binding(c,16,106,"Y","CAMERA ORBIT");binding(c,16,126,"X","RESET VIEW");
        text(c,16,164,"PAINT AND SUSPENSION UNFINISHED",1,MUTED);
        button(c,6,308,"BACK TO MENU",false);
    }
    return true;
}
MwUiAction mw_ui_touch(const MwUiModel *m,unsigned x,unsigned y)
{
    if (!valid(m) || x>=320 || y>=240) return MW_UI_NONE;
    if (m->mode==MW_UI_MENU && x>=12 && x<308 && y>=54 && y<171) {
        static const MwUiAction actions[]={MW_UI_SELECT_DRIVE,MW_UI_SELECT_GARAGE,
            MW_UI_SELECT_CONTROLS,MW_UI_SELECT_DISPLAY,MW_UI_QUIT};
        unsigned row=(y-54)/24;
        if ((y-54)%24<21) return actions[row];
    }
    if (m->mode==MW_UI_DISPLAY && x>=12 && x<308 && y>=70 && y<122)
        return MW_UI_TOGGLE_PISS_FILTER;
    if (y<208 || y>=236) return MW_UI_NONE;
    if (m->mode!=MW_UI_DRIVE) return x>=6 && x<314 && m->mode!=MW_UI_MENU?MW_UI_OPEN_MENU:MW_UI_NONE;
    if (x>=6 && x<102) return MW_UI_OPEN_MENU;
    if (x>=108 && x<208) return MW_UI_TOGGLE_HELP;
    if (x>=214 && x<314) return MW_UI_TOGGLE_DIAGNOSTICS;
    return MW_UI_NONE;
}
