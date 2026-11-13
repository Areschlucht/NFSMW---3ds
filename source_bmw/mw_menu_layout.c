#include "mw_menu_layout.h"
#include <math.h>
#include <string.h>
static bool action_valid(MwMenuAction a){return a>=MW_MENU_CAREER&&a<=MW_MENU_JUMP_SAFEHOUSE;}
static bool layout_valid(const MwMenuLayout *m){return m&&m->count&&m->count<=MW_MENU_CAPACITY&&m->selected<m->count;}
bool mw_menu_layout_init(MwMenuLayout *out,const MwMenuAction *actions,unsigned count,unsigned selected)
{
    if(!out||!actions||!count||count>MW_MENU_CAPACITY||selected>=count)return false;
    MwMenuLayout m={.count=count,.selected=selected};
    for(unsigned i=0;i<count;i++){
        if(!action_valid(actions[i]))return false;
        for(unsigned j=0;j<i;j++)if(actions[j]==actions[i])return false;
        m.actions[i]=actions[i];
    }
    *out=m;return true;
}
bool mw_menu_layout_select(MwMenuLayout *m,unsigned selected)
{if(!layout_valid(m)||selected>=m->count)return false;m->selected=selected;return true;}
bool mw_menu_layout_move(MwMenuLayout *m,int direction)
{
    if(!layout_valid(m)||(direction!=-1&&direction!=1))return false;
    m->selected=direction<0?(m->selected+m->count-1)%m->count:(m->selected+1)%m->count;return true;
}
unsigned mw_menu_layout_first(const MwMenuLayout *m)
{
    if(!layout_valid(m)||m->count<=MW_MENU_VISIBLE)return 0;
    unsigned first=m->selected<2?0:m->selected-1,max=m->count-MW_MENU_VISIBLE;
    return first<max?first:max;
}
unsigned mw_menu_layout_visible(const MwMenuLayout *m)
{if(!layout_valid(m))return 0;return m->count<MW_MENU_VISIBLE?m->count:MW_MENU_VISIBLE;}
bool mw_menu_layout_button(const MwMenuLayout *m,unsigned slot,MwMenuButton *out)
{
    if(!out||slot>=mw_menu_layout_visible(m))return false;
    unsigned index=mw_menu_layout_first(m)+slot;
    /* Stable hit areas do not move when the selected panel is raised. */
    *out=(MwMenuButton){.x=8+(int)slot*78,.y=68,.width=70,.height=98,
        .index=index,.action=m->actions[index],.selected=index==m->selected};return true;
}
MwMenuTouch mw_menu_layout_touch(MwMenuLayout *m,unsigned x,unsigned y,MwMenuAction *out)
{
    if(!layout_valid(m)||!out||x>=320||y>=240)return MW_MENU_TOUCH_NONE;
    for(unsigned slot=0;slot<mw_menu_layout_visible(m);slot++){
        MwMenuButton b;mw_menu_layout_button(m,slot,&b);
        if(x>=(unsigned)b.x&&x<(unsigned)(b.x+b.width)&&y>=(unsigned)b.y&&y<(unsigned)(b.y+b.height)){
            m->selected=b.index;*out=b.action;return MW_MENU_TOUCH_ACTIVATE;
        }
    }
    if(y>=177&&y<207&&(x<32||x>=288)){
        mw_menu_layout_move(m,x<32?-1:1);*out=m->actions[m->selected];return MW_MENU_TOUCH_SELECT;
    }
    return MW_MENU_TOUCH_NONE;
}
const char *mw_menu_action_label(MwMenuAction a)
{
    static const char *const labels[]={"","CAREER","QUICK RACE","MY CARS","CHALLENGE SERIES",
        "ALIAS MANAGER","OPTIONS","RESUME CAREER","NEW CAREER","RESUME FREE ROAM",
        "PARTS","PERFORMANCE","VISUAL","MAIN MENU","BACK","EXIT","JUMP TO SAFE HOUSE"};
    return action_valid(a)?labels[a]:"";
}
static MwMenuCameraPose preset(MwMenuAction a)
{
    MwMenuCameraPose p={.yaw=2.42f,.pitch=.18f,.distance=3.65f,.fov=40};
    switch(a){
    case MW_MENU_QUICK_RACE:p.yaw=1.05f;p.pitch=.12f;p.x=.08f;p.distance=3.8f;break;
    case MW_MENU_MY_CARS:p.yaw=1.57f;p.pitch=.12f;p.distance=4.0f;break;
    case MW_MENU_CHALLENGE:p.yaw=-.62f;p.pitch=.24f;p.distance=3.65f;break;
    case MW_MENU_ALIAS:p.yaw=3.0f;p.pitch=.21f;p.distance=3.85f;break;
    case MW_MENU_OPTIONS:p.yaw=2.82f;p.pitch=.29f;p.distance=4.1f;break;
    case MW_MENU_NEW_CAREER:p.yaw=2.64f;p.pitch=.15f;p.distance=3.7f;break;
    case MW_MENU_PARTS:p.yaw=1.32f;p.pitch=.2f;p.x=.06f;p.distance=3.4f;break;
    case MW_MENU_PERFORMANCE:p.yaw=2.72f;p.pitch=.3f;p.distance=3.15f;break;
    case MW_MENU_VISUAL:p.yaw=1.18f;p.pitch=.11f;p.distance=3.45f;break;
    default:break;
    }
    return p;
}
bool mw_menu_camera_focus(MwMenuCamera *c,MwMenuAction a,bool immediate)
{
    if(!c||!action_valid(a))return false;
    if(c->initialized&&c->action==a&&!immediate)return true;
    MwMenuCameraPose target=preset(a);
    if(!c->initialized||immediate){*c=(MwMenuCamera){.current=target,.start=target,.target=target,.duration=.48f,.action=a,.initialized=true};return true;}
    c->start=c->current;c->target=target;c->elapsed=0;c->duration=.48f;c->action=a;return true;
}
static float mix(float a,float b,float t){return a+(b-a)*t;}
bool mw_menu_camera_step(MwMenuCamera *c,float seconds)
{
    if(!c||!c->initialized||!isfinite(seconds)||seconds<0||seconds>.25f)return false;
    if(c->elapsed>=c->duration)return true;
    c->elapsed=fminf(c->duration,c->elapsed+seconds);float t=c->elapsed/c->duration;t=t*t*(3-2*t);
    MwMenuCameraPose p;
    p.yaw=c->start.yaw+remainderf(c->target.yaw-c->start.yaw,6.283185307f)*t;
    p.pitch=mix(c->start.pitch,c->target.pitch,t);p.roll=mix(c->start.roll,c->target.roll,t);
    p.x=mix(c->start.x,c->target.x,t);p.y=mix(c->start.y,c->target.y,t);
    p.distance=mix(c->start.distance,c->target.distance,t);p.fov=mix(c->start.fov,c->target.fov,t);
    if(c->elapsed==c->duration)p=c->target;
    c->current=p;return true;
}
