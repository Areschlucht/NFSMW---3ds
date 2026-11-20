#include "mw_nis_actions.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static uint32_t rd(const unsigned char*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static float rf(const unsigned char*p){uint32_t x=rd(p);float f;memcpy(&f,&x,4);return f;}
static const unsigned char*record(const MwNisActions*a,uint32_t table,uint32_t i){
    const uint32_t stride[7]={96,64,64,16,12,16,12};uint32_t n[7];
    if(!a||!a->data||table>=7)return NULL;
    n[0]=a->scenes;n[1]=a->actions;n[2]=a->systems;n[3]=a->states;n[4]=a->transitions;n[5]=a->events;n[6]=a->commands;
    if(i>=n[table])return NULL;
    return a->data+a->offsets[table]+stride[table]*i;
}
void mw_nis_actions_close(MwNisActions*a){if(a){free(a->data);memset(a,0,sizeof(*a));}}
int mw_nis_actions_open(MwNisActions*a,const char*path){
    FILE*f;long size;unsigned char h[80];uint32_t i,n[7],stride[7]={96,64,64,16,12,16,12};
    if(!a||!path)return 0;
    memset(a,0,sizeof(*a));f=fopen(path,"rb");if(!f)return 0;
    if(fseek(f,0,SEEK_END)||(size=ftell(f))<80||size>2*1024*1024||fseek(f,0,SEEK_SET)||fread(h,1,80,f)!=80)goto fail;
    if(memcmp(h,"NAC1",4)||rd(h+4)!=1||rd(h+68)!=(uint32_t)size)goto fail;
    a->size=(uint32_t)size;
    for(i=0;i<7;i++){n[i]=rd(h+8+4*i);if(n[i]>65536)goto fail;}
    for(i=0;i<8;i++){a->offsets[i]=rd(h+36+4*i);if(a->offsets[i]>a->size)goto fail;}
    if(a->offsets[0]!=80)goto fail;
    for(i=0;i<7;i++)if(a->offsets[i+1]!=a->offsets[i]+n[i]*stride[i])goto fail;
    a->scenes=n[0];a->actions=n[1];a->systems=n[2];a->states=n[3];a->transitions=n[4];a->events=n[5];a->commands=n[6];
    a->data=(unsigned char*)malloc(a->size);if(!a->data||fseek(f,0,SEEK_SET)||fread(a->data,1,a->size,f)!=a->size)goto fail;
    fclose(f);return 1;
fail:fclose(f);mw_nis_actions_close(a);return 0;
}
int mw_nis_actions_find_scene(const MwNisActions*a,const char*name,MwNisActionScene*out){
    uint32_t i;const unsigned char*p;if(!a||!name||!out)return 0;
    for(i=0;i<a->scenes;i++){p=record(a,0,i);if(!p||!memchr(p,0,48))return 0;if(strcmp(name,(const char*)p))continue;
        memset(out,0,sizeof(*out));memcpy(out->name,p,48);out->index=i;out->first_action=rd(p+48);out->action_count=rd(p+52);out->first_system=rd(p+56);out->system_count=rd(p+60);out->scene_type=rd(p+64);out->start_frame=(int32_t)rd(p+68);out->end_frame=(int32_t)rd(p+72);out->start_seconds=rf(p+76);out->total_seconds=rf(p+80);
        return isfinite(out->start_seconds)&&isfinite(out->total_seconds)&&out->total_seconds>=out->start_seconds&&out->first_action<=a->actions&&out->action_count<=a->actions-out->first_action&&out->first_system<=a->systems&&out->system_count<=a->systems-out->first_system;
    }return 0;
}
int mw_nis_actions_action(const MwNisActions*a,uint32_t index,MwNisAction*out){
    const unsigned char*p=record(a,1,index);if(!p||!out||!memchr(p,0,48))return 0;
    memset(out,0,sizeof(*out));memcpy(out->name,p,48);out->index=index;out->name_hash=rd(p+48);out->duration=rf(p+52);out->first_event=rd(p+56);out->event_count=rd(p+60);
    return isfinite(out->duration)&&out->first_event<=a->events&&out->event_count<=a->events-out->first_event;
}
int mw_nis_actions_find_action(const MwNisActions*a,const MwNisActionScene*s,const char*name,MwNisAction*out){
    uint32_t i;if(!a||!s||!name||!out||s->first_action>a->actions||s->action_count>a->actions-s->first_action)return 0;
    for(i=0;i<s->action_count;i++){if(!mw_nis_actions_action(a,s->first_action+i,out))return 0;if(!strcmp(name,out->name))return 1;}return 0;
}
int mw_nis_actions_system(const MwNisActions*a,uint32_t index,MwNisActionSystem*out){
    const unsigned char*p=record(a,2,index);if(!p||!out||!memchr(p,0,32))return 0;
    memset(out,0,sizeof(*out));memcpy(out->name,p,32);out->index=index;out->name_hash=rd(p+32);out->initial_state=rd(p+36);out->default_state=rd(p+40);out->first_state=rd(p+44);out->state_count=rd(p+48);
    return out->first_state<=a->states&&out->state_count<=a->states-out->first_state;
}
int mw_nis_actions_find_system(const MwNisActions*a,const MwNisActionScene*s,const char*name,MwNisActionSystem*out){
    uint32_t i;if(!a||!s||!name||!out||s->first_system>a->systems||s->system_count>a->systems-s->first_system)return 0;
    for(i=0;i<s->system_count;i++){if(!mw_nis_actions_system(a,s->first_system+i,out))return 0;if(!strcmp(name,out->name))return 1;}return 0;
}
int mw_nis_actions_state(const MwNisActions*a,const MwNisActionSystem*s,uint32_t key,MwNisActionState*out){
    uint32_t i;const unsigned char*p;if(!a||!s||!out||s->first_state>a->states||s->state_count>a->states-s->first_state)return 0;
    for(i=0;i<s->state_count;i++){p=record(a,3,s->first_state+i);if(!p)return 0;if(rd(p)!=key)continue;out->state_hash=key;out->filter_hash=rd(p+4);out->first_transition=rd(p+8);out->transition_count=rd(p+12);return out->first_transition<=a->transitions&&out->transition_count<=a->transitions-out->first_transition;}return 0;
}
int mw_nis_actions_transition(const MwNisActions*a,const MwNisActionState*s,uint32_t key,MwNisActionTransition*out){
    uint32_t i;const unsigned char*p;if(!a||!s||!out||s->first_transition>a->transitions||s->transition_count>a->transitions-s->first_transition)return 0;
    for(i=0;i<s->transition_count;i++){p=record(a,4,s->first_transition+i);if(!p)return 0;if(rd(p)!=key)continue;out->stimulus_hash=key;out->next_state_hash=rd(p+4);out->action_index=rd(p+8);return out->action_index==UINT32_MAX||out->action_index<a->actions;}return 0;
}
static int dispatch(const MwNisActions*a,const unsigned char*p,MwNisActionCallback cb,void*ctx){
    uint32_t first=rd(p+8),count=rd(p+12),i;MwNisActionCommand command;const unsigned char*c;uint32_t off;
    if(first>a->commands||count>a->commands-first)return -1;
    for(i=0;i<count;i++){c=record(a,6,first+i);if(!c)return -1;command.source_event_id=rd(c);off=rd(c+4);command.argument_bytes=rd(c+8);if(off<a->offsets[7]||off>a->size||command.argument_bytes>a->size-off)return -1;command.arguments_be=a->data+off;cb(ctx,&command);}return (int)count;
}
int mw_nis_actions_timed(const MwNisActions*a,const MwNisAction*action,float previous,float current,MwNisActionCallback cb,void*ctx){
    uint32_t i;int total=0,n;const unsigned char*p;float time;if(!a||!action||!cb||!isfinite(previous)||!isfinite(current)||current<previous||action->first_event>a->events||action->event_count>a->events-action->first_event)return -1;
    for(i=0;i<action->event_count;i++){p=record(a,5,action->first_event+i);if(!p)return -1;if(rd(p))continue;time=rf(p+4);if(!isfinite(time))return -1;if(time>previous&&time<=current){n=dispatch(a,p,cb,ctx);if(n<0)return -1;total+=n;}}return total;
}
int mw_nis_actions_tagged(const MwNisActions*a,const MwNisAction*action,uint32_t key,MwNisActionCallback cb,void*ctx){
    uint32_t i;int n;const unsigned char*p;if(!a||!action||!cb||action->first_event>a->events||action->event_count>a->events-action->first_event)return -1;
    for(i=0;i<action->event_count;i++){p=record(a,5,action->first_event+i);if(!p)return -1;if(rd(p)==1&&rd(p+4)==key){n=dispatch(a,p,cb,ctx);return n;}}return 0;
}
