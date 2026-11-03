/* Host-only renderer/checker. Input is the existing 152x128 P6 road map.
   Output names are bottom-screen design previews, not emulator screenshots. */
#include "mw_ui.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void save(const char *folder,const char *name,const unsigned char *fb)
{
    char path[512];assert(snprintf(path,sizeof(path),"%s/%s.ppm",folder,name)>0);
    FILE *f=fopen(path,"wb");assert(f);fprintf(f,"P6\n320 240\n255\n");
    for (unsigned y=0;y<240;++y) for (unsigned x=0;x<320;++x) {
        unsigned i=(x*240+239-y)*2,c=fb[i]|((unsigned)fb[i+1]<<8);
        unsigned char rgb[3]={(unsigned char)(((c>>11)&31)*255/31),
            (unsigned char)(((c>>5)&63)*255/63),(unsigned char)((c&31)*255/31)};
        assert(fwrite(rgb,1,3,f)==3);
    }
    assert(!fclose(f));
}
static void store32(unsigned char *p,unsigned value)
{ for (unsigned i=0;i<4;++i) p[i]=(unsigned char)(value>>(8*i)); }
static unsigned checksum(const unsigned char *p,size_t bytes)
{
    unsigned crc=~0u;
    while (bytes--) {
        crc^=*p++;
        for (unsigned b=0;b<8;++b) crc=(crc>>1)^(0xedb88320u&(0u-(crc&1)));
    }
    return ~crc;
}
int main(int argc,char **argv)
{
    assert(argc==3 || argc==4);FILE *f=fopen(argv[1],"rb");assert(f);
    unsigned w,h,max;assert(fscanf(f,"P6 %u %u %u",&w,&h,&max)==3);
    assert(w==152 && h==128 && max==255);assert(fgetc(f)=='\n');
    unsigned char map[152*128*3];assert(fread(map,1,sizeof(map),f)==sizeof(map));fclose(f);
    unsigned char guarded[MW_UI_BYTES+32];memset(guarded,0xa5,sizeof(guarded));
    unsigned char *fb=guarded+16;
    MwUiModel m={.mode=MW_UI_DRIVE,.fps=60,.speed_mps=21.6f,.triangles=37359,
        .draw_calls=180,.gpu_ms=12.4f,.draw_ms=4.2f,.logic_ms=.8f,.slip_degrees=-14};
    MwUiAssets *assets=NULL;
    if (argc==4) {
        f=fopen(argv[3],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);rewind(f);assert(n>32);
        unsigned char *raw=malloc((size_t)n);assert(raw);assert(fread(raw,1,(size_t)n,f)==(size_t)n);fclose(f);
        assets=mw_ui_assets_decode(raw,(size_t)n);assert(assets);
        assert(!mw_ui_assets_decode(raw,(size_t)n-1));raw[n-1]^=1;
        assert(!mw_ui_assets_decode(raw,(size_t)n));raw[n-1]^=1;
        /* Recompute CRC so malformed metric tests reach structural validation. */
        unsigned char old=raw[50];raw[50]=255;
        store32(raw+12,checksum(raw+48,(size_t)n-48));assert(!mw_ui_assets_decode(raw,(size_t)n));raw[50]=old;
        old=raw[48];raw[48]=127; /* required space missing */
        store32(raw+12,checksum(raw+48,(size_t)n-48));assert(!mw_ui_assets_decode(raw,(size_t)n));raw[48]=old;
        old=raw[60];raw[60]=raw[48]; /* duplicate codepoint */
        store32(raw+12,checksum(raw+48,(size_t)n-48));assert(!mw_ui_assets_decode(raw,(size_t)n));raw[60]=old;
        store32(raw+12,checksum(raw+48,(size_t)n-48));
        old=raw[24];raw[24]^=1;assert(!mw_ui_assets_decode(raw,(size_t)n));raw[24]=old;
        raw[0]='?';assert(!mw_ui_assets_decode(raw,(size_t)n));free(raw);m.assets=assets;
    }
    assert(!mw_ui_render(fb,MW_UI_BYTES-1,&m,map));assert(fb[0]==0xa5);
    assert(mw_ui_render(fb,MW_UI_BYTES,&m,map));save(argv[2],"drive",fb);
    assert(mw_ui_touch(&m,8,218)==MW_UI_OPEN_MENU);
    assert(mw_ui_touch(&m,120,218)==MW_UI_TOGGLE_HELP);
    assert(mw_ui_touch(&m,220,218)==MW_UI_TOGGLE_DIAGNOSTICS);
    assert(mw_ui_touch(&m,105,218)==MW_UI_NONE);
    assert(mw_ui_touch(&m,320,218)==MW_UI_NONE);
    assert(mw_ui_touch(&m,220,236)==MW_UI_NONE);
    m.panel=MW_UI_HELP;assert(mw_ui_render(fb,MW_UI_BYTES,&m,NULL));save(argv[2],"help",fb);
    m.panel=MW_UI_DIAGNOSTICS;assert(mw_ui_render(fb,MW_UI_BYTES,&m,NULL));save(argv[2],"stats",fb);
    m.panel=MW_UI_NAVIGATION;m.road_status=MW_UI_EDGE_REACHED;m.handbrake=true;
    assert(mw_ui_render(fb,MW_UI_BYTES,&m,map));save(argv[2],"edge",fb);
    m.mode=MW_UI_MENU;assert(mw_ui_render(fb,MW_UI_BYTES,&m,map));save(argv[2],"menu",fb);
    const MwUiAction actions[]={MW_UI_SELECT_DRIVE,MW_UI_SELECT_GARAGE,
        MW_UI_SELECT_CONTROLS,MW_UI_SELECT_DISPLAY,MW_UI_QUIT};
    for (unsigned row=0;row<5;++row) {
        assert(mw_ui_touch(&m,12,54+row*24)==actions[row]);
        assert(mw_ui_touch(&m,307,74+row*24)==actions[row]);
        assert(mw_ui_touch(&m,30,75+row*24)==MW_UI_NONE);
        assert(mw_ui_touch(&m,11,54+row*24)==MW_UI_NONE);
        assert(mw_ui_touch(&m,308,54+row*24)==MW_UI_NONE);
    }
    m.mode=MW_UI_GARAGE;assert(mw_ui_render(fb,MW_UI_BYTES,&m,NULL));save(argv[2],"garage",fb);
    m.mode=MW_UI_CONTROLS;assert(mw_ui_render(fb,MW_UI_BYTES,&m,NULL));save(argv[2],"controls",fb);
    assert(mw_ui_touch(&m,100,220)==MW_UI_OPEN_MENU);
    m.mode=MW_UI_DISPLAY;assert(!m.piss_filter);
    assert(mw_ui_render(fb,MW_UI_BYTES,&m,NULL));save(argv[2],"display-off",fb);
    assert(mw_ui_touch(&m,12,70)==MW_UI_TOGGLE_PISS_FILTER);
    assert(mw_ui_touch(&m,307,121)==MW_UI_TOGGLE_PISS_FILTER);
    assert(mw_ui_touch(&m,11,70)==MW_UI_NONE);
    assert(mw_ui_touch(&m,308,70)==MW_UI_NONE);
    assert(mw_ui_touch(&m,12,69)==MW_UI_NONE);
    assert(mw_ui_touch(&m,12,122)==MW_UI_NONE);
    assert(mw_ui_touch(&m,160,220)==MW_UI_OPEN_MENU);
    m.piss_filter=true;assert(mw_ui_render(fb,MW_UI_BYTES,&m,NULL));save(argv[2],"display-on",fb);
    assert(mw_ui_touch(&m,160,90)==MW_UI_TOGGLE_PISS_FILTER);
    m.mode=(MwUiMode)(MW_UI_DISPLAY+1);
    unsigned char first=fb[0];assert(!mw_ui_render(fb,MW_UI_BYTES,&m,NULL));assert(fb[0]==first);
    assert(mw_ui_touch(&m,160,90)==MW_UI_NONE);
    for (unsigned i=0;i<16;++i) assert(guarded[i]==0xa5 && guarded[MW_UI_BYTES+16+i]==0xa5);
    mw_ui_assets_free(assets);mw_ui_assets_free(NULL);
    puts("UI framebuffer bounds, five menu rows and Display toggle/back checks passed; nine previews written.");
    return 0;
}
