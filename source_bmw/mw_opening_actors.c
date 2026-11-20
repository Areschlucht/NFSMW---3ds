#include "mw_opening_actors.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>

static bool point(const float p[3])
{
    return p&&isfinite(p[0])&&isfinite(p[1])&&isfinite(p[2]);
}
static bool motion(const DriveState *p)
{
    return p&&isfinite(p->x)&&isfinite(p->z)&&isfinite(p->heading)&&
        isfinite(p->speed)&&isfinite(p->steering)&&isfinite(p->lateral_speed)&&
        isfinite(p->yaw_rate)&&isfinite(p->drift);
}
bool mw_opening_actors_begin(MwOpeningActors *out,const MwRaceAIPack *racers,
    const MwPursuitPack *police,const MwEventCatalog *catalog,
    const MwTrafficWorld *roads,uint32_t event,const float origin[3],
    uintptr_t player,const float source[3])
{
    if(!out||!point(origin)||!point(source)||!player)return false;
    MwOpeningActors *next=calloc(1,sizeof(*next));
    if(!next)return false;
    bool ok=mw_pursuit_begin(&next->pursuit,police,event,origin,player,source)&&
        mw_race_ai_begin(&next->race,racers,catalog,roads,event,origin,NULL);
    if(ok){
        next->prepared=true;
        *out=*next;
        /* The source route pointers belong to the permanent destination,
         * never the temporary transactional planning object. */
        out->race.route.checkpoints=out->race.checkpoints;
        for(unsigned i=0;i<out->race.count;i++)
            out->race.actors[i].progress.route.checkpoints=out->race.checkpoints;
    }
    free(next);
    return ok;
}
bool mw_opening_actors_admit_racer(MwOpeningActors *s,unsigned i,bool ready)
{
    return s&&s->prepared&&!s->running&&mw_race_ai_admit(&s->race,i,ready);
}
bool mw_opening_actors_admit_police(MwOpeningActors *s,bool ready)
{
    if(!s||!s->prepared||s->running)return false;
    s->police_admitted=ready;
    return true;
}
bool mw_opening_actors_start(MwOpeningActors *s)
{
    if(!s||!s->prepared||s->running||
       (s->pursuit.has_event&&!s->police_admitted)||
       !mw_race_ai_start(&s->race))return false;
    s->running=true;
    s->paused=s->faulted=s->simulation_ready=false;
    s->tick_phase=0;
    return true;
}
bool mw_opening_actors_pause(MwOpeningActors *s,bool pause)
{
    if(!s||!s->running||!mw_race_ai_pause(&s->race,pause))return false;
    s->paused=pause;
    return true;
}
bool mw_opening_actors_relocate(MwOpeningActors *s,const float source[3])
{
    if(!s||!s->prepared||!point(source))return false;
    return mw_pursuit_relocate(&s->pursuit,s->pursuit.player_actor,source);
}
bool mw_opening_actors_update(MwOpeningActors *s,const DriveState *player,
    float height,const float source[3],float radius,uint64_t elapsed,
    MwRaceAIDrive drive,void *context,MwOpeningActorsWork *work)
{
    MwOpeningActorsWork w={0};
    if(work)*work=w;
    if(!s||!s->running||!motion(player)||!point(source)||!isfinite(height)||
       !isfinite(radius)||radius<0||radius>10||elapsed>100000||!drive)return false;
    if(s->paused)return true;
    unsigned signals=0;
    if(!mw_pursuit_motion(&s->pursuit,s->pursuit.player_actor,source,radius,
        &signals,&w.pursuit))return false;
    w.signals=signals;
    s->tick_phase+=(uint32_t)elapsed*30u;
    bool ok=true;
    while(s->tick_phase>=1000000u){
        s->tick_phase-=1000000u;
        w.ticks++;
        bool race_ok=mw_race_ai_step(&s->race,1.f/30,drive,context,&w.race);
        bool police_ok=mw_pursuit_step(&s->pursuit,player,height,1.f/30,
            drive,context,&w.pursuit);
        if(!race_ok||!police_ok){
            s->faulted=true;
            s->simulation_ready=false;
            /* Do not spend additional callbacks on a failing frame. Preserve
             * only its fractional clock phase; no unbounded retry backlog. */
            s->tick_phase%=1000000u;
            ok=false;
            break;
        }
        s->faulted=false;
        s->simulation_ready=true;
    }
    if(work)*work=w;
    return ok;
}
bool mw_opening_actors_rank(const MwOpeningActors *s,const MwRaceProgress *p,
    const float source[3],unsigned *rank)
{
    return s&&s->running&&s->simulation_ready&&!s->faulted&&
        mw_race_ai_rank(&s->race,p,source,rank);
}
void mw_opening_actors_reset(MwOpeningActors *s)
{
    if(s)memset(s,0,sizeof(*s));
}
