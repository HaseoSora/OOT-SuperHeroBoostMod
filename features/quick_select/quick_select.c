/* Quick select (beta): hold D-pad Down / Up to toggle equipment without the pause menu.
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

#define DPAD_LEFT  0x1000ull
#define DPAD_UP    0x2000ull
#define DPAD_RIGHT 0x4000ull
#define DPAD_DOWN  0x8000ull

#define HOLD_FRAMES 18u

#define NAME_HEAVY "Armor_Adult_HeavyBoot"
#define NAME_HOVER "Armor_Adult_HoverBoot"
#define NAME_LENS  "Armor_GlassTruth"

extern char GAMEDATA_MGR[];       /* link.ld: main+0x4E842A8 */
u32 hud_frame_count(void);
int hud_owns_name(const char *actor);   /* core/hud.c: IsGet.<actor> from the live Bool table */

static u32 g_hold;
static u32 g_latch;        /* a switch was made: wait for the button release */
static u32 g_release;      /* consecutive calls without the button (the same frame may call us several times) */
static u64 g_hold_btn;
static u32 g_last_frame;
u32 g_qs_dbg[8] = {0x10000000u, 0, 0, 0, 0, 0, 0, 0};   /* calls, max hold, switches, cur, ok, what, kind, buttons */
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

/* Down: iron <-> hover boots. Returns 1 when the string was changed. */
static u32 toggle_boots(void) {
    char cur[64];
    gd_get_string(18u, cur, sizeof cur);
    copy64(g_qs_cur, cur);
    if (same(cur, NAME_HEAVY)) {
        if (!hud_owns_name(NAME_HOVER)) return 0;
        gd_set_string(18u, NAME_HOVER);
    } else if (same(cur, NAME_HOVER)) {
        if (!hud_owns_name(NAME_HEAVY)) return 0;
        gd_set_string(18u, NAME_HEAVY);
    } else {                                      /* default (Kokiri) boots: go to iron, else hover */
        if (hud_owns_name(NAME_HEAVY)) gd_set_string(18u, NAME_HEAVY);
        else if (hud_owns_name(NAME_HOVER)) gd_set_string(18u, NAME_HOVER);
        else return 0;
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
        return 1;
    }
    if (!hud_owns_name(NAME_LENS)) return 0;
    if (cur[0]) copy64(g_mask_last, cur);         /* remember the mask we are wearing */
    gd_set_string(20u, NAME_LENS);
    return 1;
}

/* No selector text: the HUD clock keeps showing the time. */
int quick_select_text(char *b, u32 cap) {
    (void)b; (void)cap;
    return 0;
}

void quick_select_on_input(u32 site, void *a0, void *a1, void *a2, u32 stock_result) {
    (void)a2;
    if (!g_shbcfg.quick_boots && !g_shbcfg.quick_mask) return;
    if (site != 3 || !a0) return;
    u32 count = (u32)(unsigned long)a1;
    if (count == 0 || count > 64) count = stock_result;
    if (count == 0 || count > 64) return;
    HidView view = {a0, count, 0};
    u64 buttons = hid_merge_buttons(&view);
    g_qs_dbg[0]++;
    g_qs_dbg[7] = (u32)buttons;

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
    if (g_hold > g_qs_dbg[1]) g_qs_dbg[1] = g_hold;
    if (g_hold >= HOLD_FRAMES && !g_latch) {
        u32 kind = held == DPAD_DOWN ? 1u : 2u;
        u32 ok = kind == 1u ? toggle_boots() : toggle_mask();
        if (ok) g_qs_dbg[2]++;
        g_qs_dbg[3] = kind; g_qs_dbg[4] = ok; g_qs_dbg[5] = kind == 1u ? 1u : 2u; g_qs_dbg[6] = kind;
        g_latch = 1;
        g_hold = 0;
    }
}
