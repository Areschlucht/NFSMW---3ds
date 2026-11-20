#include "mw_nis_actions.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
typedef struct { uint32_t count,ids[64];unsigned char first[16]; } Seen;
static void receive(void*context,const MwNisActionCommand*c){Seen*s=(Seen*)context;assert(s->count<64);s->ids[s->count++]=c->source_event_id;if(s->count==1){memcpy(s->first,c->arguments_be,c->argument_bytes<16?c->argument_bytes:16);}}
int main(int argc,char**argv){
    MwNisActions a;MwNisActionScene scene;MwNisAction action;MwNisActionSystem system;MwNisActionState state;MwNisActionTransition transition;Seen s={0};float boundary=7.446667194366455f;
    assert(argc==2);assert(mw_nis_actions_open(&a,argv[1]));assert(a.scenes==7&&a.actions==40&&a.commands==225);
    assert(mw_nis_actions_find_scene(&a,"IntroNisDD",&scene));assert(scene.scene_type==4&&scene.end_frame==1290&&scene.total_seconds==43.000003814697266f);assert(!mw_nis_actions_find_scene(&a,"intronisdd",&scene));assert(mw_nis_actions_find_scene(&a,"IntroNisDD",&scene));
    assert(mw_nis_actions_find_system(&a,&scene,"car1",&system));assert(system.initial_state==0x93bb8fb8u);
    assert(mw_nis_actions_state(&a,&system,system.initial_state,&state));assert(state.filter_hash==0);
    assert(mw_nis_actions_transition(&a,&state,0xa6a56ea1u,&transition));assert(transition.next_state_hash==0xeb9eda07u);
    assert(mw_nis_actions_action(&a,transition.action_index,&action));assert(!strcmp(action.name,"ActionCar1"));
    assert(mw_nis_actions_timed(&a,&action,-1,0,receive,&s)==1);assert(s.ids[0]==0x5e565165u);assert(s.first[7]==1);
    assert(mw_nis_actions_timed(&a,&action,0,0,receive,&s)==0);
    assert(mw_nis_actions_timed(&a,&action,0,boundary,receive,&s)==2);assert(s.ids[1]==0xa01a259bu&&s.ids[2]==0xa18e1896u);
    assert(mw_nis_actions_timed(&a,&action,boundary,boundary,receive,&s)==0);
    assert(mw_nis_actions_timed(&a,&action,NAN,boundary,receive,&s)==-1);
    memset(&s,0,sizeof(s));assert(mw_nis_actions_find_action(&a,&scene,"ActionGlobal",&action));
    assert(mw_nis_actions_tagged(&a,&action,0x08f6cb6fu,receive,&s)==2);assert(s.ids[0]==0xf699bf04u&&s.ids[1]==0x49d34ff1u);
    mw_nis_actions_close(&a);assert(a.data==NULL);puts("NIS actions: source states, payloads, ordering and interval boundaries OK");return 0;
}
