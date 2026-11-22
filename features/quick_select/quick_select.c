/* Quick select: hold D-pad Down / Up to toggle equipment without the pause menu.
 *
 *   Down: iron boots ("Armor_Adult_HeavyBoot")  <-> hover boots ("Armor_Adult_HoverBoot")
 *   Up:   the mask Link is wearing              <-> the Lens of Truth ("Armor_GlassTruth")
 *
 * Only items the player owns are used (IsGet.<actor>): without the flag the button does
 * nothing, so a save that never found the boots cannot end up wearing them.
 *
 * The slots are GameData strings, the same ones the pause menu writes:
 *   PlayerStatus.EquipBoot      String64 index 18 of the type
 *   PlayerStatus.EquipHeadArmor String64 index 20
 * Record layout (gdlive): table = mgr + 8 + 0x60*16, +0x08 count, +0x10 records;
 * record stride 0x108, live string at +0x74 (64 bytes). The game builds Link's equipment
 * from these strings when it creates him (save load / area load), which is also what the
 * pause menu relies on: the menu is open while it equips.
 *
 * Holding the D-pad button for HOLD_FRAMES toggles once; release and hold again for another.
 */
#include "../../core/dispatch.h"
#include "../../core/config.h"
#include "../../core/hid.h"
#include "../../core/remap.h"

#define DPAD_LEFT  0x1000ull
#define DPAD_UP    0x2000ull
#define DPAD_RIGHT 0x4000ull
#define DPAD_DOWN  0x8000ull

#define HOLD_FRAMES 18u

#define NAME_HEAVY "Armor_Adult_HeavyBoot"
#define NAME_HOVER "Armor_Adult_HoverBoot"
#define NAME_LENS  "Armor_GlassTruth"

extern char GAMEDATA_MGR[];       /* link.ld: main+0x4E842A8 */
extern char ITEM_MGR_SLOT[];      /* link.ld: main+0x4C7E0D0 (-> item/equipment manager) */
extern void equip_request(void *pouch, void *name_ref, u32 kind, u32 arg3);
extern void equip_refresh(void *pouch, void *name_ref, u32 one);
u32 hud_frame_count(void);
int hud_owns_name(const char *actor);   /* core/hud.c: IsGet.<actor> from the live Bool table */

static u32 g_hold;
static u32 g_latch;        /* a switch was made: wait for the button release */
static u32 g_release;      /* consecutive calls without the button (the same frame may call us several times) */
static u64 g_hold_btn;
static u32 g_last_frame;
char g_qs_cur[64];
static char g_mask_last[64];   /* the mask to come back to when leaving the Lens of Truth */

static int same(const char *a, const char *b) {
    u32 i = 0;
    while (a[i] && a[i] == b[i]) i++;
    return a[i] == b[i];
}

static void gd_put_group(unsigned char *rec, u32 ptr_off, u32 buf_off, const char *name) {
    u64 ptr = *(volatile u64 *)(rec + ptr_off);
    unsigned char *val = ptr ? (unsigned char *)ptr : rec + buf_off;
    u32 n = 0;
    while (name[n] && n < 63u) { val[n] = (unsigned char)name[n]; n++; }
    val[n] = 0;
    for (u32 i = n + 1u; i < 64u; i++) val[i] = 0;
    if (ptr) {   /* keep the record's inline buffer in step as well */
        for (u32 i = 0; i <= n; i++) rec[buf_off + i] = val[i];
        for (u32 i = n + 1u; i < 64u; i++) rec[buf_off + i] = 0;
    }
}
static void gd_set_string(u32 index, const char *name) {
    u64 mgr = *(volatile u64 *)GAMEDATA_MGR;
    if (!mgr) return;
    u64 table = mgr + 8ull + 0x60ull * 16ull;      /* String64 */
    u32 count = *(volatile u32 *)(table + 8);
    u64 recs = *(volatile u64 *)(table + 0x10);
    if (!recs || index >= count) return;
    unsigned char *rec = (unsigned char *)(recs + (u64)index * 0x108ull);
    gd_put_group(rec, 0x68, 0x74, name);   /* live value */
    gd_put_group(rec, 0xB8, 0xC4, name);   /* the copy the menu and the save keep */
}

static void gd_get_string(u32 index, char *out, u32 cap) {
    u64 mgr = *(volatile u64 *)GAMEDATA_MGR;
    out[0] = 0;
    if (!mgr) return;
    u64 table = mgr + 8ull + 0x60ull * 16ull;
    u32 count = *(volatile u32 *)(table + 8);
    u64 recs = *(volatile u64 *)(table + 0x10);
    if (!recs || index >= count) return;
    const unsigned char *rec = (const unsigned char *)(recs + (u64)index * 0x108ull);
    u64 ptr = *(volatile u64 *)(rec + 0x68);
    const char *val = ptr ? (const char *)ptr : (const char *)(rec + 0x74);
    u32 i = 0;
    while (val[i] && i + 1u < cap) { out[i] = val[i]; i++; }
    out[i] = 0;
}

