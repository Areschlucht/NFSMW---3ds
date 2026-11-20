#ifndef MW_NIS_ACTIONS_H
#define MW_NIS_ACTIONS_H
#include <stdint.h>
/* Source CARPX EventSequencer data; callbacks receive original big-endian
 * event constructor argument bytes. Names/hashes preserve source identity.
 * Runtime vehicle/renderer event implementations remain caller responsibilities.
 */
typedef struct { unsigned char *data; uint32_t size,scenes,actions,systems,states,transitions,events,commands; uint32_t offsets[8]; } MwNisActions;
typedef struct { char name[48]; uint32_t index,first_action,action_count,first_system,system_count; uint32_t scene_type; int32_t start_frame,end_frame; float start_seconds,total_seconds; } MwNisActionScene;
typedef struct { char name[48]; uint32_t index,name_hash,first_event,event_count; float duration; } MwNisAction;
typedef struct { char name[32]; uint32_t index,name_hash,initial_state,default_state,first_state,state_count; } MwNisActionSystem;
typedef struct { uint32_t state_hash,filter_hash,first_transition,transition_count; } MwNisActionState;
typedef struct { uint32_t stimulus_hash,next_state_hash,action_index; } MwNisActionTransition;
typedef struct { uint32_t source_event_id; const unsigned char *arguments_be; uint32_t argument_bytes; } MwNisActionCommand;
typedef void (*MwNisActionCallback)(void *context,const MwNisActionCommand *command);
int mw_nis_actions_open(MwNisActions *a,const char *path);
void mw_nis_actions_close(MwNisActions *a);
int mw_nis_actions_find_scene(const MwNisActions*a,const char*name,MwNisActionScene*out);
int mw_nis_actions_find_action(const MwNisActions*a,const MwNisActionScene*s,const char*name,MwNisAction*out);
int mw_nis_actions_action(const MwNisActions*a,uint32_t index,MwNisAction*out);
int mw_nis_actions_find_system(const MwNisActions*a,const MwNisActionScene*s,const char*name,MwNisActionSystem*out);
int mw_nis_actions_state(const MwNisActions*a,const MwNisActionSystem*s,uint32_t state_hash,MwNisActionState*out);
int mw_nis_actions_transition(const MwNisActions*a,const MwNisActionState*s,uint32_t stimulus_hash,MwNisActionTransition*out);
/* Original FireTimedEvents uses (previous, current] and preserves source order.
 * Starting an action sets previous=-1; fire source 'start' tag before timed0.
 * These calls dispatch only data; no invented implicit scene state changes.
 * Negative return means invalid input/data; otherwise count of commands sent.
 */
int mw_nis_actions_timed(const MwNisActions*a,const MwNisAction*action,float previous,float current,MwNisActionCallback callback,void*context);
int mw_nis_actions_tagged(const MwNisActions*a,const MwNisAction*action,uint32_t source_tag_hash,MwNisActionCallback callback,void*context);
#endif
