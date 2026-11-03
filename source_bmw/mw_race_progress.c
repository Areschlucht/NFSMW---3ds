#include "mw_race_progress.h"
bool mw_race_begin(MwRaceProgress *s,const MwRaceRoute *r)
{
    if(!s||!r||!r->laps||r->count>1024||(r->count&&!r->checkpoints))return false;
    *s=(MwRaceProgress){.route=*r,.lap=1,.running=true};return true;
}
bool mw_race_tick(MwRaceProgress *s,uint64_t dt)
{
    if(!s||!s->running||s->finished||UINT64_MAX-s->elapsed_us<dt)return false;
    s->elapsed_us+=dt;return true;
}
MwRaceEvent mw_race_gate(MwRaceProgress *s,uint32_t gate)
{
    if(!s||!s->running||s->finished)return MW_RACE_IGNORED;
    if(s->next<s->route.count){
        if(gate!=s->route.checkpoints[s->next])return MW_RACE_IGNORED;
        s->next++;return MW_RACE_CHECKPOINT;
    }
    if(gate!=s->route.finish)return MW_RACE_IGNORED;
    if(s->lap<s->route.laps){s->lap++;s->next=0;return MW_RACE_LAP;}
    s->running=false;s->finished=true;return MW_RACE_FINISHED;
}
