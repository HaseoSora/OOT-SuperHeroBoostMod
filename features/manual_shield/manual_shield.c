/* manual shield: ZL holds the guard, L toggles targeting and R3 cancels it.
 *
 * Ported from the behaviour of REXCRAFT88's Manual Shield mod for the same game
 * build. The two halves are:
 *   - manual_shield_on_input: consumes the physical L/ZL bits in the gameplay
 *     HID samples and synthesises ZL while targeting or holding the guard;
 *   - manual_shield_on_frame: keeps the native guard state off unless ZL is
 *     held (the game would otherwise raise the shield while targeting), draws
 *     the shield on guard entry and scopes the AS Bool14 setter through the
 *     small assembly wrappers in manual_shield.S.
 *
 * The option is read from ShbConfig.manual_shield; with it off both halves are
 * pass-through and the stock game behaviour is kept.
 */
#include "../../core/dispatch.h"
#include "../../core/hid.h"
#include "../../core/config.h"

typedef unsigned char u8;

#define MS_BTN_L   0x40ull
#define MS_BTN_R3  0x20ull
#define MS_BTN_ZL  0x100ull

int player_active(void);
int player_dead(void);
int player_state_is(const char *name);
int player_state_starts(const char *prefix);
const char *player_state_name(void);

/* main-relative functions (core/link.ld) */
extern void *resolve_player(void *);
extern u64 get_guard_component(void *);
extern void native_draw_equipment(void *, u32);
extern u32 as_int(void *, u32);
extern u32 as_bool(void *, u32);

/* State shared with the assembly wrappers (do not rename). */
u64 g_ms_state;          /* player state returned by resolve_player (x20/x21 in the guard sites) */
u64 g_ms_iface;          /* the player's AS interface (setter x0, guard component owner) */
u64 g_ms_equipment;      /* actor table +0x200: shield/equipment request target */
u8 g_ms_active;          /* manual shield option enabled (read by the wrappers) */
u8 g_ms_allowed;         /* this frame's guard decision (read by the setter wrapper) */
u8 g_ms_held;            /* ZL physically held this frame (and not carrying) */
u8 g_ms_carrying;        /* Link is carrying/lifting something */
u8 g_ms_targeting;       /* L toggled targeting */
u8 g_ms_prev_l;          /* previous sampled L, for the toggle edge */
u8 g_ms_last_allowed;    /* previous frame's decision, for the shield draw */
u32 g_ms_tick;           /* scheduler frames (manual_shield_on_frame calls) */
u32 g_ms_last_tick;      /* tick at the previous gameplay HID read */
u32 g_ms_stale;          /* gameplay HID reads without a scheduler tick */

/* Diagnostic counters for tools/live_check (not used by the game). */
u32 g_ms_dbg[8] = {0x10000000u, 0, 0, 0, 0, 0, 0, 0};
/* 0 reads, 1 held, 2 targeting, 3 L toggles, 4 R3 cancels, 5 stale reads, 6 frames, 7 guard entries */

static u64 rd(u64 p, unsigned off) { return *(volatile u64 *)(p + off); }

static u64 current_guard_interface(u64 actor) {
    u64 table = rd(actor, 0x270);
    if (!table) return 0;
    u64 anim = rd(table, 0x40);
    if (!anim) return 0;
    u64 p = rd(anim, 0x18);
    if (!p) return 0;
    p = rd(p, 0x18);
    if (!p) return 0;
    return rd(p, 0x40);
}

static u32 player_carrying(u64 actor) {
    if (!actor) return 0;
    u64 table = rd(actor, 0x270);
    if (!table) return 0;
    u64 lifter = rd(table, 0x2C8);
    if (!lifter) return 0;
    return *(volatile u32 *)(lifter + 0x2B0) != 0;
}

/* Actions that keep both hands (or a weapon) busy; guard must not fight them. */
static u32 guard_action_busy(u64 state) {
    if (!state) return 0;
    for (u32 i = 0; i < 2; i++) {
        const char *name = (const char *)rd(state, 0x238 + i * 0xD8);
        if (!name) continue;
        u64 first = *(const volatile u64 *)name;
        if (first == 0x6d657449646c6f48ull || *(const volatile u32 *)name == 0x7466694c ||
            *(const volatile u32 *)name == 0x62617247 ||
            first == 0x6772616843776f42ull || first == 0x746f6f6853776f42ull ||
            first == 0x616f4c6552776f42ull || first == 0x746f68736b6f6f48ull ||
            first == 0x6e6172656d6f6f42ull || first == 0x6573726f486d6941ull)
            return 1;
    }
    return 0;
}

static u32 guard_busy(u64 iface, u64 state) {
    if (!iface) return 1;
    if (g_ms_carrying || guard_action_busy(state)) return 1;
    if (as_bool((void *)iface, 62) || as_bool((void *)iface, 86)) return 1;
    if (as_int((void *)iface, 1) == 2) return 1;
    return 0;
}

static void set_native_bool(u64 iface, u32 id, u32 value) {
    u64 vtable = *(volatile u64 *)iface;
    if (!vtable) return;
    void (*setter)(void *, u32, u32) = (void (*)(void *, u32, u32))*(volatile u64 *)(vtable + 0x88);
    if (setter) setter((void *)iface, id, value);
}

