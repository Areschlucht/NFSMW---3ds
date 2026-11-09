#include "mw_event_type.h"
#include <stddef.h>
#include <string.h>
int32_t mw_event_type_from_source(const char *name)
{
    static const struct { const char *name;int32_t type; } table[]={
        {"circuit",1},{"p2p",0},{"drag",2},{"knockout",3},{"tollbooth",4},
        {"speedtrap",5},{"cashgrab",7},{"checkpointrace",6},{"challenge",8},
        {"speedtrapjump",9},{"milestonejump",10}};
    if(!name)return -1;
    for(size_t i=0;i<sizeof(table)/sizeof(*table);i++)if(!strcmp(name,table[i].name))return table[i].type;
    return -1;
}
