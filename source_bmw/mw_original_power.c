/* General logarithm/exponential decomposition follows the fdlibm family.
 * Public algorithm reference: JuliaMath/openlibm src/e_powf.c.
 * Source PPC constants, splits and fused/separate rounding are recovered here.
 *
 * Copyright (C) 1993 by Sun Microsystems, Inc. All rights reserved.
 * Developed at SunPro, a Sun Microsystems, Inc. business.
 * Permission to use, copy, modify, and distribute this software is freely
 * granted, provided that this notice is preserved.
 */
#include "mw_original_power.h"
#include <math.h>
#include <stdint.h>
#include <string.h>
/* Original8031D704 finite positive square-root branch. Integer restoring
   square root includes the original round-to-nearest/even last-bit decision.
   It does not use host sqrt/pow, a reciprocal estimate, or copied code bytes. */
static float root(float x)
{
    uint32_t bits;memcpy(&bits,&x,4);
    if(!(bits&0x7fffffffu))return 0;
    uint32_t significand=bits;int exponent=(int)(bits>>23);
    if(!exponent){
        unsigned shift=0;
        while(!(significand&0x00800000u)){significand<<=1;shift++;}
        exponent=1-(int)shift;
    }
    exponent-=127;significand=(significand&0x007fffffu)|0x00800000u;
    if(exponent%2)significand+=significand;
    exponent=exponent>=0?exponent/2:-((-exponent+1)/2);
    significand+=significand;
    uint32_t sum=0,quotient=0;
    for(uint32_t bit=0x01000000u;bit;bit>>=1){
        uint32_t trial=sum+bit;
        if(trial<=significand){significand-=trial;sum=trial+bit;quotient+=bit;}
        significand+=significand;
    }
    if(significand)quotient+=quotient&1u;
    bits=(uint32_t)((int64_t)(quotient>>1)+0x3f000000LL+(int64_t)exponent*8388608LL);
    float result;memcpy(&result,&bits,4);return result;
}
/* Positive finite exponent<=2 general branch of original8031CEC0. The
   fdlibm logarithm/exponential decomposition is evaluated in source PPC order;
   source split constants differ from later public fdlibm versions. */
static float f32(float x){volatile float r=x;return r;}
static uint32_t bits(float x){uint32_t u;memcpy(&u,&x,4);return u;}
static float value(uint32_t u){float x;memcpy(&x,&u,4);return x;}
static float high(float x){return value(bits(x)&0xfffff000u);}
static float general(float x,float y)
{
    if(x==0)return 0;
    uint32_t ix=bits(x);int n=0;
    if(ix<0x00800000u){x=f32(x*16777216.0f);ix=bits(x);n=-24;}
    n+=(int)(ix>>23)-127;uint32_t j=ix&0x007fffffu;ix=j|0x3f800000u;
    unsigned k;
    if(j<=0x1cc471u)k=0;
    else if(j<=0x5db3d6u)k=1;
    else{k=0;n++;ix-=0x00800000u;}
    float ax=value(ix),bp=k?1.5f:1.0f;
    float u=f32(ax-bp),v=f32(1.0f/f32(ax+bp));
    float s=f32(u*v),sh=high(s);
    float th=value((ix>>1|0x20000000u)+0x00040000u+(k<<21));
    float tl=f32(ax-f32(th-bp));
    float sl=f32(v*f32(f32(u-f32(sh*th))-f32(sh*tl)));
    float s2=f32(s*s);
    float poly=fmaf(s2,.20697501301765442f,.23066075146198273f);
    poly=fmaf(s2,poly,.2727281153202057f);
    poly=fmaf(s2,poly,.3333333432674408f);
    poly=fmaf(s2,poly,.4285714328289032f);
    poly=fmaf(s2,poly,.6000000238418579f);
    float r=fmaf(f32(s2*s2),poly,f32(sl*f32(sh+s)));
    s2=f32(sh*sh);th=high(f32(f32(s2+3.0f)+r));
    tl=f32(r-f32(f32(th-3.0f)-s2));
    u=f32(sh*th);v=fmaf(sl,th,f32(tl*s));
    float ph=high(f32(u+v)),pl=f32(v-f32(ph-u));
    float zh=f32(ph*.9617919921875f);
    float zl=fmaf(ph,4.701738362200558e-06f,f32(pl*.9617967009544373f));
    zl=f32(zl+(k?1.5632208487659227e-06f:0));
    float dh=k?.5849609375f:0,t=(float)n;
    float t1=high(f32(f32(f32(zh+zl)+dh)+t));
    float t2=f32(zl-f32(f32(f32(t1-t)-dh)-zh));
    float yh=high(y);pl=fmaf(f32(y-yh),t1,f32(y*t2));ph=f32(yh*t1);
    float z=f32(pl+ph);
    if(z>128|| (z==128&&f32(pl+4.299566569443414e-08f)>f32(z-ph)))return INFINITY;
    if(z< -150||(z== -150&&pl<=f32(z-ph)))return 0;
    uint32_t iz=bits(z),absolute=iz&0x7fffffffu;int shift=(int)(absolute>>23)-127;n=0;
    if(absolute>0x3f000000u){
        uint32_t nearest=iz+(0x00800000u>>(shift+1));
        shift=(int)((nearest&0x7fffffffu)>>23)-127;
        t=value(nearest&~(0x007fffffu>>shift));
        n=(int)(((nearest&0x007fffffu)|0x00800000u)>>(23-shift));
        if(iz>>31)n=-n;
        ph=f32(ph-t);
    }
    t=high(f32(pl+ph));
    u=f32(t*.693145751953125f);
    v=fmaf(f32(pl-f32(t-ph)),.6931471824645996f,f32(t*1.4286065379565116e-06f));
    z=f32(u+v);float w=f32(v-f32(z-u));t=f32(z*z);
    poly=fmaf(t,4.138136944220605e-08f,-1.6533901998627698e-06f);
    poly=fmaf(t,poly,6.61375597701408e-05f);
    poly=fmaf(t,poly,-.0027777778450399637f);
    poly=fmaf(t,poly,.1666666716337204f);
    t1=f32(z-f32(t*poly));
    r=f32(f32(f32(z*t1)/f32(t1-2))-fmaf(z,w,w));
    z=f32(1-f32(r-z));
    int64_t scaled=(int64_t)bits(z)+(int64_t)n*8388608;
    if(scaled<0x00800000)return scalbnf(z,n);
    return value((uint32_t)scaled);
}

bool mw_original_power_positive(float base,float exponent,float *out)
{
    if(!out||!isfinite(base)||!isfinite(exponent)||base<0)return false;
    float result;
    if(exponent==0)result=1;
    else if(exponent==1)result=base;
    else if(exponent==2){volatile float product=base*base;result=product;}
    else if(exponent==.5f)result=root(base);
    else if(exponent>0&&exponent<=2)result=general(base,exponent);
    else return false;
    if(!isfinite(result))return false;
    *out=result;return true;
}
double mw_original_power_callback(double base,double exponent,void *context)
{
    (void)context;float out;
    if(!mw_original_power_positive((float)base,(float)exponent,&out))return NAN;
    return out;
}

float mw_original_power_callback_float(float base,float exponent,void *context){(void)context;float out;if(!mw_original_power_positive(base,exponent,&out))return NAN;return out;}
