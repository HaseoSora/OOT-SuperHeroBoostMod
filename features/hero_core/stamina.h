/*
 * Clean-room stamina core for the unified OoT remake mod.
 * No game code is used here; this is the portable state machine.
 */
#ifndef OOT_STAMINA_H
#define OOT_STAMINA_H

typedef unsigned int u32;
typedef float f32;

typedef struct {
    f32 stamina;
    f32 cap;
    f32 full_cap;
    f32 idle_seconds;
    f32 drain_multiplier;
    u32 initialized;
    u32 last_action_token;
    u32 last_impact_token;
    u32 alive;
    u32 in_combat;
} StaminaState;

typedef struct {
    f32 units_per_heart;
    f32 regen_delay;
    f32 regen_per_second;
    f32 roll_cost;
    f32 backflip_cost;
    f32 sidestep_cost;
    f32 block_base_cost;
    f32 block_cost_per_damage_heart;
    f32 tired_damage;
    f32 tired_speed;
    f32 weapon_cost[4];
    f32 move_cost_scale[4];
    f32 low_health_cost_max;
    f32 guard_hold_per_second;
} StaminaConfig;

enum {
    ACTION_SLASH = 0,
    ACTION_ROLL = 1,
    ACTION_BACKFLIP = 2,
    ACTION_SIDESTEP = 3,
    ACTION_BOW = 4,
    ACTION_SLINGSHOT = 5,
    ACTION_BOOMERANG = 6,
};

void stamina_default_config(StaminaConfig *c);
void stamina_init(StaminaState *s, const StaminaConfig *c, u32 life_quarters);
void stamina_tick(StaminaState *s, const StaminaConfig *c, f32 dt, u32 life_quarters,
                  u32 in_combat, u32 moving, u32 attacking, u32 guard_held);
u32 stamina_begin_action(StaminaState *s, const StaminaConfig *c, u32 action,
                         u32 weapon, u32 move, u32 token);
u32 stamina_allow_guard(const StaminaState *s, u32 guard_held);
f32 stamina_damage_scale(const StaminaState *s, const StaminaConfig *c);
f32 stamina_speed_scale(const StaminaState *s, const StaminaConfig *c);

#endif
