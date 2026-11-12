#include "../../core/dispatch.h"
#include "../../core/hid.h"

/* classic_slots (F3): replica of the "legacy" extra item buttons.
 *
 * Controls on this game: X jump, A dodge, Y sword, B / L / R / ZR are the free
 * buttons. In-game R equips an item into the HUD item box and ZR uses it
 * (hold and release). The stock function at 0x1211C00 is what that equip ends up
 * calling; its third argument is the item index (inventory slot order:
 * 0 stick, 1 nut, 3 boomerang ...).
 *
 * Classic slots: B, L, R and ZR can each hold an item; an empty slot keeps its
 * normal behaviour. Pressing an assigned one:
 *   1. EQUIP   - R is pressed for a few frames and at the stock call (slot site 3,
 *                pre-hook) the item index is replaced by the slot's item;
 *   2. HOLD    - ZR is held while the slot button is held;
 *   3. RESTORE - on release the item that was in the box before is re-equipped.
 */
#define SLOT_BASE 0x10000000u
u32 g_slot_count[4] = {SLOT_BASE, SLOT_BASE, SLOT_BASE, SLOT_BASE};

#define LOG_N 24
typedef struct { u32 site; u32 result; unsigned long long a0, a1, a2; } SlotLog;
SlotLog g_slot_log[LOG_N] = {{0x7FFFFFFFu, 0, 0, 0, 0}};   /* non-zero: lives in .data */
u32 g_slot_log_n = SLOT_BASE;

enum { SLOT_B = 0, SLOT_L = 1, SLOT_R = 2, SLOT_ZR = 3, SLOT_N = 4 };
static const u64 SLOT_MASK[SLOT_N] = {BTN_B, BTN_L, BTN_R, BTN_ZR};

/* Item index per slot, -1 = empty (button stays normal). Test defaults; assignment
 * is done in game with ZL + slot button (cycles the item). (.data) */
int g_assign[SLOT_N] = {3, 1, 2, -1};

enum { PH_IDLE = 0, PH_EQUIP, PH_HOLD, PH_GAP, PH_RESTORE };
#define EQUIP_TICKS 4
#define GAP_TICKS 6

int g_pending = -1;        /* item index to force on the next stock call */
int g_zr_item = -1;        /* item the game's own buttons last selected */
int g_phase = PH_IDLE;
int g_active = -1;
u32 g_phase_t;
u64 g_cl_prev;
u32 g_cl_dbg[4] = {SLOT_BASE, SLOT_BASE, SLOT_BASE, SLOT_BASE};  /* presses, overrides, restores */

void hud_set_slot(u32 i, float icon, float count, float show);

/* Items a slot can cycle through (inventory slot order) and their ItemPattern icon
 * frame, measured in game with the CLASSIC_PROBE build (docs/RE-NOTES.md). */
static const int ITEM_CYCLE[] = {-1, 1, 2, 3, 4, 5, 6, 7, 9, 10, 13, 14, 18, 30, 31};
#define ITEM_CYCLE_N ((int)(sizeof(ITEM_CYCLE) / sizeof(ITEM_CYCLE[0])))
static int icon_of(int item) {
    switch (item) {
    case 0: return 0;   case 1: return 6;   case 2: return 4;   case 3: return 3;
    case 4: return 1;   case 5: return 33;  case 6: return 34;  case 7: return 32;
    case 9: return 5;   case 10: return 8;  case 13: return 2;  case 14: return 23;
    case 18: return 36; case 30: return 24; case 31: return 9;
    default: return 0;
    }
}
static u64 g_swallow;
static void cycle_slot(int s) {
    int pos = 0;
    for (int i = 0; i < ITEM_CYCLE_N; i++) if (ITEM_CYCLE[i] == g_assign[s]) pos = i;
    g_assign[s] = ITEM_CYCLE[(pos + 1) % ITEM_CYCLE_N];
}

/* ---- temporary probe: learn item index -> icon frame (CLASSIC_PROBE) ---- */
extern float g_last_pat_frame, g_last_num_frame;
extern u32 g_pat_changes;
typedef struct { u32 idx; u32 result; float pat; float num; } MapEntry;
MapEntry g_map[40] = {{0x7FFFFFFFu, 0, 0, 0}};
u32 g_map_n = SLOT_BASE;
static u32 g_probe_t, g_probe_idx;
static int g_probe_wait;
#ifdef CLASSIC_PROBE
static void probe_step(void) {
    g_probe_t++;
    if (g_probe_t < 3600) return;              /* let the game settle first (~30 s) */
    u32 phase = (g_probe_t - 3600) % 180;
    if (phase == 0 && g_probe_idx < 32) {
        g_pending = (int)g_probe_idx;
        g_phase = PH_EQUIP; g_phase_t = 0; g_active = 0;
        g_probe_wait = 1;
    }
    if (phase == 150 && g_probe_wait) {
        MapEntry *m = &g_map[(g_map_n - SLOT_BASE) % 40];
        g_map_n++;
        m->idx = g_probe_idx;
        m->result = g_slot_log[(g_slot_log_n - SLOT_BASE - 1) % LOG_N].result;
        m->pat = g_last_pat_frame;
        m->num = g_last_num_frame;
        g_probe_idx++;
        g_probe_wait = 0;
    }
}
#endif