static void copy64(char *dst, const char *src) {
    u32 i = 0;
    for (; i < 63u && src[i]; i++) dst[i] = src[i];
    dst[i] = 0;
}

/* Apply an equipment name through the game's own equip request (the pause menu's path), instead of
 * only writing the String64 record: the game rebuilds Link's equipment from the live request. */
typedef struct { const char *name; u64 len; } NameRef;
static u32 apply_equip(const char *name) {
    u64 slot = *(volatile u64 *)ITEM_MGR_SLOT;
    u64 mgr = slot ? *(volatile u64 *)slot : 0;
    if (!mgr || !name || !name[0]) return 0;
    static NameRef ref;
    ref.name = name; ref.len = 64u;
    equip_request((void *)mgr, &ref, 3u, 0u);
    equip_refresh((void *)mgr, &ref, 1u);
    return 1;
}

/* Down: iron <-> hover boots. Returns 1 when the string was changed. */
static u32 toggle_boots(void) {
    char cur[64];
    gd_get_string(18u, cur, sizeof cur);
    copy64(g_qs_cur, cur);
    if (same(cur, NAME_HEAVY)) {
        if (!hud_owns_name(NAME_HOVER)) return 0;
        gd_set_string(18u, NAME_HOVER);
        apply_equip(NAME_HOVER);
    } else if (same(cur, NAME_HOVER)) {
        if (!hud_owns_name(NAME_HEAVY)) return 0;
        gd_set_string(18u, NAME_HEAVY);
        apply_equip(NAME_HEAVY);
    } else {                                      /* default (Kokiri) boots: go to iron, else hover */
        if (hud_owns_name(NAME_HEAVY)) {
            gd_set_string(18u, NAME_HEAVY);
            apply_equip(NAME_HEAVY);
        } else if (hud_owns_name(NAME_HOVER)) {
            gd_set_string(18u, NAME_HOVER);
            apply_equip(NAME_HOVER);
        } else return 0;
    }
    return 1;
}

/* Up: the Lens of Truth <-> the mask Link wears. Returns 1 when the string was changed. */
static u32 toggle_mask(void) {
    char cur[64];
    gd_get_string(20u, cur, sizeof cur);
    copy64(g_qs_cur, cur);
    if (same(cur, NAME_LENS)) {
        if (!g_mask_last[0] || !hud_owns_name(g_mask_last)) return 0;
        gd_set_string(20u, g_mask_last);
        apply_equip(g_mask_last);
        return 1;
    }
    if (!hud_owns_name(NAME_LENS)) return 0;
    if (cur[0]) copy64(g_mask_last, cur);         /* remember the mask we are wearing */
    gd_set_string(20u, NAME_LENS);
    apply_equip(NAME_LENS);
    return 1;
}

/* ---- Armory: while the button with the armory role (button remap) is held, left / right change the sword and up /
 * down the shield, with the D-pad or the left stick; Link does not move meanwhile. Each step equips the next sword or
 * shield Link owns, through the game's own equip request (the pause menu's path), so the model, the HUD and the pause
 * menu follow at once. No age rule: the game takes any gear Link owns at either age (checked live: child Link with the
 * Master Sword, Biggoron's Sword, the broken knife), as the community mod Hyrule Armory Sync (a drawer on L) allows.
 * This one has no drawer: the change is applied at once. ---- */
#define GD_S64_WEAPON 23u   /* PlayerStatus.EquipWeapon (core/gd_index.h GD_S64_EQUIP_WEAPON) */
#define GD_S64_SHIELD 22u   /* PlayerStatus.EquipShield (core/gd_index.h GD_S64_EQUIP_SHIELD) */
static const char ARM_SWORDS[5][28] = {"Weapon_Sword_Kokiri", "Weapon_Sword_Master", "Weapon_Sword_Giant",
                                       "Weapon_Sword_Biggoron", "Weapon_Sword_BrokenGiant"};
static const char ARM_SHIELDS[3][24] = {"Weapon_Shield_Deku", "Weapon_Shield_Hylian", "Weapon_Shield_Mirror"};
/* who can use each one: child Link the Kokiri Sword, the Deku and the Hylian Shield; adult Link everything else and
 * the Hylian Shield (bit 1 child, bit 2 adult) */
