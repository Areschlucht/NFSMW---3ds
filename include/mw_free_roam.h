#ifndef MW_FREE_ROAM_H
#define MW_FREE_ROAM_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
enum { MW_DEST_SAFEHOUSE=1,MW_DEST_SHOP=2,MW_DEST_CARLOT=3,MW_DEST_RACE=4 };
typedef struct { const unsigned char *data;size_t bytes;uint32_t count; } MwFreeRoam;
typedef struct { uint32_t key,kind,bin,event,respawn,frontend_mode;float position[3],radius,respawn_position[3],respawn_rotation; } MwDestination;
bool mw_free_roam_open(MwFreeRoam *,const void *,size_t);
bool mw_free_roam_get(const MwFreeRoam *,uint32_t,MwDestination *);
/* Explicit 3DS interaction-prompt proximity, using the source center/radius.
   This is not the original actor narrowphase or a race checkpoint detector. */
bool mw_free_roam_near(const MwFreeRoam *,const float source_position[3],MwDestination *);
#endif
