#include "mw_opening_cinema.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
static bool ground(void*ctx,const float point[3],float*height){(void)point;*height=*(float*)ctx;return true;}
static unsigned commands;
static void dispatch(void*ctx,const char*system,const MwNisActionCommand*command){(void)ctx;assert(system&&*system&&command->source_event_id);assert(command->arguments_be||!command->argument_bytes);commands++;}
int main(int argc,char**argv){
    assert(argc==4);MwOpeningCinema c={0};assert(mw_opening_cinema_open(&c,argv[1],argv[2],argv[3]));
    assert(!c.curves.file&&c.curves.data&&c.actions.data&&c.cameras.data);
    const char*names[]={"GenericStart","IntroNis04","IntroNis05","IntroNis10","IntroNisDD","EndingNis03","IntroNisDDEnd"};
    const float totals[]={6.000000476837158f,9.666666984558105f,6.000000476837158f,15.000000953674316f,43.000003814697266f,27.700000762939453f,3.3333334922790527f};
    float origin[3]={123.25f,456.5f,92},subject[16],height=92;
    assert(mw_nis_director_scene_frame(subject,origin,16384,0));
    unsigned frames=0,actors=0;
    for(unsigned scene=0;scene<6;scene++){
        assert(mw_opening_cinema_begin(&c,names[scene],subject,origin,16384,ground,&height,dispatch,NULL));
        assert(c.timing.total_seconds==totals[scene]);
        assert(c.elapsed==0&&c.actor_frame==0&&!c.finished&&!c.failed);
        unsigned present=0;for(unsigned i=0;i<16;i++)if(c.actors[i].present){present++;for(unsigned j=0;j<16;j++)assert(isfinite(c.actors[i].source_world[j]));}assert(present);actors+=present;
        if(scene==4){assert(c.timing.scene_type==4);assert(c.actors[0].source_world[12]==1046.3294677734375f);assert(c.actors[0].source_world[13]==99.03913879394531f);}
        MwNisCamera camera;assert(mw_opening_cinema_camera(&c,subject,&camera));
        assert(mw_opening_cinema_step(&c,1.0f/60,dispatch,NULL));assert(c.elapsed==0&&c.actor_frame==.25f);
        assert(mw_opening_cinema_camera(&c,subject,&camera));frames++;
        float prior=c.elapsed,frame=c.actor_frame;assert(!mw_opening_cinema_step(&c,NAN,dispatch,NULL));assert(!mw_opening_cinema_step(&c,-1,dispatch,NULL));assert(c.elapsed==prior&&c.actor_frame==frame);
        while(!c.finished){assert(mw_opening_cinema_step(&c,1.0f/60,dispatch,NULL));assert(mw_opening_cinema_camera(&c,subject,&camera));frames++;assert(frames<20000);}
        assert(c.elapsed>c.timing.total_seconds);
    }
    assert(commands>100&&actors>16);
    MwOpeningCinema before=c;assert(!mw_opening_cinema_begin(&c,names[6],subject,origin,0,ground,&height,dispatch,NULL));assert(!memcmp(&before,&c,sizeof(c)));assert(!mw_opening_cinema_begin(&c,"missing",subject,origin,0,ground,&height,dispatch,NULL));assert(!memcmp(&before,&c,sizeof(c)));
    mw_opening_cinema_close(&c);assert(!c.ready&&!c.camera_bytes&&!c.curves.data&&!c.actions.data);
    printf("Opening cinema: six genuine camera scenes, %u actor slots, %u clock/camera frames, %u source commands, transactional admission and cleanup pass\n",actors,frames,commands);return 0;
}
