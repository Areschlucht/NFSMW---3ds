#include "streamed_world.h"
#include <assert.h>
#include <inttypes.h>
#include <math.h>
#include <stdio.h>
#include <string.h>
int main(int argc,char **argv){
    assert(argc==3);
    StreamedWorldConfig config={.asset_root=argv[1],.metadata_path=argv[2],.normal_bytes=20*1024*1024,.linear_bytes=24*1024*1024,.scratch_bytes=4*1024*1024,
        .cache_entries=2048,.object_capacity=8192,.run_capacity=65536,.render_scale=.001f,.lod_mode=STREAMED_WORLD_REFERENCE_SLOT0,.alpha_reference=40};
    StreamedWorld *world=NULL;assert(streamed_world_create(&config,&world)==STREAMED_WORLD_OK);
    StreamedWorldView view={.camera_viewer={360,180,-2410},.forward_viewer={0,0,1},.up_viewer={0,1,0},.vertical_fov_radians=1,.aspect=400.f/240,.near_world=.15f,.far_world=350,.original_fov_turn=0x3000};
    StreamedWorldResult result=streamed_world_prepare(world,360,2410,&view);StreamedWorldStats first;streamed_world_stats(world,&first);
    if(result!=STREAMED_WORLD_OK){printf("{\"result\":%d,\"detail\":\"%s\",\"normal\":%u,\"linear\":%u}\n",result,first.detail,first.normal_used,first.linear_used);streamed_world_destroy(world);return 2;}
    assert(first.draw_runs&&first.visible_instances&&first.resident_models&&first.resident_textures);
    shaderProgram_s program={0};C3D_Mtx projection;Mtx_Identity(&projection);streamed_world_draw(world,&program,0,1,&projection);assert(mock_draw_calls==first.draw_runs);
    for(unsigned i=0;i<3;i++)assert(streamed_world_prepare(world,360,2410,&view)==STREAMED_WORLD_OK);
    StreamedWorldStats steady;streamed_world_stats(world,&steady);
    assert(steady.asset_reads==first.asset_reads&&steady.asset_queries==first.asset_queries&&steady.model_uploads==first.model_uploads&&steady.texture_uploads==first.texture_uploads&&steady.arena_allocations==first.arena_allocations);
    assert(steady.normal_used==first.normal_used&&steady.linear_used==first.linear_used);
    StreamedWorldView missing=view;missing.forward_viewer[2]=-1;
    assert(streamed_world_prepare(world,360,2410,&missing)==STREAMED_WORLD_MISSING);
    StreamedWorldStats missing_stats;streamed_world_stats(world,&missing_stats);
    assert(missing_stats.region==steady.region&&missing_stats.draw_runs==steady.draw_runs&&missing_stats.normal_used==steady.normal_used&&missing_stats.linear_used==steady.linear_used);
    assert(strstr(missing_stats.detail,"7e2734a8"));
    StreamedWorldView exhausted=view;exhausted.forward_viewer[0]=-1;exhausted.forward_viewer[2]=0;
    mock_linear_limit=mock_linear_used;
    assert(streamed_world_prepare(world,360,2410,&exhausted)==STREAMED_WORLD_BUDGET);
    mock_linear_limit=SIZE_MAX;
    StreamedWorldStats budget_stats;streamed_world_stats(world,&budget_stats);
    assert(budget_stats.region==steady.region&&budget_stats.draw_runs==steady.draw_runs&&budget_stats.normal_used==steady.normal_used&&budget_stats.linear_used==steady.linear_used);
    assert(streamed_world_prepare(world,360,2410,&view)==STREAMED_WORLD_OK);
    /* A failing next view retains complete old bindings and allocation counts. */
    assert(streamed_world_prepare(world,1e7f,1e7f,&view)==STREAMED_WORLD_NEAREST_REQUIRED);
    StreamedWorldStats failed;streamed_world_stats(world,&failed);
    assert(failed.region==steady.region&&failed.draw_runs==steady.draw_runs&&failed.linear_used==steady.linear_used&&failed.normal_used==steady.normal_used);
    unsigned before=mock_draw_calls;streamed_world_draw(world,&program,0,1,&projection);assert(mock_draw_calls-before==steady.draw_runs);
    streamed_world_destroy(world);assert(mock_linear_used==0);
    printf("{\"region\":%u,\"objects\":%u,\"runs\":%u,\"triangles\":%u,\"normal_bytes\":%u,\"linear_bytes\":%u,\"model_uploads\":%u,\"texture_uploads\":%u,\"steady_frame_reads\":0,\"steady_frame_allocations\":0,\"missing_asset_rollback\":true,\"gpu_allocation_failure_rollback\":true,\"nearest_rollback\":true,\"ordered_gpu_stream_hash\":\"%016" PRIx64 "\"}\n",first.region,first.visible_instances,first.draw_runs,first.triangles,first.normal_used,first.linear_used,first.model_uploads,first.texture_uploads,mock_draw_stream_hash);
    return 0;
}
