#ifndef MW_CAREER_H
#define MW_CAREER_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
enum { MW_CAREER_STAGES=5, MW_CAREER_CARS=4, MW_CAREER_SAVE_BYTES=128 };
enum { MW_CAREER_PARTIAL=1, MW_CAREER_ENGINE_LOSS=2 };
enum { MW_CAREER_CALL_REQUEST=1, MW_CAREER_CALL_STARTED=2,
       MW_CAREER_FORCE_AI=4, MW_CAREER_SABOTAGE=8, MW_CAREER_ENGINE_BLOWN=16 };
typedef enum { MW_CAREER_INACTIVE, MW_CAREER_INTRO_MOVIE, MW_CAREER_INTRO_NIS,
    MW_CAREER_RACING, MW_CAREER_OUTRO_NIS, MW_CAREER_OUTRO_MOVIE,
    MW_CAREER_CAR_CHOICE, MW_CAREER_FREE_ROAM } MwCareerPhase;
typedef struct { const unsigned char *data;size_t bytes;uint32_t stage_at,car_at,trigger_at,string_at,string_bytes; } MwCareerPack;
typedef struct {
    uint32_t event,flags,linked_event,trigger,reward;
    const char *intro_movie,*outro_movie,*intro_nis,*outro_nis,*preset;
} MwCareerStage;
typedef struct { uint32_t key,cost,source_unlock;const char *model; } MwCareerCar;
/* Present bits:1position,2rotation,4Dimensions,8Radius,16Width. Width is a
   distinct original shape path, never an invented radius. */
typedef struct { uint32_t key,present;float position[3],rotation,dimensions[3],radius,width; } MwCareerTrigger;
typedef struct {
    uint32_t alias_id,step,flags,selected_car,owned_car,cash;
    MwCareerPhase phase;
    bool cash_known;
    uint64_t timer_us;
} MwCareer;
bool mw_career_pack_open(MwCareerPack *,const void *,size_t);
bool mw_career_stage(const MwCareerPack *,unsigned,MwCareerStage *);
bool mw_career_car(const MwCareerPack *,unsigned,MwCareerCar *);
bool mw_career_trigger_get(const MwCareerPack *,uint32_t,MwCareerTrigger *);
bool mw_career_start(MwCareer *,const MwCareerPack *,uint32_t alias_id);
/* Caller presents the exact asset for the current movie/NIS phase. Successful
   playback or an explicitly accepted skip may advance; decode failure must not. */
const char *mw_career_media(const MwCareer *,const MwCareerPack *);
bool mw_career_media_finished(MwCareer *,const MwCareerPack *);
/* Only stages1..3 accept an ordinary win. The partial and final story-loss
   stages cannot be credited by reaching their geometric finish gate. */
bool mw_career_race_result(MwCareer *,const MwCareerPack *,uint32_t event,bool won);
bool mw_career_retry(MwCareer *,const MwCareerPack *);
/* Authoritative caller entry only; the pure module supplies no actor detector.
   Partial trigger requests ECellCall(10); actual call-start begins original
   8s fade timer, then3s AI-controlled tail. Final trigger requests sabotage;
   actual engine-blown notification begins the original1s postrace timer. */
bool mw_career_trigger_enter(MwCareer *,const MwCareerPack *,uint32_t trigger);
bool mw_career_call_started(MwCareer *);
bool mw_career_engine_blown(MwCareer *);
bool mw_career_tick(MwCareer *,const MwCareerPack *,uint64_t elapsed_us);
/* Source new career starts at zero; legitimate middle-stage first-place wins
   award their source CashValue once. Selection is separate from ownership.
   Extra wallet producers remain caller-owned original/profile integrations. */
bool mw_career_select_car(MwCareer *,const MwCareerPack *,uint32_t frontend_key);
bool mw_career_set_wallet(MwCareer *,uint32_t cash);
bool mw_career_purchase(MwCareer *,const MwCareerPack *);
bool mw_career_save(const MwCareer *,const MwCareerPack *,void *,size_t);
bool mw_career_load(MwCareer *,const MwCareerPack *,uint32_t alias_id,const void *,size_t);
#endif
