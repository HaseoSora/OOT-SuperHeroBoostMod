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
int hud_pouch_has(const char *actor);    /* core/hud.c: StockNum.<actor> from the live pouch */

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

/* When the Lens was equipped outside the quick select there may be no saved mask yet:
 * use the first child mask Link owns. */
static const char *first_owned_mask(void) {
    /* chars, not pointers: a table of pointers would be a pointer in module data, which the module
     * cannot relocate (Rekarina loads it away from its link address and the value arrives truncated) */
    static const char names[8][26] = {
        "Armor_Child_Mask_Keaton", "Armor_Child_Mask_Skull", "Armor_Child_Mask_Spooky",
        "Armor_Child_Mask_Bunny", "Armor_Child_Mask_Goron", "Armor_Child_Mask_Zora",
        "Armor_Child_Mask_Gerudo", "Armor_Child_Mask_Truth",
    };
    for (u32 i = 0; i < sizeof(names) / sizeof(names[0]); i++) {
        if (hud_owns_name(names[i]) || hud_pouch_has(names[i]) == 1) return names[i];
    }
    return 0;
}

/* Up: the Lens of Truth <-> the mask Link wears. Returns 1 when the string was changed. */
static u32 toggle_mask(void) {
    char cur[64];
    gd_get_string(20u, cur, sizeof cur);
    copy64(g_qs_cur, cur);
    if (same(cur, NAME_LENS)) {
        if (!g_mask_last[0]) {
            const char *m = first_owned_mask();
            if (m) copy64(g_mask_last, m);
        }
        if (!g_mask_last[0]) return 0;
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

/* ---- Armory: the button with the armory role (button remap) opens the game's own item drawer, listing Link's swords
 * and shields (features/quick_select/armory_drawer.c). While it is held the game sees R held, as when the item
 * drawer is opened: it pops up, the stick chooses, letting the button go confirms. It starts only while Link is in
 * the game with no menu up; once started it holds R until the button is let go. ---- */
int hud_game_covered(void);     /* core/hud.c: a menu covers the game */
int player_active(void);
int hud_ingame(void);
extern u32 g_arm_held;          /* armory_drawer.c: the drawer lists gear while this is set */
static u32 g_arm_drawer_hold;   /* we hold R for the game */

static void armory_input(const HidView *view, u64 buttons) {
    u32 held = (buttons & VBTN_ARMORY) != 0;
    for (u32 i = 0; i < view->count; i++) {   /* the game never sees the role's own bit */
        u64 b = hid_get_buttons(view, i);
        if (b & VBTN_ARMORY) hid_set_buttons(view, i, b & ~VBTN_ARMORY);
    }
    if (!held) { g_arm_drawer_hold = 0; g_arm_held = 0; return; }
    if (!g_arm_drawer_hold && !hud_game_covered() && hud_ingame() && player_active() && !(buttons & BTN_R))
        g_arm_drawer_hold = 1;
    if (!g_arm_drawer_hold) return;
    g_arm_held = 1;
    for (u32 i = 0; i < view->count; i++) hid_set_buttons(view, i, hid_get_buttons(view, i) | BTN_R);
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
        if (buttons & VBTN_ARMORY) return;   /* (no quick boots / mask while the armory drawer is up) */
    }
    if (!g_shbcfg.quick_boots && !g_shbcfg.quick_mask) return;
    if (g_shbcfg.quick_mask) {
        char head[64];
        gd_get_string(20u, head, sizeof head);
        if (head[0] && !same(head, NAME_LENS)) copy64(g_mask_last, head);
    }

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
