#ifndef MW_EVENT_CATALOG_H
#define MW_EVENT_CATALOG_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "mw_race_progress.h"
#include "mw_story_tutorial.h"
typedef struct { const unsigned char *data; size_t bytes; uint32_t events,nodes,refs,strings,event_at,node_at,ref_at,string_at; } MwEventCatalog;
typedef struct { uint32_t key,laps,first,count,start,finish; int32_t original_type; const char *name,*region,*intro_movie,*outro_movie,*source_id; } MwEventDefinition;
typedef struct { uint32_t key,present; float position[3],rotation,dimensions[3],radius; } MwEventNode;
/* All views borrow validated immutable bytes. Failed decode leaves output intact. */
bool mw_event_catalog_open(MwEventCatalog *,const void *,size_t);
bool mw_event_catalog_get(const MwEventCatalog *,uint32_t,MwEventDefinition *);
bool mw_event_catalog_node(const MwEventCatalog *,uint32_t,MwEventNode *);
bool mw_event_catalog_find(const MwEventCatalog *,uint32_t,MwEventDefinition *);
/* Selects from the source event's verified type, without executing playback.
   Caller must satisfy the original tutorial producer's outer preconditions. */
bool mw_event_catalog_tutorial(const MwEventCatalog *,uint32_t,uint32_t,MwStoryTutorial *);
/* Copies exact original ordered keys to caller storage; no trigger/coordinate
   interpretation or automatic movie playback. Storage must outlive progress. */
bool mw_event_catalog_route(const MwEventCatalog *,uint32_t,uint32_t *,size_t,MwRaceRoute *);
#endif
