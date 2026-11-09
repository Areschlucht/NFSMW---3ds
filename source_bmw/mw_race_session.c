#include "mw_race_session.h"
static bool terminal(MwRaceSessionPhase p)
{ return p==MW_SESSION_IDLE||p==MW_SESSION_FINISHED||p==MW_SESSION_CANCELLED; }
static bool course(const MwEventCatalog *c,const MwEventDefinition *e,MwEventNode *start)
{
    return (e->original_type==0||e->original_type==1)&&e->laps&&e->count&&e->count<=1024&&e->finish&&
        mw_event_catalog_node(c,e->start,start)&&(start->present&3u)==3u;
}
bool mw_race_session_courses(const MwEventCatalog *c,bool localized,uint32_t *keys,size_t capacity,size_t *count)
{
    if(!c||!c->data||!count)return false;
    size_t total=0;MwEventDefinition e;MwEventNode start;
    for(uint32_t i=0;i<c->events;i++)if(mw_event_catalog_get(c,i,&e)&&course(c,&e,&start)&&(!localized||*e.display_title))total++;
    if(total>capacity||(total&&!keys)){*count=total;return false;}
    size_t index=0;
    for(uint32_t i=0;i<c->events;i++)if(mw_event_catalog_get(c,i,&e)&&course(c,&e,&start)&&(!localized||*e.display_title))keys[index++]=e.key;
    *count=total;return true;
}
bool mw_race_session_prepare(MwRaceSession *s,const MwEventCatalog *catalog,uint32_t key,const MwAliasStore *aliases,uintptr_t actor)
{
    if(!s||!aliases||!actor||!terminal(s->phase))return false;
    MwAliasStore selection=*aliases;
    if(!mw_alias_select(&selection,selection.selected))return false;
    MwEventDefinition event;
    MwEventNode start;
    if(!mw_event_catalog_find(catalog,key,&event)||!course(catalog,&event,&start))return false;
    MwRaceSession next={.phase=MW_SESSION_LOADING,.alias_id=selection.selected,.event_key=key,.player_actor=actor};
    if(!mw_event_catalog_route(catalog,key,next.checkpoint_keys,1024,&next.route)||
       !mw_event_catalog_node(catalog,event.start,&next.source_start)||(next.source_start.present&3u)!=3u)return false;
    *s=next;s->route.checkpoints=s->checkpoint_keys;return true;
}
bool mw_race_session_admit(MwRaceSession *s,bool render,bool collision,bool activation)
{
    if(!s||s->phase!=MW_SESSION_LOADING||!render||!collision||!activation)return false;
    s->phase=MW_SESSION_READY;return true;
}
bool mw_race_session_start(MwRaceSession *s)
{
    if(!s||s->phase!=MW_SESSION_READY||!mw_race_begin(&s->progress,&s->route))return false;
    s->phase=MW_SESSION_RUNNING;return true;
}
bool mw_race_session_pause(MwRaceSession *s)
{ if(!s||s->phase!=MW_SESSION_RUNNING)return false;s->phase=MW_SESSION_PAUSED;return true; }
bool mw_race_session_resume(MwRaceSession *s)
{ if(!s||s->phase!=MW_SESSION_PAUSED)return false;s->phase=MW_SESSION_RUNNING;return true; }
bool mw_race_session_tick(MwRaceSession *s,uint64_t dt)
{ return s&&s->phase==MW_SESSION_RUNNING&&mw_race_tick(&s->progress,dt); }
MwRaceEvent mw_race_session_enter(MwRaceSession *s,uintptr_t actor,uint32_t gate)
{
    if(!s||s->phase!=MW_SESSION_RUNNING||actor!=s->player_actor)return MW_RACE_IGNORED;
    MwRaceEvent result=mw_race_gate(&s->progress,gate);
    if(result==MW_RACE_FINISHED)s->phase=MW_SESSION_FINISHED;
    return result;
}
bool mw_race_session_cancel(MwRaceSession *s)
{
    if(!s||terminal(s->phase))return false;
    s->phase=MW_SESSION_CANCELLED;s->progress.running=false;return true;
}
