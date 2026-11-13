#ifndef MW_TRAFFIC_H
#define MW_TRAFFIC_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
enum { MW_TRAFFIC_MAX_ACTORS=8,MW_TRAFFIC_MAX_TRANSITIONS=16,MW_TRAFFIC_MAX_NEAREST=512 };
/* Immutable original road graph plus a port-generated spatial index. Source
   positions use internal (-sourceY, sourceZ, sourceX), not viewer XYZ. */
typedef struct {const unsigned char *data;size_t bytes;uint32_t nodes,segments,nodes_at,segments_at,profiles,profiles_at,columns,rows,grid_refs,grid_at,refs_at;float min_x,min_z,cell;} MwTrafficWorld;
typedef struct {float position[3];uint16_t id,profile,segments[7];unsigned count;} MwTrafficNode;
typedef struct {uint16_t nodes[2],id,flags;float length;} MwTrafficSegment;
typedef struct {uint32_t samples,neighbor_checks,transitions,nearest_checks;} MwTrafficWork;
typedef struct {uint16_t segment;unsigned direction;float u,speed,position[3],forward[3];bool active;} MwTrafficCar;
/* 1 admit,0 refuse,negative abort. Caller can bind original event/stream state.
   The port additionally refuses original segment flag1, as803051D4 does. */
typedef int (*MwTrafficAdmission)(void *,uint16_t segment,uint16_t flags,unsigned direction);
bool mw_traffic_open(MwTrafficWorld *,const void *,size_t);
bool mw_traffic_node(const MwTrafficWorld *,uint32_t,MwTrafficNode *);
bool mw_traffic_segment(const MwTrafficWorld *,uint32_t,MwTrafficSegment *);
/* Original packed-curve geometry, including source float32/FMA ordering. */
bool mw_traffic_sample(const MwTrafficWorld *,uint16_t,float u,float position[3],float tangent[3]);
bool mw_traffic_start(const MwTrafficWorld *,MwTrafficCar *,uint16_t,unsigned direction,float u,float speed,MwTrafficAdmission,void *,MwTrafficWork *);
/* Native traffic policy, NOT recovered original AI: constant approximate arc
   speed, straightest permitted source connection, stop at dead ends. No heap,
   graph scans or IO; <=16 transitions and<=112 candidate checks per actor step.
   Invalid/admission failure leaves the car unchanged. 1 moving,0 stopped,-1 bad. */
int mw_traffic_step(const MwTrafficWorld *,MwTrafficCar *,float seconds,MwTrafficAdmission,void *,MwTrafficWork *);
/* Spawn-only approximate nearest query, indexed by original curve bounds.
   Hard budget512 distinct segments. Never call for every actor every frame.
   Fails transactionally if the query exceeds the candidate budget. */
bool mw_traffic_nearest(const MwTrafficWorld *,const float point[3],float radius,uint16_t *segment,float *u,MwTrafficAdmission,void *,MwTrafficWork *);
#endif
