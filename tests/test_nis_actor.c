#include "mw_nis_actor.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
int main(int argc,char**argv){
    MwNisActorBank bank;MwNisActorScene scene;MwNisActorCurve curve;float a[4],b[4],q[4];
    assert(argc==2);assert(mw_nis_actor_open(&bank,argv[1]));assert(bank.banks==7&&bank.curves==95&&bank.data&&bank.file==NULL);
    assert(mw_nis_actor_find_scene(&bank,"IntroNisDD",&scene));assert(scene.curve_count==30);
    assert(!mw_nis_actor_find_scene(&bank,"intronisdd",&scene));
    assert(mw_nis_actor_find_scene(&bank,"IntroNisDD",&scene));
    assert(mw_nis_actor_find_curve(&bank,&scene,"IntroNisDDZPM_Car1_t",&curve));
    assert(curve.frames==676&&curve.channels==3&&curve.kind==MW_NIS_ACTOR_TRANSLATION);
    assert(curve.destination[0]==20&&curve.context_rate==30);
    assert(mw_nis_actor_sample(&bank,&curve,0,0,a,4));
    assert(a[0]==1046.3294677734375f&&a[1]==99.03913879394531f&&a[2]==100.35159301757812f);
    assert(mw_nis_actor_sample(&bank,&curve,675,0,a,4));
    assert(a[0]==2162.155029296875f&&a[1]==-529.4708862304688f&&a[2]==116.01654052734375f);
    assert(mw_nis_actor_sample(&bank,&curve,3.25f,1,a,4));
    assert(mw_nis_actor_sample(&bank,&curve,97.5f,0,b,4));
    assert(a[0]==b[0]&&a[1]==b[1]&&a[2]==b[2]);
    assert(!mw_nis_actor_sample(&bank,&curve,NAN,0,b,4));
    assert(!mw_nis_actor_sample(&bank,&curve,0,0,b,2));
    assert(mw_nis_actor_find_curve(&bank,&scene,"IntroNisDDZPM_Car1_q",&curve));
    assert(curve.channels==4&&curve.kind==MW_NIS_ACTOR_QUATERNION);
    assert(mw_nis_actor_sample(&bank,&curve,0,0,q,4));assert(q[2]==0.8424091935157776f);
    mw_nis_actor_close(&bank);assert(!bank.data&&!bank.file);
    puts("NIS actor source samples, context time conversion, bounds: OK");return 0;
}
