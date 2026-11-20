#ifndef MW_ORIGINAL_POWER_H
#define MW_ORIGINAL_POWER_H
#include <stdbool.h>
/* Verified positive finite-input branches of original8031CEC0 powf.
   Supported finite exponents:0..2. Finite results only; unsupported/error leaves
   output unchanged. This is not a replacement for negative/large exponent original powf. */
bool mw_original_power_positive(float base,float exponent,float *out);
/* Adapter for original mechanical math callbacks. Unsupported domains return
   NaN so the caller rejects; no approximate libm fallback is installed. */
float mw_original_power_callback_float(float base,float exponent,void *context);
double mw_original_power_callback(double base,double exponent,void *context);
#endif
