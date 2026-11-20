#include "mw_original_power.h"
#include <assert.h>
#include <float.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static float value(uint32_t bits){float x;memcpy(&x,&bits,4);return x;}
static uint32_t bits(float x){uint32_t b;memcpy(&b,&x,4);return b;}
int main(void)
{
    const uint32_t edge[]={0,1,2,3,0x003fffff,0x007fffff,0x00800000,0x00800001,
        0x3eaaaaab,0x3f000000,0x3f7fffff,0x3f800000,0x3f800001,0x40000000,0x40400000,0x40800000,0x7f7ffffe,0x7f7fffff};
    for(unsigned i=0;i<sizeof(edge)/sizeof(*edge);i++){
        float x=value(edge[i]),out=123;
        assert(mw_original_power_positive(x,0,&out)&&out==1);
        assert(mw_original_power_positive(x,1,&out)&&bits(out)==bits(x));
        assert(mw_original_power_positive(x,.5f,&out)&&bits(out)==bits(sqrtf(x)));
        volatile float square=x*x;
        out=123;bool ok=mw_original_power_positive(x,2,&out);
        if(isfinite(square))assert(ok&&bits(out)==bits(square));else assert(!ok&&out==123);
    }
    /* Independent correctly-rounded sqrtf oracle across the normal/subnormal
       exponent range; original-source comparison is in the Python harness. */
    uint32_t state=0x31704;
    for(unsigned i=0;i<4096;i++){
        state=state*1664525u+1013904223u;float x=value(state%0x7f800000u),out;
        assert(mw_original_power_positive(x,.5f,&out)&&bits(out)==bits(sqrtf(x)));
    }
    float out=123;assert(!mw_original_power_positive(-1,.5f,&out)&&out==123);
    assert(!mw_original_power_positive(4,3,&out)&&out==123);
    assert(!mw_original_power_positive(INFINITY,.5f,&out)&&out==123);
    assert(!mw_original_power_positive(NAN,1,&out)&&out==123);
    assert(!mw_original_power_positive(1,NAN,&out)&&out==123);
    assert(!mw_original_power_positive(1,1,NULL));
    assert(mw_original_power_positive(-0.0f,1,&out)&&bits(out)==0x80000000u);
    assert(mw_original_power_positive(-0.0f,.5f,&out)&&bits(out)==0);
    assert(mw_original_power_callback(4,.5,NULL)==2&&isnan(mw_original_power_callback(4,3,NULL)));
    /* Original-PPC counterexample that differs from host powf. */
    assert(mw_original_power_positive(value(0x721602c3),.7f,&out)&&bits(out)==0x62e85d41);
    assert(mw_original_power_positive(4,.75f,&out)&&bits(out)==bits(2.8284270763397217f));
    puts("Power: source-domain boundaries,4096 independent square roots, single square rounding, signed zero and unsupported rollback pass.");
}
