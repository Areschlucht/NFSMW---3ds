#ifndef MW_WORLD_STATE_H
#define MW_WORLD_STATE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
/* Shared immutable absolute source plan. Version2 adds an explicit event key
   and the independently verified0x400 matrix reflection; no warm state inferred. */
typedef struct { const unsigned char *data;size_t bytes;uint32_t bin,context,count,groups_at,overrides_at,version,event; } MwWorldState;
bool mw_world_state_open(MwWorldState *,const void *,size_t);
bool mw_world_state_source_matches(const MwWorldState *,const unsigned char source_sha256[32]);
bool mw_world_state_instance(void *,uint32_t source_offset,uint32_t original_flags,uint32_t *effective_flags);
/* Exact original CI group0 bypass; positive active,0 inactive,-1 malformed. */
int mw_world_state_group(void *,uint16_t group);
#endif
