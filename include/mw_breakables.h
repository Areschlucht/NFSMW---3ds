#ifndef MW_BREAKABLES_H
#define MW_BREAKABLES_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
typedef struct {
    const unsigned char *data;size_t bytes;
    uint32_t count,state_count,grid_at,refs_at,columns,rows,refs;
    float min_x,min_z,cell;
} MwBreakables;
typedef struct {
    uint32_t source_instance_offset,source_parameter_offset,member,attribute_key;
    uint32_t logical_section,original_flags,blueprint_key,dynamic_collision_key;
    float mass,source_scalar_be71dbad,bounds_viewer[6],translation_viewer[3];
    uint32_t source_bool_1f989f01,source_bool_6f002423,event_sequencer_key;
} MwBreakable;
typedef struct { uint32_t index,source_instance_offset,member;double fraction;float point_viewer[3]; } MwBreakableHit;
typedef bool (*MwBreakableAdmitted)(void *,uint32_t source_instance_offset,uint32_t original_flags);
/* Source-bound immutable NBP1. State is a separate caller-owned byte per
   original scenery member; every duplicate provider shares that one state. */
bool mw_breakables_open(MwBreakables *,const void *,size_t);
bool mw_breakables_get(const MwBreakables *,uint32_t index,MwBreakable *);
bool mw_breakables_find(const MwBreakables *,uint32_t source_instance_offset,uint32_t *index);
bool mw_breakables_reset(const MwBreakables *,unsigned char *states,size_t capacity);
bool mw_breakables_activate(const MwBreakables *,unsigned char *states,size_t capacity,uint32_t index);
bool mw_breakables_active(const MwBreakables *,const unsigned char *states,size_t capacity,uint32_t source_instance_offset);
/* Practical native hit candidate, NOT original smackable rigid-body collision.
   Viewer-world coordinates=(sourceX,sourceZ,-sourceY), before local rebase.
   Swept point vs source render bounds expanded by proxy radius; closest intact
   admitted prop only. Caller supplies actual activation/damage/visual policy;
   source0xBE71DBAD is deliberately not assumed to be a damage threshold.
   No state change, SD read or allocation; failure/no-hit leaves hit untouched.
   NULL admitted uses cold normal-render bit0x10 visibility. */
bool mw_breakables_sweep(const MwBreakables *,const unsigned char *states,size_t capacity,
    const float from_viewer[3],const float to_viewer[3],float radius,
    MwBreakableAdmitted admitted,void *context,MwBreakableHit *);
#endif
