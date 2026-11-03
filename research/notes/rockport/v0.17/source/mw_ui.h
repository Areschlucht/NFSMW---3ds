#ifndef MW_UI_H
#define MW_UI_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Portable bottom-screen UI: no allocation, SDK calls or GPU state changes.
   The caller owns a rotated 320x240 RGB565 little-endian framebuffer. */
enum { MW_UI_WIDTH=320, MW_UI_HEIGHT=240, MW_UI_BYTES=320*240*2,
       MW_UI_MAP_WIDTH=152, MW_UI_MAP_HEIGHT=128 };
typedef enum { MW_UI_MENU, MW_UI_DRIVE, MW_UI_GARAGE, MW_UI_CONTROLS } MwUiMode;
typedef enum { MW_UI_NAVIGATION, MW_UI_HELP, MW_UI_DIAGNOSTICS } MwUiPanel;
typedef enum { MW_UI_NONE, MW_UI_OPEN_MENU, MW_UI_SELECT_DRIVE,
    MW_UI_SELECT_GARAGE, MW_UI_SELECT_CONTROLS, MW_UI_QUIT,
    MW_UI_TOGGLE_HELP, MW_UI_TOGGLE_DIAGNOSTICS } MwUiAction;
typedef enum { MW_UI_ROAD_LOADED, MW_UI_EDGE_AHEAD, MW_UI_EDGE_BEHIND,
               MW_UI_EDGE_REACHED } MwUiRoadStatus;
typedef struct {
    MwUiMode mode;
    MwUiPanel panel;
    MwUiRoadStatus road_status;
    unsigned selected, fps, triangles, draw_calls;
    float speed_mps, slip_degrees, gpu_ms, draw_ms, logic_ms;
    bool handbrake;
} MwUiModel;

/* Optional map is tightly packed RGB8 at exactly MAP_WIDTH x MAP_HEIGHT.
   Reject invalid framebuffer/model without writing. Null map is supported. */
bool mw_ui_render(unsigned char *framebuffer,size_t bytes,const MwUiModel *model,
                  const unsigned char *map_rgb);
/* Call once on KEY_TOUCH down, using calibrated hidTouchRead coordinates.
   This reports an intent; simulation/pause/menu policy stays with the caller. */
MwUiAction mw_ui_touch(const MwUiModel *model,unsigned x,unsigned y);
#endif
