#ifndef MW_EVENT_TYPE_H
#define MW_EVENT_TYPE_H
#include <stdint.h>
/* Actual original table8041D31C and getter801A7398..801A73F4.
   Strings compare case-sensitively. Unknown names remain -1. */
int32_t mw_event_type_from_source(const char *);
#endif
