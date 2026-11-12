#include "../../core/dispatch.h"
#include "../../core/hid.h"
#include "stamina.h"

/* hero_core (F2): combat stamina. Behaviour replica, not Hero Core code.
 *
 * Site 0 drives the state: it counts frames, detects the attack press (B), and
 * charges the slash cost. While stamina is empty the attack buttons (B, ZR) are
 * removed from the input buffer at every hooked site, so the game does not
 * attack. Values come from stamina_default_config and are placeholders until
 * they are checked against the documented Hero Core numbers (docs/RE-NOTES.md).
 */

void hud_set_stamina(float value, float cap, float show);

#define LIFE_QUARTERS 20u       /* placeholder: 5 hearts, not read from the game yet */
#define COMBAT_HOLD_FRAMES 180u
#define DT_FRAME (1.0f / 60.0f)

/* Diagnostics read by tools/live_check.py (in .data so they are file-backed). */
u64 g_hc_seen = 0x100000000ull;  /* OR of every button mask seen at site 3 (+base) */
u32 g_hc_count = 0x10000000u;

static StaminaState g_stamina;
static StaminaConfig g_config;
static u32 g_initialized;
static u64 g_prev_buttons;
static u32 g_action_token;
static u32 g_combat_hold;
static u32 g_block_attack;

static void ensure_init(void) {
    if (g_initialized) return;
    stamina_default_config(&g_config);
    stamina_init(&g_stamina, &g_config, LIFE_QUARTERS);
    g_initialized = 1;
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

    /* Only site 3 runs during gameplay (live check: sites 0,1,2,4 never fire). */
    if (site == 3) {
        u64 buttons = hid_merge_buttons(&view);
        g_hc_seen |= buttons;
        g_hc_count = count;
        u64 pressed = buttons & ~g_prev_buttons;
        g_prev_buttons = buttons;

        /* Y = sword attack, A = dodge/roll, X = jump, B is free (Classic slot). */
        if (pressed & (BTN_A | BTN_Y)) {
            g_combat_hold = COMBAT_HOLD_FRAMES;
        }
        u32 in_combat = g_combat_hold != 0;
        if (g_combat_hold) g_combat_hold--;

        g_stamina.in_combat = in_combat;
        stamina_tick(&g_stamina, &g_config, DT_FRAME, LIFE_QUARTERS, in_combat, 0, 0, 0);

        if (in_combat) {
            /* begin_action returns 0 when stamina is already empty; the filter below
             * then strips the buttons so the game does not perform the action. */
            if (pressed & BTN_Y)
                stamina_begin_action(&g_stamina, &g_config, ACTION_SLASH, 0, 0, ++g_action_token);
            if (pressed & BTN_A)
                stamina_begin_action(&g_stamina, &g_config, ACTION_ROLL, 0, 0, ++g_action_token);
        }

        /* Publish to the unified HUD (core/hud.c draws it, we never do). */
        hud_set_stamina(g_stamina.stamina, g_stamina.cap,
                        (in_combat || g_stamina.stamina < g_stamina.cap - 0.5f) ? 1.0f : 0.0f);

        g_block_attack = in_combat && g_stamina.stamina <= 0.0f;
    }

    /* Exhausted: sword (Y) and dodge (A) are removed from the input. Item buttons
     * stay free (Classic slots use them). */
    if (g_block_attack) {
        for (u32 i = 0; i < count; i++) {
            u64 b = hid_get_buttons(&view, i);
            hid_set_buttons(&view, i, b & ~(BTN_A | BTN_Y));
        }
    }
}

