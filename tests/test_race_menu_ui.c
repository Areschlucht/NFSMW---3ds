#include "mw_race_session.h"
#include "mw_ui.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void *load(const char *path,size_t *bytes){FILE *f=fopen(path,"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0);rewind(f);void *data=malloc((size_t)n);assert(data&&fread(data,1,(size_t)n,f)==(size_t)n);fclose(f);*bytes=(size_t)n;return data;}
int main(int argc,char **argv){
    assert(argc==3);size_t bytes;unsigned char *events=load(argv[1],&bytes);MwEventCatalog catalog;assert(mw_event_catalog_open(&catalog,events,bytes));
    void *art=load(argv[2],&bytes);MwUiAssets *assets=mw_ui_assets_decode(art,bytes);assert(assets);free(art);
    unsigned char *guarded=malloc(MW_UI_BYTES+32);assert(guarded);memset(guarded,0xa5,MW_UI_BYTES+32);
    uint32_t keys[512];size_t count;assert(mw_race_session_courses(&catalog,true,keys,512,&count)&&count==79);
    MwUiModel ui={.mode=MW_UI_FRONTEND,.assets=assets,.frontend_title="QUICK RACE",.alias_name="PLAYER",.frontend_hint="A: SELECT  B: BACK"};
    for(size_t first=0;first<count;first++){
        ui.frontend_title_body=false;ui.frontend_title="QUICK RACE";ui.frontend_count=0;
        for(size_t j=first;j<count&&ui.frontend_count<6;j++){MwEventDefinition event;assert(mw_event_catalog_find(&catalog,keys[j],&event));ui.frontend_rows[ui.frontend_count++]=event.display_title;}
        ui.selected=ui.frontend_count-1;assert(mw_ui_render(guarded+16,MW_UI_BYTES,&ui,NULL));
        MwEventDefinition event;assert(mw_event_catalog_find(&catalog,keys[first],&event));ui.frontend_title=event.display_title;ui.frontend_title_body=true;
        ui.frontend_count=1;ui.frontend_rows[0]="BACK";ui.selected=0;ui.frontend_hint="RACE NOT AVAILABLE IN THIS VERSION";
        assert(mw_ui_render(guarded+16,MW_UI_BYTES,&ui,NULL));
        for(unsigned i=0;i<16;i++)assert(guarded[i]==0xa5&&guarded[MW_UI_BYTES+16+i]==0xa5);
    }
    mw_ui_assets_free(assets);free(guarded);free(events);puts("All79 named course list windows and preparation headings render within framebuffer bounds.");
}
