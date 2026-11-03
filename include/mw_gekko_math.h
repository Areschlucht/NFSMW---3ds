#ifndef MW_GEKKO_MATH_H
#define MW_GEKKO_MATH_H
/* Independently implemented functional estimate and original caller stages.
   No runtime emulator/reference dependency. IEEE754 bits/results only; these
   helpers do not emulate Gekko exception flags or control registers. */
double mw_gekko_frsqrte(double value);
/* Original80193420: zero preserved, reciprocal-estimate/reciprocal average. */
float mw_gekko_sqrt_newton1(float value);
/* Original801916DC /802BEBDC: <=5e-11 returns0, two single refinements. */
float mw_gekko_sqrt_newton2(float value);
#endif
