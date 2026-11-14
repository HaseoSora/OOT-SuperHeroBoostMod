#include "../../core/dispatch.h"
#include "../../core/hid.h"
#include "../../core/config.h"

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
#define BTN_RSTICK 0x0020ull   /* right stick click (R3) */
static const u64 SLOT_MASK[SLOT_N] = {BTN_B, BTN_L, BTN_R, BTN_ZR};

/* Item index per slot, -1 = empty (button stays normal). Test defaults; assigned in the pause menu's Items tab
 * with X / L / R. (.data) */
int g_assign[SLOT_N] = {3, 1, 2, -1};

enum { PH_IDLE = 0, PH_EQUIP, PH_HOLD, PH_GAP, PH_RESTORE, PH_ZRBACK };
#define EQUIP_TICKS 4
#define GAP_TICKS 20

int g_pending = -1;        /* item index to force on the next stock call (old R-press method, unused) */
int g_saved = -1;          /* item box content before a slot use (the ZR item) */
int g_borrowed;            /* a slot item is in the box; the ZR item goes back when ZR is pressed */
int g_borrow_item = -1;    /* the slot item in the box */
int g_zr_item = -1;        /* item the game's own buttons last selected */
int g_phase = PH_IDLE;
int g_active = -1;
u32 g_phase_t;
u64 g_cl_prev;
u32 g_cl_dbg[4] = {SLOT_BASE, SLOT_BASE, SLOT_BASE, SLOT_BASE};  /* presses, overrides, restores */

void hud_slot_item(u32 slot, int item);
int player_active(void);
int player_state_is(const char *name);   /* core/player.c: Link's current action state */
int player_state_starts(const char *prefix);
const char *player_state_name(void);
char g_cl_refused[24];   /* diagnostic: Link's state when a slot press was ignored (not free) */
int hud_zr_item(void);
void hud_zr_hold(int hold);
int hud_ingame(void);   /* core/hud.c: 0 while a menu covers the game (pause ...) */
int hud_menu_items(void);   /* core/hud.c: the pause menu's Items tab is open */
int hud_menu_item(void);    /* core/hud.c: item index highlighted there (-1: none / not owned) */   /* core/hud.c: keep showing the ZR item while a slot item borrows the item box */
/* The game's own "put this item in the item box" call, as the R button makes it (main+0x33C9AB4):
 * main+0x1211C00(item manager, item set, item index, 1, 1); manager = **(main+0x4C7E0D0),
 * set = byte +0x5C0 of **(main+0x4C7E2A8). Calling it directly equips without pressing R (R opens the selector). */
extern char SLOTFN[], ITEM_MGR_SLOT[], ITEM_SET_SLOT[];
u32 g_equip_dbg[2];   /* direct equips done, skipped (no manager) */
static void equip_now(int item) {
    u64 slot = *(u64 *)ITEM_MGR_SLOT, sets = *(u64 *)ITEM_SET_SLOT;
    u64 mgr = slot ? *(u64 *)slot : 0, so = sets ? *(u64 *)sets : 0;
    if (!mgr || !so || item < 0) { g_equip_dbg[1]++; return; }
    u64 set = *(volatile unsigned char *)(so + 0x5C0);
    ((void (*)(u64, u64, u64, u64, u64))(void *)SLOTFN)(mgr, set, (u64)item, 1, 1);
    g_equip_dbg[0]++;
}   /* core/hud.c: item index of the game's own (hidden) item box, -1 = unknown */

/* Items a slot can cycle through (inventory slot order) and their ItemPattern icon
 * frame, measured in game with the CLASSIC_PROBE build (docs/RE-NOTES.md). */
