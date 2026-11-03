#include "world_vertex.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void)
{
    NfsVertex source[2]={{{.1f,.2f,.3f},{1,0,0},{2,.25f},{.2f,.4f,.6f,1}},{{-.3f,.2f,-.1f},{0,1,0},{-2,.75f},{.6f,.4f,.2f,1}}};
    NfsVertex copy[2];memcpy(copy,source,sizeof(copy));WorldVertex packed[2];world_vertex_pack(packed,source,2);
    assert(sizeof(WorldVertex)==36 && sizeof(NfsVertex)==48);
    for (unsigned i=0;i<2;++i) {
        assert(!memcmp(packed[i].position,source[i].position,sizeof(packed[i].position)));
        assert(!memcmp(packed[i].color,source[i].color,sizeof(packed[i].color)));
        assert(packed[i].uv[0]==source[i].uv[0] && packed[i].uv[1]==1-source[i].uv[1]);
    }
    assert(!memcmp(source,copy,sizeof(source)));
    puts("World vertex pack: exact positions/colours/UV convention; 48 -> 36 bytes, source unchanged.");return 0;
}
