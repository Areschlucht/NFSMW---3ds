#ifndef MW_GINSU_BINDINGS_H
#define MW_GINSU_BINDINGS_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
typedef struct {const unsigned char *data;size_t bytes;uint32_t count;} MwGinsuBindings;
typedef struct {
 const char *model,*profile,*accel,*decel,*engineaudio;
 uint32_t physical_key,engineaudio_key,car_id,master_volume,accel_volume,decel_volume,flags;
 float minimum_rpm,maximum_rpm,decel_minimum_rpm,decel_maximum_rpm;
} MwGinsuBinding;
bool mw_ginsu_bindings_open(MwGinsuBindings*,const void*,size_t);
bool mw_ginsu_binding_get(const MwGinsuBindings*,uint32_t,MwGinsuBinding*);
/* Profile is authoritative original pvehicle collection name. Optional model
 * is an additional guard, never a heuristic selection among sound variants. */
bool mw_ginsu_binding_profile(const MwGinsuBindings*,const char*profile,const char*model,MwGinsuBinding*);
#endif
