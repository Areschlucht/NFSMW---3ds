#include "mw_story_tutorial.h"
bool mw_story_tutorial_select(int32_t type,uint32_t flags,MwStoryTutorial *out)
{
    if(!out)return false;
    uint32_t mask=0;const char *stem=0;
    switch(type){
        case 2:mask=0x40;stem="drag_tutorial";break;
        case 5:mask=0x80;stem="speedtrap_tutorial";break;
        case 4:mask=0x100;stem="tollbooth_tutorial";break;
        default:break;
    }
    if(flags&mask)stem=0;
    *out=(MwStoryTutorial){.movie_stem=stem,.profile_flags=stem?flags|mask:flags};return true;
}
