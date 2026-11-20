#include "mw_opening_actors.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static MwOpeningActors actors,before;
static void *load(const char *path,size_t *bytes)
{
    FILE *f=fopen(path,"rb");assert(f);
    assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0);rewind(f);
    void *data=malloc((size_t)n);assert(data);
    assert(fread(data,1,(size_t)n,f)==(size_t)n&&!fclose(f));
    *bytes=(size_t)n;return data;
}
typedef struct {unsigned calls,fail_on;} Drive;
static int driving(void *context,DriveState *s,float *height,DriveInput in,float dt)
{
    Drive *d=context;d->calls++;
    if(d->fail_on&&d->calls==d->fail_on){s->x+=100;*height+=100;return -1;}
    return drive_step(s,in,dt)?1:-1;
}
static void crossing(const MwPursuitTrigger *t,float from[3],float to[3])
{
    memcpy(from,t->position,12);memcpy(to,t->position,12);
    float angle=t->rotation*.017453292519943295f;
    from[0]-=cosf(angle)*4;from[1]-=sinf(angle)*4;
    to[0]+=cosf(angle)*4;to[1]+=sinf(angle)*4;
}
static void player_at(DriveState *player,const float source[3],const float origin[3])
{
    drive_reset(player,source[0]-origin[0],-source[1]-origin[2],0);
}
int main(int argc,char **argv)
{
    assert(argc==5);
    size_t n[4];void *data[4];for(unsigned i=0;i<4;i++)data[i]=load(argv[i+1],n+i);
    MwRaceAIPack pack;MwPursuitPack police;MwEventCatalog catalog;MwTrafficWorld roads;
    assert(mw_race_ai_pack_open(&pack,data[0],n[0]));
    assert(mw_pursuit_pack_open(&police,data[1],n[1]));
    assert(mw_event_catalog_open(&catalog,data[2],n[2]));
    assert(mw_traffic_open(&roads,data[3],n[3]));
    const uint32_t events[]={0x42938ce2,0xd348f2cd,0x6ddd8383,0x9f60a40e,0xf7e4440a};
    const float origin[]={-100,20,300};const uintptr_t actor=123;
    unsigned ticks=0;
    for(unsigned e=0;e<5;e++){
        float source[3]={0};
        assert(mw_opening_actors_begin(&actors,&pack,&police,&catalog,&roads,
            events[e],origin,actor,source));
        assert(actors.race.route.checkpoints==actors.race.checkpoints);
        for(unsigned i=0;i<actors.race.count;i++)
            assert(actors.race.actors[i].progress.route.checkpoints==actors.race.checkpoints);
        unsigned rank=999;MwRaceProgress progress;
        assert(mw_race_begin(&progress,&actors.race.route));
        assert(!mw_opening_actors_rank(&actors,&progress,source,&rank)&&rank==999);
        assert(!mw_opening_actors_start(&actors));
        for(unsigned i=0;i<actors.race.count;i++)
            assert(mw_opening_actors_admit_racer(&actors,i,true));
        if(e==2||e==4){
            assert(actors.pursuit.has_event&&!mw_opening_actors_start(&actors));
            assert(mw_opening_actors_admit_police(&actors,true));
        }else assert(!actors.pursuit.has_event);
        assert(mw_opening_actors_start(&actors));
        assert(!mw_opening_actors_rank(&actors,&progress,source,&rank));
        assert(!mw_opening_actors_admit_racer(&actors,0,false));
        assert(!mw_opening_actors_admit_police(&actors,false));

        DriveState player={0};player_at(&player,source,origin);
        Drive drive={0};MwOpeningActorsWork work={0};
        assert(mw_opening_actors_update(&actors,&player,-20,source,1,16666,
            driving,&drive,&work));
        assert(!work.ticks&&!drive.calls);
        assert(!mw_opening_actors_rank(&actors,&progress,source,&rank));
        assert(mw_opening_actors_update(&actors,&player,-20,source,1,16667,
            driving,&drive,&work));
        assert(!work.ticks&&!drive.calls);
        assert(mw_opening_actors_update(&actors,&player,-20,source,1,1,
            driving,&drive,&work));
        assert(work.ticks==1&&drive.calls==actors.race.count);
        ticks+=work.ticks;
        assert(mw_opening_actors_rank(&actors,&progress,source,&rank));

        /* Even a synthetic finished player cannot receive a result while
         * NPC rendering/admission or an authoritative physical tick is absent. */
        progress.finished=true;progress.elapsed_us=0;
        drive.calls=0;drive.fail_on=1;
        assert(!mw_opening_actors_update(&actors,&player,-20,source,1,33334,
            driving,&drive,&work));
        assert(actors.faulted&&!actors.simulation_ready);
        rank=999;assert(!mw_opening_actors_rank(&actors,&progress,source,&rank)&&rank==999);
        drive.calls=0;drive.fail_on=0;
        assert(mw_opening_actors_update(&actors,&player,-20,source,1,33334,
            driving,&drive,&work));
        assert(!actors.faulted&&actors.simulation_ready);
        assert(mw_opening_actors_rank(&actors,&progress,source,&rank));

        MwPursuitTrigger spawn={0};float from[3],to[3];
        if(actors.pursuit.has_event){
            assert(mw_pursuit_trigger_get(&actors.pursuit,0,&spawn));
            crossing(&spawn,from,to);
            assert(mw_opening_actors_relocate(&actors,from));
            player_at(&player,to,origin);
        }else memcpy(to,source,12);
        assert(mw_opening_actors_pause(&actors,true));before=actors;
        drive.calls=0;
        assert(mw_opening_actors_update(&actors,&player,-20,to,1,100000,
            driving,&drive,&work));
        assert(!work.ticks&&!work.signals&&!drive.calls&&!memcmp(&before,&actors,sizeof actors));
        assert(mw_opening_actors_pause(&actors,false));
        assert(mw_opening_actors_update(&actors,&player,to[2]-origin[1],to,1,100000,
            driving,&drive,&work));
        assert(work.ticks==3&&work.race.drive_calls<=9&&work.pursuit.drive_calls<=6);
        if(actors.pursuit.has_event){
            assert(work.signals==MW_PURSUIT_SPAWN&&actors.pursuit.pursuit_active);
            assert(actors.pursuit.actors[0].active&&actors.pursuit.actors[1].active);
            assert(work.pursuit.drive_calls==6);
            /* A failed second cop callback also prevents a result even when
             * all racing opponents completed their physical tick. */
            drive.calls=0;drive.fail_on=actors.race.count+2;
            assert(!mw_opening_actors_update(&actors,&player,to[2]-origin[1],to,1,33334,
                driving,&drive,&work));
            assert(actors.faulted&&!mw_opening_actors_rank(&actors,&progress,to,&rank));
            drive.calls=0;drive.fail_on=0;
            assert(mw_opening_actors_update(&actors,&player,to[2]-origin[1],to,1,33334,
                driving,&drive,&work));
            assert(mw_opening_actors_rank(&actors,&progress,to,&rank));
            /* Relocation discards a teleport sweep. It cannot manufacture a
             * source bail event along the skipped path. */
            MwPursuitTrigger bail;
            assert(mw_pursuit_trigger_get(&actors.pursuit,1,&bail));
            crossing(&bail,from,to);
            assert(mw_opening_actors_relocate(&actors,to));
            player_at(&player,to,origin);
            assert(mw_opening_actors_update(&actors,&player,to[2]-origin[1],to,1,0,
                driving,&drive,&work)&&!work.signals&&!actors.pursuit.no_new_pursuits);
        }
        unsigned second_ticks=0;uint32_t phase=actors.tick_phase;
        for(unsigned i=0;i<10;i++){
            assert(mw_opening_actors_update(&actors,&player,to[2]-origin[1],to,1,100000,
                driving,&drive,&work));
            second_ticks+=work.ticks;
            assert(work.ticks<=3&&work.race.drive_calls<=9&&work.pursuit.drive_calls<=6);
            assert(!work.race.planner_nodes&&!work.race.planner_edges&&!work.race.nearest_nodes);
        }
        assert(second_ticks==30&&phase==actors.tick_phase);
        before=actors;
        assert(!mw_opening_actors_begin(&actors,&pack,&police,&catalog,&roads,
            0xdeadbeef,origin,actor,source));
        assert(!memcmp(&before,&actors,sizeof actors));
        assert(!mw_opening_actors_update(&actors,&player,0,source,1,100001,
            driving,&drive,&work)&&!memcmp(&before,&actors,sizeof actors));
        mw_opening_actors_reset(&actors);
        assert(!actors.prepared&&!actors.running&&!actors.race.count);
        assert(!mw_opening_actors_rank(&actors,&progress,source,&rank));
    }
    for(unsigned i=0;i<4;i++)free(data[i]);
    printf("Opening actors: five events, %u first admitted ticks, police model/trigger guards, bounded30Hz clocks, pause/relocation and failed-motion result rejection passed.\n",ticks);
    return 0;
}
