#include "mw_ui.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

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
enum { BG=0x1082, PANEL=0x18e3, LINE=0x4207, TEXT=0xef7b,
       MUTED=0x9d12, ACCENT=0xdde7, ALERT=0xfba8 };
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
static void text(unsigned char *fb,int x,int y,const char *s,unsigned scale,unsigned color)
{
    for (;*s;++s,x+=(int)(6*scale)) {
        const char *g=strchr(alphabet,*s);
        if (!g) continue;
        const unsigned char *columns=glyphs[g-alphabet];
        for (unsigned a=0;a<5;++a) for (unsigned b=0;b<7;++b)
            if (columns[a]&(1u<<b)) rect(fb,x+(int)(a*scale),y+(int)(b*scale),(int)scale,(int)scale,color);
    }
}
static bool valid(const MwUiModel *m)
{
    return m && (unsigned)m->mode<=MW_UI_CONTROLS &&
        (unsigned)m->panel<=MW_UI_DIAGNOSTICS &&
        (unsigned)m->road_status<=MW_UI_EDGE_REACHED;
}
static void button(unsigned char *fb,int x,int width,const char *label,bool active)
{
    rect(fb,x,208,width,28,active?ACCENT:PANEL);
    text(fb,x+(width-(int)strlen(label)*6)/2,218,label,1,active?BG:TEXT);
}
static void binding(unsigned char *fb,int x,int y,const char *key,const char *label)
{
    text(fb,x,y,key,1,ACCENT);text(fb,x+24,y,label,1,TEXT);
}
static void help(unsigned char *fb,int x,int y)
{
    binding(fb,x,y,"A","ACCELERATE");binding(fb,x,y+16,"B","BRAKE");
    binding(fb,x,y+32,"Y","REVERSE");binding(fb,x,y+48,"R","HANDBRAKE");
    binding(fb,x,y+64,"PAD","STEER");binding(fb,x,y+80,"X","RESET CAR");
    text(fb,x,y+104,"STEER AND TAP R AT SPEED",1,MUTED);
    text(fb,x,y+116,"RELEASE AND COUNTERSTEER",1,MUTED);
}
static void stat(unsigned char *fb,int y,const char *label,float number)
{
    char s[32];
    if (!isfinite(number) || number<0 || number>9999) snprintf(s,sizeof(s),"%s --",label);
    else snprintf(s,sizeof(s),"%s %.1F MS",label,(double)number);
    text(fb,118,y,s,2,TEXT);
}
bool mw_ui_render(unsigned char *fb,size_t bytes,const MwUiModel *m,const unsigned char *map)
{
    if (!fb || bytes<MW_UI_BYTES || !valid(m)) return false;
    rect(fb,0,0,320,240,BG);rect(fb,0,0,320,24,PANEL);rect(fb,0,23,320,1,ACCENT);
    text(fb,8,8,"NFS MOST WANTED",1,TEXT);text(fb,206,8,"3DS PROTOTYPE",1,MUTED);
    if (m->mode==MW_UI_DRIVE) {
        rect(fb,6,30,96,140,PANEL);rect(fb,108,30,206,140,PANEL);
        text(fb,14,38,"SPEED",1,MUTED);
        float speed=isfinite(m->speed_mps)?fabsf(m->speed_mps)*3.6f:0;
        unsigned kmh=speed>=999?999:(unsigned)speed;char s[40];snprintf(s,sizeof(s),"%03u",kmh);
        text(fb,14,56,s,3,TEXT);text(fb,14,84,"KM/H",1,MUTED);
        text(fb,14,106,m->speed_mps<-.5f?"REVERSE":"FORWARD",1,TEXT);
        text(fb,14,125,m->handbrake?"HANDBRAKE":"",1,ACCENT);
        snprintf(s,sizeof(s),"FPS %u",m->fps>999?999:m->fps);text(fb,14,151,s,1,MUTED);
        if (m->panel==MW_UI_HELP) help(fb,118,39);
        else if (m->panel==MW_UI_DIAGNOSTICS) {
            text(fb,118,39,"PERFORMANCE",1,ACCENT);
            stat(fb,59,"GPU",m->gpu_ms);stat(fb,75,"DRAW",m->draw_ms);stat(fb,91,"LOGIC",m->logic_ms);
            snprintf(s,sizeof(s),"WORLD TRIS %u",m->triangles);text(fb,118,111,s,1,TEXT);
            snprintf(s,sizeof(s),"DRAW CALLS %u",m->draw_calls);text(fb,118,127,s,1,TEXT);
            int slip=isfinite(m->slip_degrees)?(int)fminf(180,fmaxf(-180,m->slip_degrees)):0;
            snprintf(s,sizeof(s),"SLIP %+d DEG",slip);text(fb,118,147,s,1,MUTED);
        } else if (map) {
            for (unsigned y=0;y<MW_UI_MAP_HEIGHT;++y) for (unsigned x=0;x<MW_UI_MAP_WIDTH;++x) {
                const unsigned char *p=map+(y*MW_UI_MAP_WIDTH+x)*3;
                unsigned c=((unsigned)(p[0]>>3)<<11)|((unsigned)(p[1]>>2)<<5)|(p[2]>>3);
                pixel(fb,(int)x+135,(int)y+36,c);
            }
        } else text(fb,140,94,"MAP UNAVAILABLE",1,MUTED);
        static const char *messages[]={"COLONIAL - LOADED ROAD","ROAD EDGE AHEAD","ROAD EDGE BEHIND","EDGE REACHED - REVERSE OR RESET"};
        text(fb,8,179,messages[m->road_status],1,m->road_status?ALERT:TEXT);
        text(fb,8,194,"PARTIAL MAP / PROTOTYPE PHYSICS",1,MUTED);
        button(fb,6,96,"MENU",false);button(fb,108,100,"HELP",m->panel==MW_UI_HELP);
        button(fb,214,100,"STATS",m->panel==MW_UI_DIAGNOSTICS);
    } else if (m->mode==MW_UI_MENU) {
        const char *items[]={"DRIVE COLONIAL","GARAGE","CONTROLS","QUIT"};
        for (unsigned i=0;i<4;++i) {
            bool selected=i==m->selected;rect(fb,12,38+(int)i*31,296,27,selected?ACCENT:PANEL);
            text(fb,24,48+(int)i*31,items[i],1,selected?BG:TEXT);
        }
        text(fb,12,178,"ORIGINAL ROCKPORT / COLONIAL SAMPLE",1,MUTED);
        text(fb,12,194,"PARTIAL MAP / PROTOTYPE PHYSICS",1,MUTED);
        text(fb,12,218,"TOUCH OR PAD + A TO SELECT",1,TEXT);
    } else if (m->mode==MW_UI_CONTROLS) {
        text(fb,12,36,"DRIVING CONTROLS",2,TEXT);help(fb,16,62);
        button(fb,6,308,"BACK TO MENU",false);
    } else {
        text(fb,12,36,"BMW M3 GTR",2,TEXT);
        binding(fb,16,66,"A","ROLL WHEELS");binding(fb,16,86,"PAD","STEER WHEELS");
        binding(fb,16,106,"Y","CAMERA ORBIT");binding(fb,16,126,"X","RESET VIEW");
        text(fb,16,164,"PAINT AND SUSPENSION UNFINISHED",1,MUTED);
        button(fb,6,308,"BACK TO MENU",false);
    }
    return true;
}
MwUiAction mw_ui_touch(const MwUiModel *m,unsigned x,unsigned y)
{
    if (!valid(m) || x>=320 || y>=240) return MW_UI_NONE;
    if (m->mode==MW_UI_MENU && x>=12 && x<308 && y>=38 && y<158) {
        unsigned row=(y-38)/31;
        if ((y-38)%31<27) return (MwUiAction)(MW_UI_SELECT_DRIVE+row);
    }
    if (y<208 || y>=236) return MW_UI_NONE;
    if (m->mode!=MW_UI_DRIVE) return x>=6 && x<314 && m->mode!=MW_UI_MENU?MW_UI_OPEN_MENU:MW_UI_NONE;
    if (x>=6 && x<102) return MW_UI_OPEN_MENU;
    if (x>=108 && x<208) return MW_UI_TOGGLE_HELP;
    if (x>=214 && x<314) return MW_UI_TOGGLE_DIAGNOSTICS;
    return MW_UI_NONE;
}
