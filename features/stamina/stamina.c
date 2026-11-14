#include "stamina.h"

/* Clean-room stamina defaults. They are deliberately plain data so the
 * balance can be tuned without touching the state machine. */
void stamina_default_config(StaminaConfig *c) {
    c->units_per_heart = 20.0f;
    c->regen_delay = 1.25f;
    c->regen_per_second = 24.0f;
    c->roll_cost = 10.0f;
    c->backflip_cost = 8.0f;
    c->sidestep_cost = 4.0f;
    c->block_base_cost = 8.0f;
    c->block_cost_per_damage_heart = 1.0f;
    c->tired_damage = 0.5f;
    c->tired_speed = 0.75f;
    c->weapon_cost[0] = 8.0f;
    c->weapon_cost[1] = 12.0f;
    c->weapon_cost[2] = 24.0f;
    c->weapon_cost[3] = 24.0f;
    c->move_cost_scale[0] = 1.0f;
    c->move_cost_scale[1] = 1.1f;
    c->move_cost_scale[2] = 1.5f;
    c->move_cost_scale[3] = 1.8f;
    c->low_health_cost_max = 2.0f;
    c->guard_hold_per_second = 2.0f;
}

void stamina_init(StaminaState *s, const StaminaConfig *c, u32 life_quarters) {
    f32 cap = (f32)life_quarters * 0.25f * c->units_per_heart;
    s->stamina = cap;
    s->cap = cap;
    s->full_cap = cap;
    s->idle_seconds = 0.0f;
    s->drain_multiplier = 1.0f;
    s->initialized = 1;
    s->last_action_token = 0;
    s->last_impact_token = 0;
    s->alive = 1;
    s->in_combat = 0;
}

static f32 clampf(f32 v, f32 lo, f32 hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

void stamina_tick(StaminaState *s, const StaminaConfig *c, f32 dt, u32 life_quarters,
                  u32 in_combat, u32 moving, u32 attacking, u32 guard_held) {
    f32 cap = (f32)life_quarters * 0.25f * c->units_per_heart;
    if (cap > 1.0f) {
        s->cap = cap;
        if (s->stamina > cap) s->stamina = cap;
    }
    s->in_combat = in_combat;
    s->alive = life_quarters != 0;
    if (guard_held && in_combat && s->stamina > 0.0f) {
        s->stamina -= c->guard_hold_per_second * dt * s->drain_multiplier;
        s->idle_seconds = 0.0f;
    } else if (!in_combat && !moving && !attacking) {
        s->idle_seconds += dt;
        if (s->idle_seconds >= c->regen_delay) {
            s->stamina += c->regen_per_second * dt;
        }
    } else {
        s->idle_seconds = 0.0f;
    }
    s->stamina = clampf(s->stamina, 0.0f, s->cap);
}

u32 stamina_begin_action(StaminaState *s, const StaminaConfig *c, u32 action,
                         u32 weapon, u32 move, u32 token) {
    f32 cost = 0.0f;
    if (s->last_action_token == token) return s->stamina > 0.0f;
    s->last_action_token = token;
    switch (action) {
    case ACTION_ROLL: cost = c->roll_cost * c->move_cost_scale[0]; break;
    case ACTION_BACKFLIP: cost = c->backflip_cost * c->move_cost_scale[0]; break;
    case ACTION_SIDESTEP: cost = c->sidestep_cost * c->move_cost_scale[0]; break;
    case ACTION_BOW:
    case ACTION_SLINGSHOT:
    case ACTION_BOOMERANG:
        cost = c->weapon_cost[weapon < 4 ? weapon : 0] * c->move_cost_scale[1];
        break;
    default:
        cost = c->weapon_cost[weapon < 4 ? weapon : 0] *
               c->move_cost_scale[move < 4 ? move : 0];
        break;
    }
    if (!s->in_combat) return 1;
    if (s->stamina <= 0.0f) return 0;
    s->stamina -= cost * s->drain_multiplier;
    if (s->stamina < 0.0f) s->stamina = 0.0f;
    s->idle_seconds = 0.0f;
    return 1;
}

u32 stamina_allow_guard(const StaminaState *s, u32 guard_held) {
    if (!guard_held) return 0;
    return s->stamina > 0.0f;
}

f32 stamina_damage_scale(const StaminaState *s, const StaminaConfig *c) {
    return s->stamina > 0.0f ? 1.0f : c->tired_damage;
}

f32 stamina_speed_scale(const StaminaState *s, const StaminaConfig *c) {
    return s->stamina > 0.0f ? 1.0f : c->tired_speed;
}
