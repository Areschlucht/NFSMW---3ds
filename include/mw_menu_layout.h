#ifndef MW_MENU_LAYOUT_H
#define MW_MENU_LAYOUT_H
#include <stdbool.h>
#include <stddef.h>

/* Stable port actions, not recovered FEng object/script IDs. Parent owns pages,
   active car, career eligibility and activation; this module owns screen layout. */
typedef enum {
    MW_MENU_CAREER=1, MW_MENU_QUICK_RACE, MW_MENU_MY_CARS, MW_MENU_CHALLENGE,
    MW_MENU_ALIAS, MW_MENU_OPTIONS, MW_MENU_RESUME_CAREER, MW_MENU_NEW_CAREER,
    MW_MENU_RESUME_FREE_ROAM, MW_MENU_PARTS, MW_MENU_PERFORMANCE, MW_MENU_VISUAL,
    MW_MENU_MAIN_MENU, MW_MENU_BACK, MW_MENU_EXIT, MW_MENU_JUMP_SAFEHOUSE
} MwMenuAction;
enum { MW_MENU_CAPACITY=16, MW_MENU_VISIBLE=4, MW_MENU_CAPTION_Y=181,
       MW_MENU_DETAIL_Y=201, MW_MENU_FOOTER_Y=221 };
typedef struct {
    MwMenuAction actions[MW_MENU_CAPACITY];
    unsigned count,selected;
} MwMenuLayout;
typedef struct { int x,y,width,height;unsigned index;MwMenuAction action;bool selected; } MwMenuButton;
typedef enum { MW_MENU_TOUCH_NONE, MW_MENU_TOUCH_SELECT, MW_MENU_TOUCH_ACTIVATE } MwMenuTouch;
bool mw_menu_layout_init(MwMenuLayout *,const MwMenuAction *,unsigned count,unsigned selected);
bool mw_menu_layout_select(MwMenuLayout *,unsigned selected);
bool mw_menu_layout_move(MwMenuLayout *,int direction);
unsigned mw_menu_layout_first(const MwMenuLayout *);
unsigned mw_menu_layout_visible(const MwMenuLayout *);
bool mw_menu_layout_button(const MwMenuLayout *,unsigned visible_index,MwMenuButton *);
/* A button tap immediately selects AND activates its explicit action. Footer
   arrows change selection only. Empty screen space never activates a menu. */
MwMenuTouch mw_menu_layout_touch(MwMenuLayout *,unsigned x,unsigned y,MwMenuAction *);
const char *mw_menu_action_label(MwMenuAction);

/* Page-dependent frontend vehicle framing. Numbers are new 3DS adaptation
   presets inspired by the supplied screenshots, not original GC camera curves.
   Use current active car in the caller; no hardcoded BMW ownership here. */
typedef struct { float yaw,pitch,roll,x,y,distance,fov; } MwMenuCameraPose;
typedef struct {
    MwMenuCameraPose current,start,target;
    float elapsed,duration;
    MwMenuAction action;
    bool initialized;
} MwMenuCamera;
bool mw_menu_camera_focus(MwMenuCamera *,MwMenuAction,bool immediate);
bool mw_menu_camera_step(MwMenuCamera *,float seconds);
#endif
