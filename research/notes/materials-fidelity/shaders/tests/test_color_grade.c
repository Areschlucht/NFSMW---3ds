#include "mw_color_grade.h"
#include <citro3d.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
static C3D_TexEnv stages[6];
static unsigned calls;
C3D_TexEnv *C3D_GetTexEnv(int stage) { assert(stage>=0&&stage<6);++calls;return &stages[stage]; }
static void check_stage0(void) {
    assert(stages[0].func[0]==GPU_MODULATE && stages[0].func[1]==GPU_MODULATE);
    for (int c=0;c<2;++c) {
        assert(stages[0].src[c][0]==GPU_TEXTURE0);
        assert(stages[0].src[c][1]==GPU_PRIMARY_COLOR);
    }
}
static void check_pass(int stage,int channel) {
    assert(stages[stage].func[channel]==GPU_REPLACE);
    assert(stages[stage].src[channel][0]==GPU_PREVIOUS);
    assert(stages[stage].scale[channel]==1);
}
int main(void) {
    /* Start with poisoned state, matching a previous unrelated UI/material. */
    memset(stages,0x89,sizeof(stages));mw_color_grade_apply(true);
    assert(calls==6);check_stage0();
    assert(stages[1].color==UINT32_C(0xffc9fff6));
    assert(stages[1].func[0]==GPU_MODULATE);
    assert(stages[1].src[0][0]==GPU_PREVIOUS&&stages[1].src[0][1]==GPU_CONSTANT);
    check_pass(1,1);
    for (int i=2;i<6;++i) { check_pass(i,0);check_pass(i,1); }
    C3D_TexEnv first[6];memcpy(first,stages,sizeof(first));
    mw_color_grade_apply(false);check_stage0();
    for (int i=1;i<6;++i) { check_pass(i,0);check_pass(i,1); }
    mw_color_grade_apply(true);assert(memcmp(first,stages,sizeof(first))==0);
    for (unsigned alpha=0;alpha<256;++alpha) {
        uint32_t color=UINT32_C(0x79b2ec00)|alpha;
        assert(mw_color_grade_clear(color,false)==color);
        assert((mw_color_grade_clear(color,true)&255)==alpha);
    }
    assert(mw_color_grade_clear(UINT32_C(0x000000ab),true)==UINT32_C(0x000000ab));
    assert(mw_color_grade_clear(UINT32_C(0xffffff01),true)==UINT32_C(0xf6ffc901));
    puts("Color grade: state reset, neutral identity, alpha preservation and toggle restoration pass");
}
