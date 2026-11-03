#include "garage_menu.h"
#include <assert.h>
#include <stddef.h>
#include <stdio.h>
int main(void)
{
    GarageUI ui;garage_ui_reset(&ui);assert(ui.screen==UI_MAIN && ui.selected==0);
    garage_ui_event(&ui,UI_ACCEPT);assert(ui.screen==UI_MAP_MISSING);
    garage_ui_event(&ui,UI_ACCEPT);assert(ui.screen==UI_MAIN);
    garage_ui_event(&ui,UI_DOWN|UI_ACCEPT);assert(ui.screen==UI_GARAGE);
    garage_ui_event(&ui,UI_ACCEPT);assert(ui.screen==UI_GARAGE);
    garage_ui_event(&ui,UI_START);assert(ui.screen==UI_MAIN);
    garage_ui_event(&ui,UI_DOWN|UI_ACCEPT);assert(ui.screen==UI_CONTROLS);
    garage_ui_event(&ui,UI_BACK);assert(ui.screen==UI_MAIN);
    garage_ui_reset(&ui);garage_ui_event(&ui,UI_UP);assert(ui.selected==3);
    garage_ui_event(&ui,UI_DOWN);assert(ui.selected==0);
    garage_ui_event(&ui,UI_START);assert(ui.screen==UI_QUIT);
    garage_ui_event(&ui,UI_BACK);assert(ui.screen==UI_QUIT);
    garage_ui_reset(&ui);garage_ui_event(&ui,UI_UP|UI_ACCEPT);assert(ui.screen==UI_QUIT);
    garage_ui_reset(NULL);garage_ui_event(NULL,UI_ACCEPT);
    puts("Menu checks passed: navigation, wrap, unavailable map, garage, controls, back and exit.");
    return 0;
}