static const int ITEM_CYCLE[] = {-1, 1, 2, 3, 4, 5, 6, 7, 9, 10, 13, 14, 18, 30, 31};
#define ITEM_CYCLE_N ((int)(sizeof(ITEM_CYCLE) / sizeof(ITEM_CYCLE[0])))
__attribute__((unused)) static int icon_of(int item) {
    switch (item) {
    case 0: return 0;   case 1: return 6;   case 2: return 4;   case 3: return 3;
    case 4: return 1;   case 5: return 33;  case 6: return 34;  case 7: return 32;
    case 9: return 5;   case 10: return 8;  case 13: return 2;  case 14: return 23;
    case 18: return 36; case 30: return 24; case 31: return 9;
    default: return 0;
    }
}
static u64 g_swallow;
__attribute__((unused)) static void cycle_slot(int s) {
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

    /* Publish the slots to the HUD replica (core/hud.c): B, L, R as assigned (ZR mirrors the game's own box). */
    for (int s = 0; s < SLOT_N; s++)
        hud_slot_item((u32)s, s == SLOT_ZR && g_assign[s] < 0 ? g_zr_item : g_assign[s]);

    u64 buttons = hid_merge_buttons(&view);
    u64 pressed = buttons & ~g_cl_prev;
    g_cl_prev = buttons;

    /* Pause menu, Items tab: X, L and R assign the highlighted item to the B, L and R slots (like Classic's X / L / R;
     * B stays "back"). An item already on another slot swaps with it. The game's ZL / ZR still change tabs. */
    if (g_ootcfg.classic_replica && hud_menu_items()) {
        static const u64 MENU_BTN[SLOT_ZR] = {BTN_X, BTN_L, BTN_R};   /* -> SLOT_B, SLOT_L, SLOT_R */
        for (int s = 0; s < SLOT_ZR; s++) {
            if (!(pressed & MENU_BTN[s])) continue;
            int it = hud_menu_item();
            if (it < 0) continue;
            for (int o = 0; o < SLOT_ZR; o++) if (o != s && g_assign[o] == it) g_assign[o] = g_assign[s];
            g_assign[s] = it;
            g_cl_dbg[3]++;
        }
        set_all(&view, BTN_X | BTN_L | BTN_R, 0);
        g_phase = PH_IDLE; g_swallow = 0;
        return;
    }

    /* Link must be free to act: standing or moving. Menus, the ocarina, dialogues, the item selector, climbing,
     * swimming ... keep every button as the game means it (B = back / cancel there). A use in progress goes on. */
    int ingame = player_active() && hud_ingame();
    int free_now = ingame && (player_state_is("Wait") || player_state_is("Move") ||
                              player_state_starts("LockOn"));   /* LockOn*: ZL held (target or free), aiming */
    if (!g_ootcfg.classic_replica || (!free_now && g_phase == PH_IDLE)) {
        if (ingame && (pressed & (BTN_B | BTN_L | BTN_R))) {   /* remember why a slot button did nothing */
            const char *n = player_state_name();
            for (int i = 0; i < 23; i++) g_cl_refused[i] = n[i];
        }
        g_swallow = 0;
        return;
    }
    if (!ingame) {   /* a menu opened mid-use (pause ...): stop holding anything */
        g_phase = PH_IDLE; g_swallow = 0;
        return;
    }

    /* What the game has in its item box. While a slot item borrows it, a different item there means the player
     * picked a new one (R selector / pause menu): that becomes the ZR item and nothing is put back. */
    int box = hud_zr_item();
    if (!g_borrowed) {
        if (box >= 0) g_zr_item = box;
    } else if (g_phase == PH_IDLE && box >= 0 && box != g_borrow_item && box != g_saved) {
        g_borrowed = 0; g_zr_item = box; hud_zr_hold(0);
    }

    g_swallow &= buttons;
    if (g_swallow) set_all(&view, g_swallow, 0);
    buttons &= ~g_swallow;
    pressed &= ~g_swallow;

    u64 all_slot = 0;
    for (int s = 0; s < SLOT_N; s++) if (g_assign[s] >= 0) all_slot |= SLOT_MASK[s];

    if (g_phase == PH_IDLE) {
        for (int s = 0; s < SLOT_N; s++) {
            if ((pressed & SLOT_MASK[s]) && g_assign[s] >= 0) {
                if (!g_borrowed) { g_saved = g_zr_item; g_borrowed = 1; hud_zr_hold(1); }
                g_active = s;
                g_borrow_item = g_assign[s];
                if (box != g_assign[s]) equip_now(g_assign[s]);   /* already there (used again): no swap */
                g_phase = PH_EQUIP;
                g_phase_t = 0;
                g_cl_dbg[0]++;
                break;
            }
        }
        /* ZR pressed while a slot item borrows the box: put the ZR item back first, then let ZR through */
        if (g_phase == PH_IDLE && g_borrowed && (pressed & BTN_ZR) && g_saved >= 0) {
            equip_now(g_saved);
            g_phase = PH_ZRBACK;
            g_phase_t = 0;
            g_cl_dbg[2]++;
        }
    }

    /* Assigned slot buttons never reach the game directly: the item is used through ZR. */
    u64 set = 0, clear = all_slot;
    switch (g_phase) {
    case PH_EQUIP:                             /* let the equip settle before using it */
        if (++g_phase_t >= EQUIP_TICKS) g_phase = PH_HOLD;
        break;
    case PH_HOLD:                              /* ZR follows the slot button (aim while held, throw on release) */
        if (buttons & SLOT_MASK[g_active]) set = BTN_ZR;
        else g_phase = PH_IDLE;                /* the item stays in the box: nothing is swapped mid-use */
        break;
    case PH_ZRBACK:                            /* hold ZR back until the box has the ZR item again */
        clear |= BTN_ZR;
        if (box == g_saved || ++g_phase_t > 30) {
            g_borrowed = 0; hud_zr_hold(0);
            g_phase = PH_IDLE;                 /* ZR (still held by the player) reaches the game from now on */
        } else if (g_phase_t % 8 == 0) {
            equip_now(g_saved);
        }
        break;
    default:
        g_phase = PH_IDLE;
        break;
    }
    set_all(&view, clear, set);
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

