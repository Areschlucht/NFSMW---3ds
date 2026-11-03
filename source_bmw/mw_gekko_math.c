#include "mw_gekko_math.h"
#include <stdint.h>
#include <string.h>
#include <math.h>

/* Numeric functional constants inferred by querying32 segment starts and
   their next15-bit mantissa ticks, then independently exhaustively checked
   over both normalized exponent parities. Generation/provenance is recorded
   by tools/perf_gekko_derive.py; no external implementation is copied here. */
typedef struct { uint32_t intercept;uint16_t decrement; } EstimateSegment;
static const EstimateSegment segments[2][16]={
    {{67084288,1956},{63082496,1792},{59416576,1648},{56041472,1522},
     {52924416,1412},{50032640,1316},{47341568,1228},{44826624,1150},
     {42471424,1082},{40259584,1018},{38174720,962},{36204544,910},
     {34344960,862},{32579584,818},{30904320,778},{29310976,742}},
    {{27781120,1384},{24950784,1267},{22358016,1165},{19972096,1077},
     {17768448,999},{15724544,930},{13819904,869},{12042240,814},
     {10375168,764},{8810496,720},{7335936,680},{5945344,643},
     {4628480,609},{3381248,579},{2197504,550},{1071104,523}}
};
static double from_bits(uint64_t bits)
{ double value;memcpy(&value,&bits,sizeof(value));return value; }
double mw_gekko_frsqrte(double value)
{
    uint64_t bits;memcpy(&bits,&value,sizeof(bits));
    uint64_t fraction=bits&UINT64_C(0x000fffffffffffff);
    unsigned encoded=(unsigned)((bits>>52)&2047u);
    if (encoded==2047 && fraction) return from_bits(bits|UINT64_C(0x0008000000000000));
    if (!encoded && !fraction) return from_bits((bits&UINT64_C(0x8000000000000000))|UINT64_C(0x7ff0000000000000));
    if (bits>>63) return from_bits(UINT64_C(0x7ff8000000000000));
    if (encoded==2047) return 0.0;
    int exponent=(int)encoded-1023;
    if (!encoded) {
        exponent=-1022;
        while (!(fraction&UINT64_C(0x0010000000000000))) { fraction<<=1;--exponent; }
        fraction&=UINT64_C(0x000fffffffffffff);
    }
    int half=exponent>=0?exponent/2:-((1-exponent)/2);
    unsigned parity=(unsigned)(exponent-2*half),tick=(unsigned)(fraction>>37);
    const EstimateSegment *s=&segments[parity][tick>>11];
    uint32_t mantissa=s->intercept-s->decrement*(tick&2047u);
    return from_bits(((uint64_t)(1022-half)<<52)|((uint64_t)mantissa<<26));
}
float mw_gekko_sqrt_newton1(float value)
{
    if (value==0.0f) return value;
    double estimate=mw_gekko_frsqrte((double)value);
    float reciprocal=(float)(1.0/estimate);
    float average_sum=(float)fma((double)value,estimate,(double)reciprocal);
    return average_sum*0.5f;
}
float mw_gekko_sqrt_newton2(float value)
{
    if (!(value>5.0000000667571598005e-11f)) return 0.0f;
    double estimate=mw_gekko_frsqrte((double)value);
    for (unsigned i=0;i<2;++i) {
        float square=(float)(estimate*estimate),half=(float)(estimate*0.5);
        float residual=fmaf(-value,square,1.0f);
        estimate=(double)(float)fma((double)residual,(double)half,estimate);
    }
    return (float)(estimate*(double)value);
}
