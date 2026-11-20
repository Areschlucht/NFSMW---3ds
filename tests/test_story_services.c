#include "mw_story_services.h"
#include <assert.h>
#include <math.h>
int main(void){
 MwStoryEngine e;uint32_t bucket=123,number=456;
 mw_story_engine_reset(&e);
 assert(!mw_story_engine_sabotage(&e,0,0));
 assert(!mw_story_engine_sabotage(&e,0,NAN));
 assert(mw_story_engine_sabotage(&e,20,5));assert(e.deadline==25);
 assert(!mw_story_engine_sabotage(&e,21,10));
 for(int i=0;i<300;i++)assert(!mw_story_engine_tick(&e,24.99f));
 assert(mw_story_engine_tick(&e,25));assert(e.blown&&e.deadline==0);
 assert(!mw_story_engine_tick(&e,100));assert(!mw_story_engine_blow(&e));
 assert(!mw_story_engine_sabotage(&e,100,5));
 mw_story_engine_reset(&e);assert(mw_story_engine_blow(&e));assert(!mw_story_engine_tick(&e,100));
 assert(mw_story_cell_selector(10,&bucket,&number));assert(bucket==0x10000&&number==1);
 assert(mw_story_cell_selector(16,&bucket,&number));assert(bucket==0x10000&&number==64);
 assert(!mw_story_cell_selector(9,&bucket,&number));assert(bucket==0x10000&&number==64);
 return 0;
}
