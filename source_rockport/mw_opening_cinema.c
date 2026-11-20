#include "mw_opening_cinema.h"
#include "mw_nis_pose.h"
#include <math.h>
#include <stdlib.h>
#include <string.h>
static void identity(float m[16]){memset(m,0,64);m[0]=m[5]=m[10]=m[15]=1;}
static bool finite_array(const float*v,unsigned n){if(!v)return false;for(unsigned i=0;i<n;i++)if(!isfinite(v[i]))return false;return true;}
void mw_opening_cinema_close(MwOpeningCinema*c){if(!c)return;free(c->camera_bytes);mw_nis_actor_close(&c->curves);mw_nis_actions_close(&c->actions);memset(c,0,sizeof(*c));}
bool mw_opening_cinema_open(MwOpeningCinema*c,const char*camera,const char*actors,const char*actions){
    if(!c||!camera||!actors||!actions)return false;
    memset(c,0,sizeof(*c));FILE*f=fopen(camera,"rb");long size;
    if(!f)return false;
    if(fseek(f,0,SEEK_END)||(size=ftell(f))<32||size>2*1024*1024||fseek(f,0,SEEK_SET)){fclose(f);return false;}
    c->camera_bytes=malloc((size_t)size);
    bool ok=c->camera_bytes&&fread(c->camera_bytes,1,(size_t)size,f)==(size_t)size;
    fclose(f);
    if(!ok||!mw_nis_open(&c->cameras,c->camera_bytes,(size_t)size)||!mw_nis_actor_open(&c->curves,actors)||!mw_nis_actions_open(&c->actions,actions)){mw_opening_cinema_close(c);return false;}
    c->ready=true;return true;
}
typedef struct {MwOpeningNisCommand callback;void*context;const char*system;} CommandContext;
static void command(void*context,const MwNisActionCommand*cmd){CommandContext*c=context;if(c->callback)c->callback(c->context,c->system,cmd);}
static bool actor_pose(MwOpeningCinema*c,MwOpeningNisActor*a){
    float t[3],q[4],s[3]={1,1,1};
    return mw_nis_actor_sample(&c->curves,&a->translation,c->actor_frame,0,t,3)&&mw_nis_actor_sample(&c->curves,&a->quaternion,c->actor_frame,0,q,4)&&(!a->has_scale||mw_nis_actor_sample(&c->curves,&a->scale,c->actor_frame,0,s,3))&&mw_nis_pose_vehicle(s,q,t,c->rotation,c->translation,a->source_world,a->bond);
}
bool mw_opening_cinema_begin(MwOpeningCinema*c,const char*name,const float subject[16],const float origin[3],uint16_t heading,MwNisGround ground,void*ground_context,MwOpeningNisCommand cb,void*context){
    if(!c||!c->ready||!name||!ground||!finite_array(subject,16)||!finite_array(origin,3))return false;
    /* Prepare a bounded value copy; failed admission leaves previous scene. */
    MwOpeningCinema staged=*c;MwNisActorScene actor_scene;
    memset(&staged.director,0,sizeof(staged.director));memset(staged.actors,0,sizeof(staged.actors));memset(staged.systems,0,sizeof(staged.systems));
    if(!mw_nis_find(&staged.cameras,name,&staged.scene)||!mw_nis_actions_find_scene(&staged.actions,name,&staged.timing)||!mw_nis_actor_find_scene(&staged.curves,name,&actor_scene)||staged.timing.system_count>MW_OPENING_NIS_SYSTEMS||!(staged.timing.total_seconds>staged.timing.start_seconds))return false;
    MwNisDirector*d=&staged.director;memcpy(d->subject,subject,64);d->has_subject=true;d->has_scene=true;d->fix_elevation=true;d->world_queries_enabled=true;d->ground=ground;d->ground_context=ground_context;d->scene_ground_height=origin[2];
    if(!mw_nis_director_scene_frame(d->scene,origin,heading,staged.timing.scene_type)||!mw_nis_director_choose_track(d,&staged.cameras,&staged.scene,&staged.selected_track)||!mw_nis_track(&staged.cameras,&staged.scene,staged.selected_track,&staged.track))return false;
    memcpy(staged.rotation,d->scene,64);staged.rotation[12]=staged.rotation[13]=staged.rotation[14]=0;identity(staged.translation);memcpy(staged.translation+12,d->scene+12,12);
    staged.elapsed=staged.timing.start_seconds;staged.previous_step=0;staged.actor_frame=0;staged.system_count=staged.timing.system_count;staged.finished=false;staged.failed=false;staged.playing=true;
    for(unsigned i=0;i<MW_OPENING_NIS_ACTORS;i++){
        char curve[96];const char*kind=i<8?"Car":"Cop";unsigned number=i%8+1;MwOpeningNisActor*a=staged.actors+i;
        snprintf(curve,sizeof(curve),"%sZPM_%s%u_t",name,kind,number);bool t=mw_nis_actor_find_curve(&staged.curves,&actor_scene,curve,&a->translation)!=0;
        snprintf(curve,sizeof(curve),"%sZPM_%s%u_q",name,kind,number);bool q=mw_nis_actor_find_curve(&staged.curves,&actor_scene,curve,&a->quaternion)!=0;
        if(t!=q)return false;
        if(!t)continue;
        snprintf(curve,sizeof(curve),"%sZPM_%s%u_s",name,kind,number);a->has_scale=mw_nis_actor_find_curve(&staged.curves,&actor_scene,curve,&a->scale)!=0;a->present=true;
        if(!actor_pose(&staged,a))return false;
    }
    for(unsigned i=0;i<staged.system_count;i++){
        MwOpeningNisSystem*s=staged.systems+i;MwNisActionState state;MwNisActionTransition transition;
        if(!mw_nis_actions_system(&staged.actions,staged.timing.first_system+i,&s->source)||!mw_nis_actions_state(&staged.actions,&s->source,s->source.initial_state,&state)||state.filter_hash)return false;
        s->state=state.state_hash;s->elapsed=0;
        if(!mw_nis_actions_transition(&staged.actions,&state,0xa6a56ea1u,&transition))continue;
        s->state=transition.next_state_hash;if(transition.action_index==UINT32_MAX)continue;
        if(!mw_nis_actions_action(&staged.actions,transition.action_index,&s->action))return false;
        s->running=true;
    }
    *c=staged;
    for(unsigned i=0;i<c->system_count;i++){
        MwOpeningNisSystem*s=c->systems+i;if(!s->running)continue;CommandContext out={cb,context,s->source.name};
        if(mw_nis_actions_tagged(&c->actions,&s->action,0x669c6d75u,command,&out)<0||mw_nis_actions_timed(&c->actions,&s->action,-1,0,command,&out)<0){c->failed=true;c->playing=false;return false;}
    }
    return true;
}
bool mw_opening_cinema_step(MwOpeningCinema*c,float dt,MwOpeningNisCommand cb,void*context){
    if(!c||!c->ready||!c->playing||c->failed||!isfinite(dt)||dt<0||dt>1)return false;
    /* CAnimScene updates registered systems using previous mTimeStep. */
    for(unsigned i=0;i<c->system_count;i++){
        MwOpeningNisSystem*s=c->systems+i;if(!s->running)continue;float next=s->elapsed+c->previous_step;CommandContext out={cb,context,s->source.name};
        if(mw_nis_actions_timed(&c->actions,&s->action,s->elapsed,next,command,&out)<0){c->failed=true;c->playing=false;return false;}
        s->elapsed=next;
        if(s->action.duration>=0&&next>=s->action.duration&&!s->ended){if(mw_nis_actions_tagged(&c->actions,&s->action,0x4cf5d439u,command,&out)<0){c->failed=true;c->playing=false;return false;}s->ended=true;s->running=false;}
    }
    c->elapsed=c->elapsed+c->previous_step;c->previous_step=dt;
    c->actor_frame=c->actor_frame+dt*(.5f*30.0f);
    for(unsigned i=0;i<MW_OPENING_NIS_ACTORS;i++)if(c->actors[i].present&&!actor_pose(c,c->actors+i)){c->failed=true;c->playing=false;return false;}
    c->finished=c->elapsed>c->timing.total_seconds;
    return true;
}
bool mw_opening_cinema_camera(MwOpeningCinema*c,const float subject[16],MwNisCamera*out){
    if(!c||!out||!c->ready||!c->playing||c->failed||!finite_array(subject,16))return false;
    memcpy(c->director.subject,subject,64);return mw_nis_director_scene_camera(&c->director,&c->cameras,&c->track,c->elapsed,c->timing.start_seconds,c->timing.total_seconds,out);
}
void mw_opening_cinema_invalidate_ground(MwOpeningCinema*c){if(c)mw_nis_director_invalidate_ground(&c->director);}
