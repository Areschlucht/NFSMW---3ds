#include "mw_playable_race.h"
#include <math.h>
#include <string.h>

static bool point_valid(const float p[3])
{ return p&&isfinite(p[0])&&isfinite(p[1])&&isfinite(p[2]); }
static bool gate_valid(const MwEventNode *n)
{
    if(!n||(n->present&1u)==0||!point_valid(n->position))return false;
    if(n->present&8u)return isfinite(n->radius)&&n->radius>0;
    if((n->present&6u)!=6u||!isfinite(n->rotation))return false;
    for(unsigned i=0;i<3;i++)if(!isfinite(n->dimensions[i])||n->dimensions[i]<=0)return false;
    return true;
}
static void local_point(const MwEventNode *n,const float p[3],double out[3])
{
    double angle=-(double)remainderf(n->rotation,360.0f)*0.017453292519943295;
    double c=cos(angle),s=sin(angle);
    /* Original internal basis is (-sourceY,sourceZ,sourceX). Apply inverse yaw. */
    double x=(double)n->position[1]-p[1],z=(double)p[0]-n->position[0];
    out[0]=c*x-s*z;out[1]=(double)p[2]-n->position[2];out[2]=s*x+c*z;
}
static bool sweep(const MwEventNode *n,const float a[3],const float b[3],float radius,
                  double cursor,double *entry)
{
    if(!gate_valid(n)||!point_valid(a)||!point_valid(b)||!isfinite(radius)||radius<0)return false;
    if(n->present&8u){
        double d[3],v[3],rr=(double)n->radius+radius,qa=0,qb=0,qc=-rr*rr;
        for(unsigned i=0;i<3;i++){
            d[i]=(double)a[i]-n->position[i];v[i]=(double)b[i]-a[i];
            qa+=v[i]*v[i];qb+=d[i]*v[i];qc+=d[i]*d[i];
        }
        double at=qc+2*qb*cursor+qa*cursor*cursor;
        if(at<=0||qa==0)return false;
        double disc=qb*qb-qa*qc;if(disc<0)return false;
        double t=(-qb-sqrt(disc))/qa;
        if(t<cursor||t>1)return false;
        *entry=t;return true;
    }
    double p[3],q[3];local_point(n,a,p);local_point(n,b,q);
    double half[3]={(double)n->dimensions[1]*.5+radius,
                    (double)n->dimensions[2]+radius,(double)n->dimensions[0]*.5+radius};
    double enter=cursor,leave=1;bool inside=true;
    for(unsigned i=0;i<3;i++){
        double v=q[i]-p[i],at=p[i]+v*cursor;
        if(at < -half[i] || at > half[i])inside=false;
        if(v==0){if(p[i] < -half[i] || p[i] > half[i])return false;continue;}
        double lo=(-half[i]-p[i])/v,hi=(half[i]-p[i])/v;
        if(lo>hi){double t=lo;lo=hi;hi=t;}
        if(lo>enter)enter=lo;
        if(hi<leave)leave=hi;
        if(enter>leave)return false;
    }
    if(inside||enter<cursor||enter>1||leave<cursor)return false;
    *entry=enter;return true;
}
bool mw_playable_race_sweep(const MwEventNode *n,const float a[3],const float b[3],
                           float radius,double *entry)
{
    if(!entry)return false;
    return sweep(n,a,b,radius,0,entry);
}
bool mw_playable_race_width_sweep(const MwEventNode *pose,float width,const float a[3],
                                 const float b[3],float radius,double *entry)
{
    if(!pose||!entry||(pose->present&3u)!=3u||(pose->present&12u)||!isfinite(width)||width<=0)return false;
    MwEventNode box=*pose;box.present|=4u;
    box.dimensions[0]=1;box.dimensions[1]=width;box.dimensions[2]=50;
    return sweep(&box,a,b,radius,0,entry);
}
static bool terminal(MwPlayableRacePhase phase)
{ return phase==MW_PLAYABLE_EMPTY||phase==MW_PLAYABLE_FINISHED||phase==MW_PLAYABLE_CANCELLED; }
bool mw_playable_race_prepare(MwPlayableRace *r,MwRaceSession *s,const MwEventCatalog *c,
    uint32_t key,const MwAliasStore *aliases,uintptr_t actor,float radius)
{
    if(!r||!s||!c||!terminal(r->phase)||!isfinite(radius)||radius<0)return false;
    MwEventDefinition e;MwEventNode node;uint32_t keys[1024];MwRaceRoute route;
    if(!mw_event_catalog_find(c,key,&e)||(e.original_type!=0&&e.original_type!=1)||
       !mw_event_catalog_route(c,key,keys,1024,&route)||
       !mw_event_catalog_node(c,e.start,&node)||(node.present&3u)!=3u||
       !point_valid(node.position)||!isfinite(node.rotation))return false;
    for(size_t i=0;i<=route.count;i++){
        if(!mw_event_catalog_node(c,i==route.count?route.finish:keys[i],&node)||!gate_valid(&node))return false;
    }
    if(!mw_race_session_prepare(s,c,key,aliases,actor))return false;
    *r=(MwPlayableRace){.session=s,.catalog=c,.phase=MW_PLAYABLE_LOADING,.actor_radius=radius};
    return true;
}
bool mw_playable_race_admit(MwPlayableRace *r,bool render,bool collision,bool activation)
{
    if(!r||r->phase!=MW_PLAYABLE_LOADING||!mw_race_session_admit(r->session,render,collision,activation))return false;
    r->phase=MW_PLAYABLE_READY;return true;
}
bool mw_playable_race_countdown(MwPlayableRace *r,uint64_t duration,const float position[3])
{
    if(!r||r->phase!=MW_PLAYABLE_READY||!point_valid(position))return false;
    if(!duration&&!mw_race_session_start(r->session))return false;
    memcpy(r->previous_source,position,sizeof(r->previous_source));
    r->countdown_us=duration;r->phase=duration?MW_PLAYABLE_COUNTDOWN:MW_PLAYABLE_RUNNING;
    return true;
}
bool mw_playable_race_next(const MwPlayableRace *r,MwEventNode *out)
{
    if(!r||!r->session||!r->catalog||!out||terminal(r->phase))return false;
    const MwRaceSession *s=r->session;
    size_t next=(s->phase==MW_SESSION_RUNNING||s->phase==MW_SESSION_PAUSED)?s->progress.next:0;
    uint32_t key=next<s->route.count?s->checkpoint_keys[next]:s->route.finish;
    return mw_event_catalog_node(r->catalog,key,out);
}
static uint64_t at_time(uint64_t span,double fraction)
{
    if(fraction<=0)return 0;
    if(fraction>=1)return span;
    double time=(double)span*fraction;
    return time>=(double)span?span:(uint64_t)time;
}
bool mw_playable_race_update(MwPlayableRace *r,uintptr_t actor,const float position[3],
                            uint64_t dt,MwPlayableRaceUpdate *out)
{
    if(!r||!r->session||!out||!point_valid(position)||!actor||actor!=r->session->player_actor||
       (r->phase!=MW_PLAYABLE_COUNTDOWN&&r->phase!=MW_PLAYABLE_RUNNING))return false;
    MwPlayableRaceUpdate result={0};
    if(r->phase==MW_PLAYABLE_COUNTDOWN){
        if(dt<r->countdown_us){r->countdown_us-=dt;*out=result;return true;}
        uint64_t running=dt-r->countdown_us;
        if(!mw_race_session_start(r->session))return false;
        r->countdown_us=0;r->phase=MW_PLAYABLE_RUNNING;
        memcpy(r->previous_source,position,sizeof(r->previous_source));result.started=true;
        /* No driving sweep across frozen countdown time. The next update owns
           the first movement; retain only its unconsumed running-clock tail. */
        if(!mw_race_session_tick(r->session,running))return false;
        *out=result;return true;
    }
    MwRaceSession *s=r->session;
    if(!dt){
        for(unsigned i=0;i<3;i++)if(position[i]!=r->previous_source[i])return false;
        *out=result;return true;
    }
    if(UINT64_MAX-s->progress.elapsed_us<dt)return false;
    MwPlayableRace saved=*r;MwRaceProgress saved_progress=s->progress;MwRaceSessionPhase saved_phase=s->phase;
    double cursor=0;uint64_t timed=0;
    /* One straight movement cannot legitimately complete repeated laps. This
       also bounds work even for a malformed route with repeated/overlap gates. */
    for(size_t visits=0;visits<=s->route.count;visits++){
        MwEventNode node;double hit;
        if(!mw_playable_race_next(r,&node))goto failure;
        if(!sweep(&node,r->previous_source,position,r->actor_radius,cursor,&hit))break;
        /* Coincident/duplicate next gates need a distinct later entry. Avoid
           numerical boundary roundoff counting the very same contact twice. */
        if(result.crossed&&hit<=cursor)break;
        uint64_t now=at_time(dt,hit);
        if(now<timed||!mw_race_session_tick(s,now-timed))goto failure;
        timed=now;
        MwRaceEvent event=mw_race_session_enter(s,actor,node.key);
        if(event==MW_RACE_IGNORED)goto failure;
        result.event=event;result.gate=node.key;result.crossed++;r->last_gate=node.key;
        cursor=hit;
        if(event==MW_RACE_FINISHED){
            r->phase=MW_PLAYABLE_FINISHED;result.finished=true;result.finish_fraction=hit;break;
        }
    }
    if(r->phase==MW_PLAYABLE_RUNNING&&!mw_race_session_tick(s,dt-timed))goto failure;
    memcpy(r->previous_source,position,sizeof(r->previous_source));*out=result;return true;
failure:
    *r=saved;s->progress=saved_progress;s->phase=saved_phase;return false;
}
bool mw_playable_race_pause(MwPlayableRace *r)
{
    if(!r||(r->phase!=MW_PLAYABLE_RUNNING&&r->phase!=MW_PLAYABLE_COUNTDOWN))return false;
    if(r->phase==MW_PLAYABLE_RUNNING&&!mw_race_session_pause(r->session))return false;
    r->resume_phase=r->phase;r->phase=MW_PLAYABLE_PAUSED;return true;
}
bool mw_playable_race_relocate(MwPlayableRace *r,uintptr_t actor,const float position[3])
{
    if(!r||!r->session||!actor||actor!=r->session->player_actor||
       (r->phase!=MW_PLAYABLE_RUNNING&&r->phase!=MW_PLAYABLE_COUNTDOWN)||!point_valid(position))return false;
    memcpy(r->previous_source,position,sizeof(r->previous_source));return true;
}
bool mw_playable_race_resume(MwPlayableRace *r)
{
    if(!r||r->phase!=MW_PLAYABLE_PAUSED)return false;
    if(r->resume_phase==MW_PLAYABLE_RUNNING&&!mw_race_session_resume(r->session))return false;
    r->phase=r->resume_phase;return true;
}
bool mw_playable_race_cancel(MwPlayableRace *r)
{
    if(!r||terminal(r->phase)||!mw_race_session_cancel(r->session))return false;
    r->phase=MW_PLAYABLE_CANCELLED;return true;
}
static bool pose(const MwEventNode *n,float position[3],float *yaw)
{
    if(!n||!position||!yaw||(n->present&3u)!=3u||!point_valid(n->position)||!isfinite(n->rotation))return false;
    memcpy(position,n->position,sizeof(n->position));
    *yaw=remainderf(90.0f+remainderf(n->rotation,360.0f),360.0f)*0.017453292519943295f;
    return true;
}
bool mw_playable_race_start_pose(const MwPlayableRace *r,float position[3],float *yaw)
{ return r&&r->session&&pose(&r->session->source_start,position,yaw); }
bool mw_playable_race_recovery_pose(const MwPlayableRace *r,float position[3],float *yaw)
{
    if(!r||!r->session)return false;
    MwEventNode n;
    if(r->last_gate&&mw_event_catalog_node(r->catalog,r->last_gate,&n))return pose(&n,position,yaw);
    return pose(&r->session->source_start,position,yaw);
}
