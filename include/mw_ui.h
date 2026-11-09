#ifndef MW_UI_H
#define MW_UI_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Portable bottom-screen renderer: no allocation, SDK calls or GPU state changes.
   The caller owns a rotated 320x240 RGB565 little-endian framebuffer. */
enum { MW_UI_WIDTH=320, MW_UI_HEIGHT=240, MW_UI_BYTES=320*240*2,
       MW_UI_MAP_WIDTH=152, MW_UI_MAP_HEIGHT=128 };
typedef enum { MW_UI_MENU, MW_UI_DRIVE, MW_UI_GARAGE, MW_UI_CONTROLS,
               MW_UI_DISPLAY, MW_UI_TITLE, MW_UI_FRONTEND } MwUiMode;
typedef enum { MW_UI_NAVIGATION, MW_UI_HELP, MW_UI_DIAGNOSTICS } MwUiPanel;
typedef enum { MW_UI_NONE, MW_UI_OPEN_MENU, MW_UI_SELECT_DRIVE,
    MW_UI_SELECT_GARAGE, MW_UI_SELECT_CONTROLS, MW_UI_QUIT,
    MW_UI_TOGGLE_HELP, MW_UI_TOGGLE_DIAGNOSTICS, MW_UI_SELECT_DISPLAY,
    MW_UI_TOGGLE_PISS_FILTER } MwUiAction;
typedef enum { MW_UI_ROAD_LOADED, MW_UI_EDGE_AHEAD, MW_UI_EDGE_BEHIND,
               MW_UI_EDGE_REACHED, MW_UI_MAP_PAUSED, MW_UI_MAP_LOADING } MwUiRoadStatus;
typedef struct MwUiAssets MwUiAssets;
/* NUI2 converted-art pack; malformed input returns NULL. Source may be freed
   after decode. Assets own one bounded allocation; NULL uses built-in fallback. */
MwUiAssets *mw_ui_assets_decode(const void *data,size_t bytes);
void mw_ui_assets_free(MwUiAssets *assets);
typedef struct {
    MwUiMode mode;
    MwUiPanel panel;
    MwUiRoadStatus road_status;
    unsigned selected, fps, triangles, draw_calls;
    float speed_mps, slip_degrees, gpu_ms, draw_ms, logic_ms;
    bool handbrake, piss_filter, streamed_map;
    const MwUiAssets *assets;
    const char *frontend_title,*alias_name,*frontend_hint;
    const char *frontend_rows[6];
    unsigned frontend_count;
    bool frontend_title_body; /* Localized route names need the full body atlas. */
} MwUiModel;

/* Optional map is tightly packed RGB8 at exactly MAP_WIDTH x MAP_HEIGHT.
   Reject invalid framebuffer/model without writing. Null map is supported. */
bool mw_ui_render(unsigned char *framebuffer,size_t bytes,const MwUiModel *model,
                  const unsigned char *map_rgb);
/* Call once on KEY_TOUCH down, using calibrated hidTouchRead coordinates.
   This reports an intent; simulation/pause/menu policy stays with the caller. */
MwUiAction mw_ui_touch(const MwUiModel *model,unsigned x,unsigned y);
#endif
