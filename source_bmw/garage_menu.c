#include "garage_menu.h"
#include <stddef.h>
void garage_ui_reset(GarageUI *ui)
{ if (ui) *ui=(GarageUI){.screen=UI_MAIN,.selected=0}; }
void garage_ui_event(GarageUI *ui,uint32_t buttons)
{
    if (!ui || ui->screen==UI_QUIT) return;
    if (ui->screen==UI_MAIN) {
        if (buttons&UI_START) { ui->screen=UI_QUIT;return; }
        if (buttons&UI_UP) ui->selected=(ui->selected+3)%4;
        if (buttons&UI_DOWN) ui->selected=(ui->selected+1)%4;
        if (buttons&UI_ACCEPT) {
            const GarageScreen destinations[]={UI_MAP_MISSING,UI_GARAGE,UI_CONTROLS,UI_QUIT};
            ui->screen=destinations[ui->selected];
        }
    } else if (buttons&(UI_BACK|UI_START)) ui->screen=UI_MAIN;
    else if (ui->screen!=UI_GARAGE && (buttons&UI_ACCEPT)) ui->screen=UI_MAIN;
}
