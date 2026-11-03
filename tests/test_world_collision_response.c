#include "mw_body_collision.h"
#include <assert.h>
#include <math.h>
#include <stddef.h>
static float boundary_sqrt(float squared,void *context){assert(squared>0);(*(unsigned*)context)++;return nextafterf(.2f,INFINITY);}
int main(void){
    float coefficients[2]={.3f,.55f},normal[3]={0,1,0},out[3];
    assert(mw_body_collision_tangent_response(coefficients,(float[3]){1,-10,0},normal,-10,out)==1);
    assert(out[0]==-1&&out[1]==0&&out[2]==0);
    assert(mw_body_collision_tangent_response(coefficients,(float[3]){10,-10,0},normal,-10,out)==2);
    assert(out[0]==-3&&out[1]==0&&out[2]==0);
    assert(mw_body_collision_tangent_response(coefficients,(float[3]){0,-10,0},normal,-10,out)==1);
    assert(out[0]==0&&out[1]==0&&out[2]==0);
    assert(mw_body_collision_tangent_response(coefficients,(float[3]){1,1,1},normal,1,out)==0);
    assert(out[0]==0&&out[1]==0&&out[2]==0);
    float pair[2];assert(mw_body_collision_world_friction((float[2]){.55f,.3f},2,.5f,pair)==0);
    assert(pair[0]==.15f&&pair[1]==.275f);
    assert(mw_body_collision_world_friction((float[2]){.2f,.8f},2,1,pair)==0&&pair[0]==.2f&&pair[1]==.2f);
    assert(mw_body_collision_world_friction((float[1]){.55f},1,0,pair)==0&&pair[0]==0&&pair[1]==0);
    float boundary_pair[2]={.1f,.2f},velocity[3]={.2f,-1,0};unsigned calls=0;MwBodyCollisionMath math={boundary_sqrt,&calls};
    assert(mw_body_collision_tangent_response(boundary_pair,velocity,normal,-1,out)==2);
    assert(mw_body_collision_tangent_response_with_math(boundary_pair,velocity,normal,-1,out,&math)==2&&calls==1);
    assert(fabsf(out[0]+.1f)<.000001f);
    assert(mw_body_collision_tangent_response(NULL,velocity,normal,-1,out)==-1);
    assert(mw_body_collision_tangent_response((float[2]){-1,1},velocity,normal,-1,out)==-1);
    assert(mw_body_collision_tangent_response(boundary_pair,(float[3]){NAN,0,0},normal,-1,out)==-1);
    assert(mw_body_collision_world_friction(boundary_pair,0,1,pair)==-1);
    assert(mw_body_collision_world_friction(boundary_pair,2,NAN,pair)==-1);
    return 0;
}