#define AGE_CHILD 1u
#define AGE_ADULT 2u
static const unsigned char ARM_SWORD_AGE[5] = {AGE_CHILD, AGE_ADULT, AGE_ADULT, AGE_ADULT, AGE_ADULT};
static const unsigned char ARM_SHIELD_AGE[3] = {AGE_CHILD, AGE_CHILD | AGE_ADULT, AGE_ADULT};
int hud_is_child(void);         /* core/hud.c: 1 / 0, -1 = no GameData */
#define ARM_STICK 16000        /* stick deflection that counts as a direction (of +-32767) */
int hud_pouch_has(const char *actor);   /* core/hud.c: PouchData.<actor>.StockNum > 0 (1 / 0, -1 unknown) */
/* Link has this sword / shield: in the pouch (what the pause menu lists), or its IsGet flag */
static int gear_owned(const char *nm) { return hud_pouch_has(nm) > 0 || hud_owns_name(nm); }
int hud_game_covered(void);     /* core/hud.c: a menu covers the game */
int player_active(void);
int player_state_is(const char *name);
int player_state_starts(const char *prefix);
u32 g_arm_dbg[4];              /* diagnostic: steps taken, equips done, last list index, refused (Link busy) */
char g_arm_last[64];           /* diagnostic: the last name equipped */
static u32 g_arm_dir;          /* direction held in the previous read (1 left, 2 right, 3 up, 4 down) */

/* ---- the quick menu (drawn by core/hud.c from these globals) ----
 * Holding the armory button opens it: a row of the swords and a row of the shields Link owns, the cursor on what he
 * wears. Left / right moves in the row, up / down changes the row; letting the button go equips the one under the
 * cursor (nothing when it did not move). Under a menu (pause ...) it closes without a change. */
extern u32 g_arm_open;                  /* core/hud.c: the menu is up */
extern int g_arm_row, g_arm_col;        /* core/hud.c: the cursor (row 0 swords, 1 shields) */
extern char g_arm_names[2][5][28];      /* core/hud.c: the gear Link owns, per row */
extern u32 g_arm_n[2];                  /* core/hud.c: how many per row */
static int g_arm_last_row;              /* the menu opens on the row used last */
static char g_arm_pending[28];          /* chosen while Link was busy: equipped as soon as he is free */

static int arm_free(void) {
    return player_state_is("Wait") || player_state_is("Move") || player_state_starts("LockOn");
}
/* the gear of a row Link owns and can use at his age, and where the one he wears is in it (-1 none) */
static int arm_fill(u32 row) {
    const char *list = row ? (const char *)ARM_SHIELDS : (const char *)ARM_SWORDS;
    const unsigned char *age = row ? ARM_SHIELD_AGE : ARM_SWORD_AGE;
    u32 n = row ? 3u : 5u, stride = row ? 24u : 28u, k = 0;
    int ch = hud_is_child();
    u32 bit = ch > 0 ? AGE_CHILD : AGE_ADULT;   /* (no GameData: the adult set) */
    char cur[64];
    gd_get_string(row ? GD_S64_SHIELD : GD_S64_WEAPON, cur, sizeof cur);
    int on = -1;
    for (u32 i = 0; i < n; i++) {
        const char *nm = list + i * stride;
        if (!(age[i] & bit) || !gear_owned(nm)) continue;
        if (same(cur, nm)) on = (int)k;
        u32 j = 0;
        for (; j < 27u && nm[j]; j++) g_arm_names[row][k][j] = nm[j];
        g_arm_names[row][k][j] = 0;
        k++;
    }
    g_arm_n[row] = k;
    return on;
}
static void arm_equip(const char *nm) {
    char cur[64];
    gd_get_string(nm[7] == 'S' && nm[8] == 'h' ? GD_S64_SHIELD : GD_S64_WEAPON, cur, sizeof cur);   /* Weapon_Sh.. */
    if (same(cur, nm)) return;
    /* Only the game's request: it compares the name with what Link wears and does nothing when they are equal, so
     * the String64 record must not be written first (the game writes it itself when the change goes through). */
    apply_equip(nm);
    copy64(g_arm_last, nm);
    g_arm_dbg[1]++;
}

