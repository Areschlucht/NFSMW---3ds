#ifndef GARAGE_MENU_H
#define GARAGE_MENU_H
#include <stdint.h>
typedef enum { UI_MAIN,UI_GARAGE,UI_CONTROLS,UI_MAP_MISSING,UI_QUIT } GarageScreen;
enum { UI_UP=1,UI_DOWN=2,UI_ACCEPT=4,UI_BACK=8,UI_START=16 };
typedef struct { GarageScreen screen; unsigned selected; } GarageUI;
void garage_ui_reset(GarageUI *ui);
void garage_ui_event(GarageUI *ui,uint32_t buttons);
#endif