static void set_all(const HidView *v, u64 clear, u64 set) {
    for (u32 i = 0; i < v->count; i++) {
        u64 b = hid_get_buttons(v, i);
        hid_set_buttons(v, i, (b & ~clear) | set);
    }
}

void classic_slots_on_input(u32 site, void *a0, void *a1, void *a2, u32 stock_result) {
    (void)a2;
    if (site != 3 || !a0) return;
    u32 count = (u32)(unsigned long)a1;
    if (count == 0 || count > 64) count = stock_result;
    if (count == 0 || count > 64) return;
    HidView view = {a0, count, 0};

    u64 buttons = hid_merge_buttons(&view);
    u64 pressed = buttons & ~g_cl_prev;
    g_cl_prev = buttons;
#ifdef CLASSIC_PROBE
    probe_step();
#endif

    /* Assignment: hold ZL and press B / L / R to cycle that slot's item. The press
     * is swallowed until released so it does not also act. (ZR is not assignable
     * this way: ZL+ZR is the normal target-and-use.) */
    for (int s = 0; s < SLOT_ZR; s++) {
        if ((buttons & BTN_ZL) && (pressed & SLOT_MASK[s]) && g_phase == PH_IDLE) {
            cycle_slot(s);
            g_swallow |= SLOT_MASK[s];
        }
    }
    g_swallow &= buttons;
    if (g_swallow) set_all(&view, g_swallow, 0);
    buttons &= ~g_swallow;
    pressed &= ~g_swallow;

    /* Publish every slot to the unified HUD (core/hud.c draws it). */
    for (int s = 0; s < SLOT_N; s++) {
        int it = g_assign[s];
        hud_set_slot((u32)s, it >= 0 ? (float)icon_of(it) : 0.0f, -1.0f, it >= 0 ? 1.0f : 0.0f);
    }

    u64 all_slot = 0;
    for (int s = 0; s < SLOT_N; s++) if (g_assign[s] >= 0) all_slot |= SLOT_MASK[s];

    if (g_phase == PH_IDLE) {
        for (int s = 0; s < SLOT_N; s++) {
            if ((pressed & SLOT_MASK[s]) && g_assign[s] >= 0) {
                g_active = s;
                g_pending = g_assign[s];
                g_phase = PH_EQUIP;
                g_phase_t = 0;
                g_cl_dbg[0]++;
                break;
            }
        }
    }

    /* Assigned slot buttons never reach the game directly. */
    u64 set = 0;
    switch (g_phase) {
    case PH_EQUIP:
        set = BTN_R;
        if (++g_phase_t >= EQUIP_TICKS) g_phase = PH_HOLD;
        break;
    case PH_HOLD:
        if (buttons & SLOT_MASK[g_active]) {
            set = BTN_ZR;
        } else {
            g_phase = PH_GAP;
            g_phase_t = 0;
        }
        break;
    case PH_GAP:
        if (++g_phase_t >= GAP_TICKS) {
            if (g_zr_item >= 0 && g_zr_item != g_assign[g_active]) {
                g_pending = g_zr_item;
                g_phase = PH_RESTORE;
                g_phase_t = 0;
                g_cl_dbg[2]++;
            } else {
                g_phase = PH_IDLE;
            }
        }
        break;
    case PH_RESTORE:
        set = BTN_R;
        if (++g_phase_t >= EQUIP_TICKS) { g_phase = PH_IDLE; g_pending = -1; }
        break;
    default:
        break;
    }
    set_all(&view, all_slot, set);
}

/* Called before the stock item function: may replace its item index (x2). */
u64 classic_slots_pre(u32 site, void *a0, void *a1, u64 a2) {
    (void)a0; (void)a1;
    if (site != 3) return a2;
    if (g_pending >= 0) {
        g_cl_dbg[1]++;
        u64 r = (u64)(long long)g_pending;
        g_pending = -1;
        return r;
    }
    g_zr_item = (int)a2;   /* a natural call: remember the box item */
    return a2;
}

void classic_slots_on_call(u32 site, void *a0, void *a1, void *a2, u32 stock_result) {
    if (site < 4) g_slot_count[site]++;
    SlotLog *e = &g_slot_log[(g_slot_log_n - SLOT_BASE) % LOG_N];
    g_slot_log_n++;
    e->site = site;
    e->result = stock_result;
    e->a0 = (unsigned long long)a0;
    e->a1 = (unsigned long long)a1;
    e->a2 = (unsigned long long)a2;
}

