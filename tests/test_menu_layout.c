#include "mw_menu_layout.h"
#include "mw_menu_icons.h"
#include <assert.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
enum { ICON_BYTES=198176, CANVAS=320*240*2, GUARD=31 };
static uint32_t crc(const unsigned char *p,size_t n){uint32_t c=~0u;while(n--){c^=*p++;for(unsigned j=0;j<8;j++)c=(c>>1)^(0xedb88320u&-(c&1u));}return ~c;}
static void put32(unsigned char *p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(n>>(i*8));}
static void corrupt_reject(unsigned char *data,size_t at,bool repair_crc)
{
    unsigned char before[4];memcpy(before,data+12,4);data[at]^=1;if(repair_crc)put32(data+12,crc(data+16,ICON_BYTES-16));
    MwMenuIcons untouched={.data=(void *)1,.bytes=123};assert(!mw_menu_icons_open(&untouched,data,ICON_BYTES));assert(untouched.data==(void *)1&&untouched.bytes==123);
    data[at]^=1;memcpy(data+12,before,4);
}
int main(int argc,char **argv)
{
    assert(argc==2);
    const MwMenuAction actions[]={MW_MENU_CAREER,MW_MENU_CHALLENGE,MW_MENU_QUICK_RACE,MW_MENU_MY_CARS,MW_MENU_ALIAS,MW_MENU_OPTIONS};
    MwMenuLayout m;assert(mw_menu_layout_init(&m,actions,6,0));
    unsigned total=0;
    for(unsigned selection=0;selection<6;selection++){
        assert(mw_menu_layout_select(&m,selection));unsigned first=mw_menu_layout_first(&m);
        assert(selection>=first&&selection<first+4&&first<=2);
        for(unsigned slot=0;slot<4;slot++){
            MwMenuButton b;assert(mw_menu_layout_button(&m,slot,&b));assert(b.index==first+slot&&b.action==actions[b.index]);
            MwMenuLayout touched=m;MwMenuAction out=MW_MENU_EXIT;
            assert(mw_menu_layout_touch(&touched,(unsigned)b.x+35,100,&out)==MW_MENU_TOUCH_ACTIVATE);
            assert(out==b.action&&touched.selected==b.index);total++;
        }
    }
    assert(!mw_menu_layout_button(&m,4,&(MwMenuButton){0}));
    assert(mw_menu_layout_select(&m,0));assert(mw_menu_layout_move(&m,-1)&&m.selected==5);assert(mw_menu_layout_move(&m,1)&&m.selected==0);
    MwMenuAction out=MW_MENU_EXIT;assert(mw_menu_layout_touch(&m,13,190,&out)==MW_MENU_TOUCH_SELECT&&m.selected==5);assert(mw_menu_layout_touch(&m,306,190,&out)==MW_MENU_TOUCH_SELECT&&m.selected==0);
    out=MW_MENU_EXIT;MwMenuLayout unchanged=m;
    assert(mw_menu_layout_touch(&m,80,100,&out)==MW_MENU_TOUCH_NONE&&out==MW_MENU_EXIT);
    assert(mw_menu_layout_touch(&m,320,0,&out)==MW_MENU_TOUCH_NONE);assert(mw_menu_layout_touch(&m,100,220,&out)==MW_MENU_TOUCH_NONE);
    assert(!memcmp(&m,&unchanged,sizeof m));
    assert(!mw_menu_layout_move(&m,0));assert(!mw_menu_layout_select(&m,6));
    assert(!mw_menu_layout_init(&m,actions,0,0));assert(!mw_menu_layout_init(&m,actions,17,0));assert(!mw_menu_layout_init(&m,actions,6,6));assert(!memcmp(&m,&unchanged,sizeof m));
    const MwMenuAction repeated[]={MW_MENU_CAREER,MW_MENU_CAREER};assert(!mw_menu_layout_init(&m,repeated,2,0));
    const MwMenuAction invalid[]={0};assert(!mw_menu_layout_init(&m,invalid,1,0));
    for(int action=MW_MENU_CAREER;action<=MW_MENU_JUMP_SAFEHOUSE;action++){
        assert(*mw_menu_action_label((MwMenuAction)action));MwMenuCamera a={0},b={0};
        assert(mw_menu_camera_focus(&a,MW_MENU_CAREER,true));b=a;
        assert(mw_menu_camera_focus(&a,(MwMenuAction)action,false)&&mw_menu_camera_focus(&b,(MwMenuAction)action,false));
        for(unsigned i=0;i<60;i++)assert(mw_menu_camera_step(&a,1.f/60));
        for(unsigned i=0;i<8;i++)assert(mw_menu_camera_step(&b,.125f));
        assert(!memcmp(&a.current,&a.target,sizeof a.current));assert(!memcmp(&a.current,&b.current,sizeof a.current));
        assert(isfinite(a.current.yaw)&&a.current.distance>=3&&a.current.distance<=4.5f&&a.current.fov>=35&&a.current.fov<=50);
        MwMenuCamera before=a;assert(!mw_menu_camera_step(&a,NAN));assert(!mw_menu_camera_step(&a,-.1f));assert(!mw_menu_camera_step(&a,.3f));assert(!mw_menu_camera_focus(&a,0,false));assert(!memcmp(&a,&before,sizeof a));
    }
    MwMenuCamera interrupted={0};assert(mw_menu_camera_focus(&interrupted,MW_MENU_CAREER,true));assert(mw_menu_camera_focus(&interrupted,MW_MENU_MY_CARS,false));assert(mw_menu_camera_step(&interrupted,.15f));
    MwMenuCameraPose current=interrupted.current;assert(mw_menu_camera_focus(&interrupted,MW_MENU_OPTIONS,false));assert(!memcmp(&interrupted.start,&current,sizeof current));
    assert(mw_menu_camera_focus(&interrupted,MW_MENU_QUICK_RACE,true)&&interrupted.current.yaw==interrupted.target.yaw);
    FILE *f=fopen(argv[1],"rb");assert(f);unsigned char *data=malloc(ICON_BYTES),*canvas=malloc(CANVAS+GUARD*2);assert(data&&canvas);
    assert(fread(data,1,ICON_BYTES,f)==ICON_BYTES&&fgetc(f)==EOF);assert(!fclose(f));MwMenuIcons icons;assert(mw_menu_icons_open(&icons,data,ICON_BYTES));
    for(unsigned i=1;i<=13;i++){MwMenuIcon icon;assert(mw_menu_icon_find(&icons,(MwMenuAction)i,&icon));assert(icon.width==(i==13?16u:64u)&&icon.height==icon.width&&icon.source_hash);}
    assert(!mw_menu_icon_find(&icons,MW_MENU_EXIT,&(MwMenuIcon){0}));
    for(unsigned selection=0;selection<6;selection++){
        assert(mw_menu_layout_select(&m,selection));memset(canvas,0x5a,CANVAS+GUARD*2);assert(mw_menu_icons_render(&icons,&m,canvas+GUARD,CANVAS));
        for(unsigned i=0;i<GUARD;i++)assert(canvas[i]==0x5a&&canvas[GUARD+CANVAS+i]==0x5a);
    }
    memset(canvas,0x5a,CANVAS+GUARD*2);assert(!mw_menu_icons_render(&icons,&m,canvas+GUARD,CANVAS-1));
    MwMenuLayout bad=m;bad.count=17;assert(!mw_menu_icons_render(&icons,&bad,canvas+GUARD,CANVAS));
    bad=m;bad.actions[mw_menu_layout_first(&bad)]=0;assert(!mw_menu_icons_render(&icons,&bad,canvas+GUARD,CANVAS));
    for(unsigned i=0;i<CANVAS+GUARD*2;i++)assert(canvas[i]==0x5a);
    const unsigned offsets[]={0,4,8,12,16,20,24,28,32,64,96,544};
    for(unsigned i=0;i<sizeof offsets/sizeof *offsets;i++)corrupt_reject(data,offsets[i],false);
    for(unsigned row=0;row<13;row++)for(unsigned field=0;field<8;field++)corrupt_reject(data,128+row*32+field*4,true);
    MwMenuIcons rejected;assert(!mw_menu_icons_open(&rejected,data,ICON_BYTES-1));assert(!mw_menu_icons_open(&rejected,data,ICON_BYTES+1));
    free(data);free(canvas);printf("menu: %u direct-touch actions, scrolling/empty-space, 16 camera actions, 6 guarded layouts and malformed icon packs pass\n",total);return 0;
}
