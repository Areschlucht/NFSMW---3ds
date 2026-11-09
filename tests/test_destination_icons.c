#include "mw_destination_icons.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { NFI_BYTES=4608, GUARD=19, WIDTH=17, HEIGHT=13, CANVAS=WIDTH*HEIGHT*3 };
static uint32_t get32(const unsigned char *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void put32(unsigned char *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(8*i));}
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned i=0;i<8;i++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void fixcrc(unsigned char *p){put32(p+12,crc(p+96,NFI_BYTES-96));}
static void reject(const unsigned char *p,size_t n)
{
    const unsigned char sentinel=1;
    MwDestinationIcons out={&sentinel,123};
    assert(!mw_destination_icons_open(&out,p,n));
    assert(out.data==&sentinel&&out.bytes==123);
}
static void compare_blit(const MwDestinationIcons *icons,unsigned kind,int type,int x,int y)
{
    unsigned char guarded[GUARD+CANVAS+GUARD],expected[CANVAS];
    memset(guarded,0x7d,sizeof guarded);memset(expected,0x7d,sizeof expected);
    MwDestinationIcon icon;assert(mw_destination_icon_find(icons,kind,type,&icon));
    /* Independent destination-pixel reference, including offscreen centers. */
    for(unsigned py=0;py<HEIGHT;py++)for(unsigned px=0;px<WIDTH;px++){
        int64_t sx=(int64_t)px-x+icon.width/2,sy=(int64_t)py-y+icon.height/2;
        if(sx<0||sy<0||sx>=icon.width||sy>=icon.height)continue;
        const unsigned char *s=icon.rgba+((size_t)sy*icon.width+(size_t)sx)*4;
        for(unsigned c=0;c<3;c++)expected[(py*WIDTH+px)*3+c]=(unsigned char)((s[c]*s[3]+125u*(255-s[3])+127)/255);
    }
    assert(mw_destination_icon_blit(icons,kind,type,guarded+GUARD,CANVAS,WIDTH,HEIGHT,x,y));
    assert(!memcmp(guarded+GUARD,expected,CANVAS));
    for(unsigned i=0;i<GUARD;i++)assert(guarded[i]==0x7d&&guarded[GUARD+CANVAS+i]==0x7d);
}
int main(int argc,char **argv)
{
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);
    unsigned char data[NFI_BYTES],bad[NFI_BYTES];
    assert(fread(data,1,sizeof data,f)==sizeof data&&fgetc(f)==EOF);assert(!fclose(f));
    MwDestinationIcons icons;assert(mw_destination_icons_open(&icons,data,sizeof data));
    const uint32_t hashes[]={0x2cfd5273,0x1ce551d4,0x12bb8395,0x571cd206,0x25559384};
    const int positions[][2]={{8,6},{0,0},{16,12},{-7,-7},{24,20},{INT_MIN,INT_MAX},{INT_MAX,INT_MIN}};
    for(unsigned i=0;i<5;i++){
        unsigned kind=i<3?i+1:4;int type=i<3?-1:(int)i-3;
        MwDestinationIcon icon;assert(mw_destination_icon_find(&icons,kind,type,&icon));
        assert(icon.source_hash==hashes[i]&&icon.width==(i==3?8u:16u)&&icon.height==icon.width);
        assert(icon.rgba==data+get32(data+96+i*32+20));
        unsigned nonzero=0,partial=0;for(unsigned p=0;p<icon.width*icon.height;p++){unsigned a=icon.rgba[p*4+3];nonzero+=a!=0;partial+=a>0&&a<255;}
        const unsigned coverage[]={140,159,128,40,140},blend[]={34,35,10,20,27};
        assert(nonzero==coverage[i]&&partial==blend[i]);
        for(unsigned p=0;p<sizeof positions/sizeof *positions;p++)compare_blit(&icons,kind,type,positions[p][0],positions[p][1]);
    }
    MwDestinationIcon unchanged={data,123,456,789};
    assert(!mw_destination_icon_find(&icons,4,2,&unchanged));assert(unchanged.rgba==data&&unchanged.width==123);
    assert(!mw_destination_icon_find(&icons,0,0,&unchanged));assert(!mw_destination_icon_find(&icons,UINT_MAX,0,&unchanged));
    unsigned char canvas[CANVAS];memset(canvas,0xa5,sizeof canvas);
    assert(!mw_destination_icon_blit(&icons,4,99,canvas,sizeof canvas,WIDTH,HEIGHT,0,0));
    assert(!mw_destination_icon_blit(&icons,1,0,canvas,sizeof canvas-1,WIDTH,HEIGHT,0,0));
    assert(!mw_destination_icon_blit(&icons,1,0,canvas,sizeof canvas,0,HEIGHT,0,0));
    assert(!mw_destination_icon_blit(&icons,1,0,canvas,sizeof canvas,UINT_MAX,UINT_MAX,0,0));
    for(unsigned i=0;i<sizeof canvas;i++)assert(canvas[i]==0xa5);
    reject(data,0);reject(data,95);reject(data,sizeof data-1);reject(data,sizeof data+1);reject(NULL,sizeof data);
    const unsigned corrupt_offsets[]={0,4,8,12,16,20,24,28,32,64,256};
    for(unsigned i=0;i<sizeof corrupt_offsets/sizeof *corrupt_offsets;i++){memcpy(bad,data,sizeof bad);bad[corrupt_offsets[i]]^=1;reject(bad,sizeof bad);}
    /* Structural errors must fail even when the payload CRC is valid. */
    for(unsigned row=0;row<5;row++)for(unsigned field=0;field<8;field++){
        memcpy(bad,data,sizeof bad);bad[96+row*32+field*4]^=1;fixcrc(bad);reject(bad,sizeof bad);
    }
    assert(!mw_destination_icons_open(NULL,data,sizeof data));
    MwDestinationIcons missing={data,0};assert(!mw_destination_icon_find(&missing,1,0,&unchanged));
    puts("destination icons: five source glyphs, 35 clipped alpha draws, malformed sidecars passed");return 0;
}
