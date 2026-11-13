#include "world_streaming_scene.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static void put16(unsigned char *p,unsigned n){p[0]=(unsigned char)n;p[1]=(unsigned char)(n>>8);}
int main(void){
 const int values[]={-32768,-32767,-8192,-1,0,1,8192,32767};unsigned cases=0;
 for(unsigned i=0;i<8;i++)for(unsigned lane=0;lane<3;lane++)for(unsigned eligible=0;eligible<2;eligible++)for(unsigned initially=0;initially<2;initially++){
  unsigned char raw[64]={0},saved[64];unsigned old=(eligible?0x00800000u:0u)|(initially?0x400u:0u);
  for(unsigned b=0;b<4;b++)raw[24+b]=(unsigned char)(old>>(b*8));
  for(unsigned a=0;a<9;a++)put16(raw+44+a*2,(unsigned)(a==lane?values[i]:(int)a+1));
  memcpy(saved,raw,64);WorldStreamingSceneInstance s={.original_instance=raw};
  for(unsigned repeat=0;repeat<2;repeat++){
   assert(world_streaming_scene_instance_transform(&s,old^0x400u));
   for(unsigned a=0;a<9;a++){
    unsigned bits=(unsigned)(a==lane?values[i]:(int)a+1)&65535u;if(eligible&&a<3)bits=(0u-bits)&65535u;
    int expected=bits>=32768?(int)bits-65536:(int)bits;assert(s.matrix[a]==(float)expected/8192.0f);
   }
   assert(!memcmp(saved,raw,64));
  }
  assert(world_streaming_scene_instance_transform(&s,old));assert(s.matrix[lane]==(float)values[i]/8192.0f);cases++;
 }
 assert(!world_streaming_scene_instance_transform(NULL,0));puts("192 repeated Q13 reflection applications preserve source bytes and restore exactly");assert(cases==96);
}