void manual_shield_on_input(u32 site, void *a0, void *a1, void *a2, u32 stock_result) {
    (void)a2;
    if (site != 3 || !a0) return;
    if (!g_shbcfg.manual_shield) {
        g_ms_active = 0;
        g_ms_held = 0;
        g_ms_allowed = 0;
        g_ms_targeting = 0;
        g_ms_prev_l = 0;
        return;
    }
    g_ms_active = 1;
    u32 count = (u32)(unsigned long)a1;
    if (count == 0 || count > 64) count = stock_result;
    if (count == 0 || count > 64) return;
    HidView view = {a0, count, 0};

    /* The scheduler frame tells us which reads belong to a new frame. While the
     * player scheduler is paused the game keeps polling this path: reserve L/ZL
     * there too, so a paused menu cannot change the targeting state. */
    u32 tick = g_ms_tick;
    if (tick == g_ms_last_tick) ++g_ms_stale;
    else { g_ms_last_tick = tick; g_ms_stale = 0; }
    if (g_ms_stale > 8) {
        g_ms_prev_l = (u8)((hid_get_buttons(&view, 0) & MS_BTN_L) != 0);
        g_ms_held = 0;
        g_ms_allowed = 0;
        for (u32 i = 0; i < count; i++)
            hid_set_buttons(&view, i, hid_get_buttons(&view, i) & ~(MS_BTN_L | MS_BTN_ZL));
        g_ms_dbg[5]++;
        return;
    }
    if (player_dead()) {   /* death ragdoll / game over: never filter the screen's input */
        g_ms_prev_l = (u8)((hid_get_buttons(&view, 0) & MS_BTN_L) != 0);
        g_ms_held = 0;
        g_ms_allowed = 0;
        g_ms_targeting = 0;
        g_ms_last_allowed = 0;
        return;
    }
    if (!player_active()) {   /* title, loading, pause: keep the toggles from firing spuriously */
        g_ms_prev_l = (u8)((hid_get_buttons(&view, 0) & MS_BTN_L) != 0);
        g_ms_held = 0;
        g_ms_allowed = 0;
        for (u32 i = 0; i < count; i++)
            hid_set_buttons(&view, i, hid_get_buttons(&view, i) & ~(MS_BTN_L | MS_BTN_ZL));
        return;
    }

    u32 held_guard = 0, held_l = 0, held_r3 = 0;
    for (u32 i = 0; i < count; i++) {
        u64 bits = hid_get_buttons(&view, i);
        if (i == 0) {
            held_guard = (bits & MS_BTN_ZL) != 0 && !g_ms_carrying;
            held_l = (bits & MS_BTN_L) != 0;
            held_r3 = (bits & MS_BTN_R3) != 0;
        }
        /* consume the physical guard and L selector; ZL is synthesised below */
        hid_set_buttons(&view, i, bits & ~(MS_BTN_L | MS_BTN_ZL));
    }

    u32 targeting = g_ms_targeting;
    if (held_l && !g_ms_prev_l) { targeting ^= 1u; g_ms_dbg[3]++; }
    if (held_r3) { targeting = 0; g_ms_dbg[4]++; }
    g_ms_prev_l = (u8)(held_l != 0);
    g_ms_targeting = (u8)(targeting != 0);
    g_ms_held = (u8)(held_guard != 0);

    if (targeting || held_guard) {
        for (u32 i = 0; i < count; i++)
            hid_set_buttons(&view, i, hid_get_buttons(&view, i) | MS_BTN_ZL);
    }
    g_ms_dbg[0]++;
    g_ms_dbg[1] = held_guard;
    g_ms_dbg[2] = targeting;
}

void manual_shield_on_frame(void *scheduler) {
    g_ms_iface = 0;
    g_ms_equipment = 0;
    g_ms_carrying = 0;
    g_ms_allowed = 0;
    if (!g_shbcfg.manual_shield) {
        g_ms_active = 0;
        g_ms_state = 0;
        g_ms_tick = 0;
        g_ms_last_tick = 0;
        g_ms_stale = 0;
        g_ms_held = 0;
        g_ms_targeting = 0;
        g_ms_prev_l = 0;
        g_ms_last_allowed = 0;
        return;
    }
    g_ms_active = 1;
    ++g_ms_tick;
    g_ms_dbg[6]++;

    if (!scheduler) return;
    u64 state = (u64)resolve_player(scheduler);
    if (!state) { g_ms_state = 0; return; }
    g_ms_state = state;
    u64 actor = rd(state, 0x18);
    if (!actor) return;
    g_ms_carrying = (u8)player_carrying(actor);
    u64 component = get_guard_component((void *)actor);
    if (!component) return;

    u64 iface = current_guard_interface(actor);
    if (iface) g_ms_iface = iface;
    u64 table = rd(actor, 0x270);
    u64 equipment = table ? rd(table, 0x200) : 0;
    if (iface && equipment) g_ms_equipment = equipment;

    /* The option is standalone: no stamina gate (the stamina feature still
     * charges its own held/hit costs if it is enabled). */
    u32 held = g_ms_held != 0;
    u32 alive = player_active() && !player_dead();
    u32 allowed = iface && held && alive && !guard_busy(iface, state);
    g_ms_allowed = (u8)(allowed != 0);

    /* Match the native guard flag without requesting target/camera. */
    u32 *state_flags = (u32 *)(state + 0xE50);
    if (allowed) *state_flags |= 0x80100u;
    else *state_flags &= ~0x80000u;
    u32 *flags = (u32 *)(component + 0x24);
    if (allowed) *flags |= 0x20u;
    else *flags &= ~0x20u;

    /* The stock setter would raise the shield on targeting; the wrapper keeps it
     * scoped to this interface + Bool14 and follows g_ms_allowed. */
    if (iface) set_native_bool(iface, 14, allowed);

    /* Draw only the shield: targeting must not make the hook draw the sword. */
    if (allowed && !g_ms_last_allowed) {
        if (equipment && (!iface || as_int((void *)iface, 1) != 2)) {
            native_draw_equipment((void *)equipment, 4);
            g_ms_dbg[7]++;
        }
    }
    g_ms_last_allowed = (u8)(allowed != 0);
}