static void armory_input(const HidView *view, u64 buttons) {
    u32 held = (buttons & VBTN_ARMORY) != 0;
    for (u32 i = 0; i < view->count; i++) {   /* the game never sees the role's own bit */
        u64 b = hid_get_buttons(view, i);
        if (b & VBTN_ARMORY) hid_set_buttons(view, i, b & ~VBTN_ARMORY);
    }
    int playing = !hud_game_covered() && player_active();
    if (g_arm_pending[0] && playing && arm_free()) { arm_equip(g_arm_pending); g_arm_pending[0] = 0; }
    if (!playing) {                           /* a menu came up: close without a change */
        g_arm_open = 0; g_arm_dir = 0;
        return;
    }
    if (!held) {
        if (g_arm_open) {                     /* released: equip the one under the cursor */
            g_arm_open = 0;
            g_arm_last_row = g_arm_row;
            if ((u32)g_arm_col < g_arm_n[g_arm_row]) {
                const char *nm = g_arm_names[g_arm_row][g_arm_col];
                if (arm_free()) arm_equip(nm);
                else { copy64(g_arm_pending, nm); g_arm_dbg[3]++; }
            }
        }
        g_arm_dir = 0;
        return;
    }
    if (!g_arm_open) {                        /* just pressed: open on the last row, cursor on what he wears */
        int on0 = arm_fill(0), on1 = arm_fill(1);
        g_arm_row = g_arm_n[g_arm_last_row] ? g_arm_last_row : (g_arm_n[0] ? 0 : 1);
        int on = g_arm_row ? on1 : on0;
        g_arm_col = on >= 0 ? on : 0;
        g_arm_open = 1;
        g_arm_dir = 0;
    }
    /* the direction: D-pad first, else the left stick (s32 x / y at sample + 0x10) */
    const volatile int *st = (const volatile int *)((unsigned char *)view->samples + 0x10);
    int x = st[0], y = st[1];
    u32 dir = (buttons & DPAD_LEFT) ? 1u : (buttons & DPAD_RIGHT) ? 2u : (buttons & DPAD_UP) ? 3u :
              (buttons & DPAD_DOWN) ? 4u : x < -ARM_STICK ? 1u : x > ARM_STICK ? 2u : y > ARM_STICK ? 3u :
              y < -ARM_STICK ? 4u : 0u;
    /* Link stays where he is while the menu is up: no D-pad, no left stick */
    for (u32 i = 0; i < view->count; i++) {
        u64 b = hid_get_buttons(view, i);
        hid_set_buttons(view, i, b & ~(DPAD_LEFT | DPAD_RIGHT | DPAD_UP | DPAD_DOWN));
        volatile int *p = (volatile int *)((unsigned char *)view->samples + (u64)i * HID_STRIDE + 0x10);
        p[0] = 0; p[1] = 0;
    }
    if (dir && dir != g_arm_dir) {           /* one step per push */
        g_arm_dbg[0]++;
        int n = (int)g_arm_n[g_arm_row];
        if (dir == 1u && n) g_arm_col = (g_arm_col + n - 1) % n;
        else if (dir == 2u && n) g_arm_col = (g_arm_col + 1) % n;
        else if ((dir == 3u || dir == 4u)) {
            int row = dir == 3u ? 0 : 1;   /* (an empty row is skipped) */
            if (row != g_arm_row && g_arm_n[row]) {
                g_arm_row = row;
                g_arm_col = g_arm_col < (int)g_arm_n[row] ? g_arm_col : (int)g_arm_n[row] - 1;
            }
        }
        g_arm_dbg[2] = (u32)(g_arm_row * 8 + g_arm_col);
    }
    g_arm_dir = dir;
}

void quick_select_on_input(u32 site, void *a0, void *a1, void *a2, u32 stock_result) {
    (void)a2;
    if (site != 3 || !a0) return;
    u32 count = (u32)(unsigned long)a1;
    if (count == 0 || count > 64) count = stock_result;
    if (count == 0 || count > 64) return;
    HidView view = {a0, count, 0};
    u64 buttons = hid_merge_buttons(&view);
    if (remap_on()) {
        armory_input(&view, buttons);
        if (buttons & VBTN_ARMORY) return;   /* the armory owns the D-pad while held */
    }
    if (!g_shbcfg.quick_boots && !g_shbcfg.quick_mask) return;

    u32 now = hud_frame_count();
    u32 new_frame = (now != g_last_frame);
    if (new_frame) g_last_frame = now;

    u64 held = 0;
    if (g_shbcfg.quick_boots && (buttons & DPAD_DOWN) && !(buttons & DPAD_UP)) held = DPAD_DOWN;
    else if (g_shbcfg.quick_mask && (buttons & DPAD_UP)) held = DPAD_UP;

    if (!held) {
        g_hold = 0;
        g_hold_btn = 0;
        if (g_latch && ++g_release >= 5u) { g_latch = 0; g_release = 0; }
        return;
    }
    g_release = 0;
    if (g_hold_btn != held) {
        g_hold = 0;
        g_hold_btn = held;
        g_latch = 0;
    }
    if (new_frame && !g_latch) g_hold++;
    if (g_hold >= HOLD_FRAMES && !g_latch) {
        u32 kind = held == DPAD_DOWN ? 1u : 2u;
        if (kind == 1u) toggle_boots();
        else toggle_mask();
        g_latch = 1;
        g_hold = 0;
    }
}
