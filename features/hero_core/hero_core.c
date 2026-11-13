#include "../../core/dispatch.h"
#include "../../core/hid.h"
#include "stamina.h"

/* hero_core: stamina. Behaviour replica, not Hero Core code.
 *
 *  - Y (sword): costs stamina during combat; blocked at 0 in combat.
 *  - A (dodge): costs stamina only when it actually rolls, i.e. when pressed with the
 *    stick deflected (standing still A costs nothing).
 *  - Running (stick fully deflected) drains stamina gradually; at 0 the stick is halved so
 *    Link can only walk.
 *  - X (jump): costs stamina; with none left the jump is blocked.
 *  Once empty, stamina must recover to EXHAUST_RECOVER before running/jumping/rolling again.
 * Values are placeholders (stamina_default_config + the constants below).
 */

void hud_set_stamina(float value, float cap, float show);
u32 hud_frame_count(void);
u32 player_take_events(void);
int player_state_is(const char *name);
#define PEV_ROLL 1u
#define PEV_SIDESTEP 2u
#define PEV_JUMP 4u
#define PEV_ATTACK 8u
#define PEV_GUARDHIT 16u

#define LIFE_QUARTERS 20u       /* placeholder: 5 hearts, not read from the game yet */
#define COMBAT_HOLD_FRAMES 180u
#define DT_FRAME (1.0f / 60.0f)

#define JUMP_COST 8.0f
#define RUN_DRAIN_PER_SEC 7.0f
#define EXHAUST_RECOVER 15.0f
#define STICK_MAX 32767.0f
#define STICK_MOVE2 (0.30f * 0.30f * STICK_MAX * STICK_MAX)   /* deflected enough to roll/walk */
#define STICK_RUN2 (0.85f * 0.85f * STICK_MAX * STICK_MAX)    /* running */
#define STICK_FAST2 (0.55f * 0.55f * STICK_MAX * STICK_MAX)   /* limited when exhausted */

/* Diagnostics read by tools/live_check.py (in .data so they are file-backed). */
u64 g_hc_seen = 0x100000000ull;  /* OR of every button mask seen at site 3 (+base) */
u32 g_hc_count = 0x10000000u;
u32 g_hc_dbg[5] = {0x10000000u, 0x10000000u, 0x10000000u, 0x10000000u, 0x10000000u};   /* rolls, jumps, run frames, exhausted */

static StaminaState g_stamina;
static StaminaConfig g_config;
static u32 g_initialized;
static u64 g_prev_buttons;
static u32 g_action_token;
static u32 g_combat_hold;
static u32 g_exhausted;
static u32 g_last_frame;

static void ensure_init(void) {
    if (g_initialized) return;
    stamina_default_config(&g_config);
    stamina_init(&g_stamina, &g_config, LIFE_QUARTERS);
    g_initialized = 1;
}

/* NpadFullKeyState: left stick = two s32 at +0x10 (x, y). Returns max squared deflection. */
int g_stick_dbg[16] = {0x7777};
static float stick_mag2(const HidView *v) {
    float best = 0.0f;
    for (u32 i = 0; i < v->count; i++) {
        volatile int *p = (volatile int *)((unsigned char *)v->samples + (u64)i * HID_STRIDE + 0x10);
        if (i < 8) { g_stick_dbg[i * 2] = p[0]; g_stick_dbg[i * 2 + 1] = p[1]; }
        float x = (float)p[0], y = (float)p[1];
        float m = x * x + y * y;
        if (m > best) best = m;
    }
    return best;
}

static void halve_stick(const HidView *v) {
    for (u32 i = 0; i < v->count; i++) {
        volatile int *p = (volatile int *)((unsigned char *)v->samples + (u64)i * HID_STRIDE + 0x10);
        p[0] = p[0] / 2;
        p[1] = p[1] / 2;
    }
}

static void spend(float cost) {
    g_stamina.stamina -= cost * g_stamina.drain_multiplier;
    if (g_stamina.stamina < 0.0f) g_stamina.stamina = 0.0f;
    g_stamina.idle_seconds = 0.0f;
}

