#include "mw_nis_director.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static bool identity(void *p,uint8_t mode,bool target,const float in[3],float out[3]){(void)p;(void)mode;(void)target;memcpy(out,in,12);return true;}
static unsigned ground_queries;
static bool flat(void *p,const float point[3],float *height){(void)point;ground_queries++;*height=*(const float*)p;return true;}
int main(int argc,char **argv){
    assert(argc==2);FILE *f=fopen(argv[1],"rb");assert(f);assert(!fseek(f,0,SEEK_END));long bytes=ftell(f);assert(bytes>0);rewind(f);unsigned char *raw=malloc((size_t)bytes);assert(raw&&fread(raw,1,(size_t)bytes,f)==(size_t)bytes);fclose(f);
    MwNisPack p;assert(mw_nis_open(&p,raw,(size_t)bytes));
    MwNisDirector d={.has_subject=true,.has_scene=true,.has_fixed_subject=true,.fix_elevation=true,.world_queries_enabled=true,.scene_ground_height=92,.ground=flat};
    float origin[3]={123.25f,-84.5f,92},height=92;d.ground_context=&height;
    assert(mw_nis_director_scene_frame(d.scene,origin,31913,0));memcpy(d.subject,d.scene,64);memcpy(d.fixed_subject,d.scene,64);
    MwNisProviders raw_provider={identity,identity,NULL};unsigned count=0,modes[4]={0};
    for(unsigned i=0;i<p.scenes;i++){
        MwNisScene scene;assert(mw_nis_scene(&p,i,&scene));
        for(unsigned j=0;j<scene.track_count;j++){
            MwNisTrack track;assert(mw_nis_track(&p,&scene,j,&track));
            for(unsigned step=0;step<=120;step++){
                float elapsed=2+45*(float)step/120,parameter=(elapsed-2)/45;
                MwNisCamera original,result;assert(mw_nis_camera_parameter_provided(&p,&track,parameter,&raw_provider,&original));
                assert(mw_nis_director_scene_camera(&d,&p,&track,elapsed,2,47,&result));
                float expected_eye[3],expected_target[3];
                assert(original.eye_mode<4&&original.target_mode<4);modes[original.eye_mode]++;modes[original.target_mode]++;
                if(original.eye_mode==1)memcpy(expected_eye,original.eye,12);else assert(mw_nis_director_transform(d.scene,original.eye,expected_eye));
                if(original.target_mode==1)memcpy(expected_target,original.target,12);else assert(mw_nis_director_transform(d.scene,original.target,expected_target));
                assert(!memcmp(result.eye,expected_eye,12)&&!memcmp(result.target,expected_target,12));
                assert(result.fov_turn==(float)(uint16_t)original.fov_turn&&result.roll_source==original.roll_source);
                assert(result.finished==(elapsed>=47));assert(!memcmp(result.reference_flags,original.reference_flags,4));count++;
            }
        }
    }
    assert(modes[0]&&modes[1]&&modes[3]);
    /* The original DD ignore-orientation cut captures its subject on entering
     * key20, then follows current translation while keeping that orientation. */
    MwNisScene dd;MwNisTrack ddtrack;assert(mw_nis_find(&p,"IntroNisDD",&dd)&&mw_nis_track(&p,&dd,0,&ddtrack));
    d.has_active_key=false;MwNisCamera cut;
    assert(mw_nis_director_scene_camera(&d,&p,&ddtrack,14.7f,0,43.000003814697266f,&cut));
    assert(mw_nis_director_scene_frame(d.subject,origin,16384,0));
    assert(mw_nis_director_scene_camera(&d,&p,&ddtrack,15,0,43.000003814697266f,&cut));assert(cut.key_index==20&&cut.reference_flags[0]);
    float captured[16];memcpy(captured,d.fixed_subject,64);assert(!memcmp(captured,d.subject,64));
    float moved[3]={240,-160,92};assert(mw_nis_director_scene_frame(d.subject,moved,32768,0));
    assert(mw_nis_director_scene_camera(&d,&p,&ddtrack,15.1f,0,43.000003814697266f,&cut));assert(cut.key_index==20&&!memcmp(captured,d.fixed_subject,64));
    MwNisCamera local;assert(mw_nis_camera_parameter_provided(&p,&ddtrack,15.1f/43.000003814697266f,&raw_provider,&local));
    memcpy(captured+12,d.subject+12,12);float fixed_eye[3];assert(mw_nis_director_transform(captured,local.eye,fixed_eye));assert(!memcmp(fixed_eye,cut.eye,12));
    MwNisScene scene;MwNisTrack track;assert(mw_nis_find(&p,"IntroNis04",&scene)&&mw_nis_track(&p,&scene,0,&track));
    d.has_active_key=false;ground_queries=0;
    assert(mw_nis_director_camera(&d,&p,&track,.01f,&cut));unsigned initial_queries=ground_queries;assert(initial_queries>0);
    assert(mw_nis_director_camera(&d,&p,&track,.02f,&cut)&&ground_queries==initial_queries);
    mw_nis_director_invalidate_ground(&d);assert(mw_nis_director_camera(&d,&p,&track,.02f,&cut)&&ground_queries>initial_queries);
    MwNisCamera sentinel={.key_index=876},out=sentinel;d.has_scene=false;
    assert(!mw_nis_director_camera(&d,&p,&track,0,&out)&&!memcmp(&out,&sentinel,sizeof(out)));d.has_scene=true;d.ground=NULL;
    assert(!mw_nis_director_camera(&d,&p,&track,0,&out)&&!memcmp(&out,&sentinel,sizeof(out)));
    assert(!mw_nis_director_scene_camera(&d,&p,&track,NAN,0,6,&out));
    assert(!mw_nis_director_scene_camera(&d,&p,&track,0,6,6,&out));
    float m[16],in[3]={1,2,3},before[3]={9,8,7},result[3];assert(mw_nis_director_scene_frame(m,origin,123,1));assert(m[0]==1&&m[5]==1&&m[10]==1&&m[12]==0&&m[14]==0);
    memcpy(result,before,12);m[4]=NAN;assert(!mw_nis_director_transform(m,in,result)&&!memcmp(result,before,12));
    free(raw);printf("NIS director: %u source scene-clock samples, modes0/1/3, fixed reference flags, terrain and provider rejection pass\n",count);return 0;
}
