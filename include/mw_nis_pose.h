#ifndef MW_NIS_POSE_H
#define MW_NIS_POSE_H
/* Original EAGL BuildSQT, ROOT skeleton and AnimatedCars_SetMainAndWheels
 * matrix chain. Flat16 arrays retain original byte/index layout, translation
 * at12..14. Quaternion order x,y,z,w; NEVER normalized or slerped here.
 * Actual source ROOT has two identity rest bones; the animated car is bone1.
 * Scene matrices must be original source rotation/translation providers.
 * Returns0 for missing/nonfinite input,1 on success. No allocation/I/O.
 */
int mw_nis_pose_sqt(const float scale[3],const float quaternion[4],const float translation[3],float out_local[16]);
int mw_nis_pose_world(const float local[16],const float scene_rotation[16],const float scene_translation[16],float out_source_world[16],float out_original_bond[16]);
int mw_nis_pose_vehicle(const float scale[3],const float quaternion[4],const float translation[3],const float scene_rotation[16],const float scene_translation[16],float out_source_world[16],float out_original_bond[16]);
/* Original rigorous terrain query takes Bondtranslation aspoint, mask0/type3
 * and requests no normal. Onhit overwrite BondY=returned_world_height+5;
 * onmiss preserve animated matrix. The actual source terrain query is external. */
int mw_nis_pose_ground_height(float bond[16],int hit,float world_height);
#endif