void hero_core_on_input(u32 site, void *a0, void *a1, void *a2, u32 stock_result) {
    (void)a2;
    ensure_init();
    if (!a0) return;

    /* Same argument reading as the input wrappers: a1 is the sample count. */
    u32 count = (u32)(unsigned long)a1;
    if (count == 0 || count > 64) count = stock_result;
    if (count == 0 || count > 64) return;

    HidView view = {a0, count, 0};

    if (site != 3) return;   /* only site 3 runs during gameplay */

    u64 buttons = hid_merge_buttons(&view);
    g_hc_seen |= buttons;
    g_hc_count = count;
    u64 pressed = buttons & ~g_prev_buttons;
    g_prev_buttons = buttons;

    float m2 = stick_mag2(&view);
    u32 moving = m2 > STICK_MOVE2;
    u32 running = (buttons & BTN_A) && moving;   /* sprint = A held while moving */

    /* State advances once per rendered frame (the reader can run more than once). */
    u32 now = hud_frame_count();
    u32 frames = now - g_last_frame;
    int new_frame = (now == 0) || frames != 0;
    if (frames > 4) frames = 1;
    g_last_frame = now;
    float dt = (now == 0 ? 1u : frames) * DT_FRAME;

    if (g_exhausted && g_stamina.stamina >= EXHAUST_RECOVER) g_exhausted = 0;
    if (!g_exhausted && g_stamina.stamina <= 0.0f) g_exhausted = 1;

    if (new_frame) {
        /* Costs come from Link's ACTIONS (player_track), not from button presses. */
        u32 ev = player_take_events();
        if (ev & PEV_ATTACK) {
            g_combat_hold = COMBAT_HOLD_FRAMES;
            stamina_begin_action(&g_stamina, &g_config, ACTION_SLASH, 0, 0, ++g_action_token);
            g_hc_dbg[4]++;
        }
        if (ev & PEV_ROLL) {
            g_combat_hold = COMBAT_HOLD_FRAMES;
            spend(g_config.roll_cost);
            g_hc_dbg[0]++;
        }
        if (ev & PEV_SIDESTEP) {
            g_combat_hold = COMBAT_HOLD_FRAMES;
            spend(g_config.sidestep_cost);
        }
        if (ev & PEV_GUARDHIT) {   /* a hit on the shield costs stamina */
            g_combat_hold = COMBAT_HOLD_FRAMES;
            spend(g_config.block_base_cost);
        }
        if (ev & PEV_JUMP) {
            spend(JUMP_COST);
            g_hc_dbg[1]++;
        }
        u32 in_combat = g_combat_hold != 0;
        if (g_combat_hold) g_combat_hold--;
        g_stamina.in_combat = in_combat;

        /* Sprint: A held while the move state is active drains gradually. */
        u32 draining = running && !g_exhausted && g_stamina.stamina > 0.0f && player_state_is("Move");
        if (draining) {
            g_stamina.stamina -= RUN_DRAIN_PER_SEC * dt * g_stamina.drain_multiplier;
            if (g_stamina.stamina < 0.0f) g_stamina.stamina = 0.0f;
            g_stamina.idle_seconds = 0.0f;
            g_hc_dbg[2]++;
        }
        stamina_tick(&g_stamina, &g_config, dt, LIFE_QUARTERS, in_combat, draining, 0, 0);
        if (g_stamina.stamina <= 0.0f) g_exhausted = 1;
        g_hc_dbg[3] = 0x10000000u + g_exhausted;

        hud_set_stamina(g_stamina.stamina, g_stamina.cap,
                        (in_combat || draining || g_exhausted || g_stamina.stamina < g_stamina.cap - 0.5f)
                            ? 1.0f : 0.0f);
    }
    /* Filters on the input the game sees (every call, not only the first of a frame). */
    u64 strip = 0;
    if (g_exhausted) strip |= BTN_X | BTN_A;                          /* no jump, no roll */
    if (g_stamina.in_combat && g_stamina.stamina <= 0.0f) strip |= BTN_Y;   /* no sword at 0 */
    if (strip) {
        for (u32 i = 0; i < count; i++) {
            u64 b = hid_get_buttons(&view, i);
            hid_set_buttons(&view, i, b & ~strip);
        }
    }
}
