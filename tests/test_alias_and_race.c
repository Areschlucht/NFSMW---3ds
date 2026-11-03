#include "mw_alias.h"
#include "mw_race_progress.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>
int main(void){
    MwAliasStore s={0},decoded={0};unsigned char raw[MW_ALIAS_SAVE_BYTES],bad[MW_ALIAS_SAVE_BYTES];
    assert(mw_alias_create(&s,"Razor"));uint32_t first=s.selected;
    assert(!mw_alias_create(&s,"rAzOr"));assert(!mw_alias_create(&s," ../bad"));
    assert(!mw_alias_create(&s,"Trailing "));assert(mw_alias_create(&s,"Driver 2"));
    assert(mw_alias_rename(&s,first,"Rockport"));assert(mw_alias_select(&s,first));
    assert(mw_alias_encode(&s,raw,sizeof(raw)));assert(mw_alias_decode(&decoded,raw,sizeof(raw)));
    assert(decoded.count==2&&decoded.selected==first&&!strcmp(mw_alias_selected_name(&decoded),"Rockport"));
    for(unsigned i=0;i<sizeof(raw);i++)for(unsigned bit=0;bit<8;bit++){
        memcpy(bad,raw,sizeof(raw));bad[i]^=1u<<bit;MwAliasStore before=decoded;
        assert(!mw_alias_decode(&decoded,bad,sizeof(bad)));assert(!memcmp(&decoded,&before,sizeof(decoded)));
    }
    assert(mw_alias_remove(&s,first));assert(s.count==1&&strcmp(mw_alias_selected_name(&s),"Rockport"));
    assert(mw_alias_remove(&s,s.selected));assert(!s.count&&!s.selected);
    for(unsigned i=0;i<MW_ALIAS_CAPACITY;i++){char n[32];snprintf(n,sizeof(n),"Driver %u",i);assert(mw_alias_create(&s,n));}
    assert(!mw_alias_create(&s,"Too many"));
    uint32_t gates[]={101,103,104};MwRaceRoute route={gates,3,999,2};MwRaceProgress race;
    assert(mw_race_begin(&race,&route));assert(mw_race_tick(&race,1250000));
    assert(mw_race_gate(&race,999)==MW_RACE_IGNORED);assert(mw_race_gate(&race,103)==MW_RACE_IGNORED);
    for(unsigned lap=0;lap<2;lap++){
        for(unsigned i=0;i<3;i++){assert(mw_race_gate(&race,gates[i])==MW_RACE_CHECKPOINT);assert(mw_race_gate(&race,gates[i])==MW_RACE_IGNORED);}
        assert(mw_race_gate(&race,999)==(lap?MW_RACE_FINISHED:MW_RACE_LAP));
    }
    assert(!mw_race_tick(&race,1));assert(mw_race_gate(&race,999)==MW_RACE_IGNORED);assert(race.elapsed_us==1250000);
    puts("Alias CRUD, roundtrip, 5376 single-bit corruption rejections and ordered race/lap/finish checks passed.");
}
