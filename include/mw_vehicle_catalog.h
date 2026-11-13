#ifndef MW_VEHICLE_CATALOG_H
#define MW_VEHICLE_CATALOG_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
/* Borrowed immutable NVC1 view. Catalog presence does not imply career unlock. */
typedef struct { const unsigned char *data;size_t bytes;uint32_t count; } MwVehicleCatalog;
typedef struct {
    const char *id,*display_name;
    uint32_t frontend_key,ecar_key,body_crc,wheel_crc;
    float half_extent;
} MwVehicleSpec;
bool mw_vehicle_catalog_open(MwVehicleCatalog *,const void *,size_t);
bool mw_vehicle_catalog_get(const MwVehicleCatalog *,uint32_t,MwVehicleSpec *);
bool mw_vehicle_catalog_find_id(const MwVehicleCatalog *,const char *,MwVehicleSpec *);
bool mw_vehicle_catalog_find_frontend(const MwVehicleCatalog *,uint32_t,MwVehicleSpec *);
#endif
