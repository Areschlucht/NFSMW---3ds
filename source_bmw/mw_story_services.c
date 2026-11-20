#include "mw_story_services.h"
#include <math.h>
void mw_story_engine_reset(MwStoryEngine *e){if(e){e->deadline=0.0f;e->blown=0;}}
int mw_story_engine_sabotage(MwStoryEngine *e,float clock,float delay){
    /* Original finite input domain; reject invalid native service input. */
    if(!e||!isfinite(clock)||!isfinite(delay)||e->deadline>0.0f||e->blown||delay<=0.000001f)return 0;
    e->deadline=clock+delay;return 1;
}
int mw_story_engine_blow(MwStoryEngine *e){
    if(!e||e->blown)return 0;
    e->blown=1;e->deadline=0.0f;return 1;
}
int mw_story_engine_tick(MwStoryEngine *e,float clock){
    if(!e||!isfinite(clock)||e->deadline<=0.0f)return 0;
    if(e->deadline-clock>0.0f)return 0;
    e->deadline=0.0f;return mw_story_engine_blow(e);
}
int mw_story_cell_selector(int id,uint32_t *bucket,uint32_t *number){
    if(!bucket||!number)return 0;
    static const unsigned char lo[17]={10,17,23,30,37,42,47,53,58,64,70,73,77,80,85,89,97};
    static const unsigned char hi[17]={16,22,29,36,41,46,52,57,63,69,72,76,79,84,88,96,105};
    for(unsigned i=0;i<17;i++)if(id>=lo[i]&&id<=hi[i]){
        *bucket=1u<<(16-i);*number=1u<<(id-lo[i]);return 1;
    }
    return 0;
}
