#ifndef MW_ALIAS_H
#define MW_ALIAS_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
/* 3DS save-format limits; not claims about original GameCube alias capacity. */
enum { MW_ALIAS_CAPACITY=16, MW_ALIAS_NAME_BYTES=32, MW_ALIAS_SAVE_BYTES=672 };
typedef struct { uint32_t id; char name[MW_ALIAS_NAME_BYTES]; } MwAlias;
typedef struct { unsigned count; uint32_t selected,last_id; MwAlias aliases[MW_ALIAS_CAPACITY]; } MwAliasStore;
bool mw_alias_create(MwAliasStore *,const char *);
bool mw_alias_rename(MwAliasStore *,uint32_t,const char *);
bool mw_alias_select(MwAliasStore *,uint32_t);
bool mw_alias_remove(MwAliasStore *,uint32_t);
const char *mw_alias_selected_name(const MwAliasStore *);
bool mw_alias_encode(const MwAliasStore *,unsigned char *,size_t);
bool mw_alias_decode(MwAliasStore *,const unsigned char *,size_t);
#endif
