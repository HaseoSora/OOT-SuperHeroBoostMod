/* Quick select (beta): hold D-pad Down/Up to switch the boots / mask without the pause menu.
 *
 * The equipment slots are GameData strings, the same ones the pause menu writes:
 *   PlayerStatus.EquipBoot      (String64 index 18 of the type)
 *   PlayerStatus.EquipHeadArmor (String64 index 20)
 * Record layout (gdlive): table = mgr + 8 + 0x60*16, +0x08 count, +0x10 records;
 * record stride 0x108, live string at +0x74 (64 bytes). Writing it applies at once.
 *
 * An empty boot string is the Kokiri Boots (the default, no HUD icon); an empty mask is "none".
 * Holding the D-pad button for HOLD_FRAMES switches to the next option once; release and hold
 * again for the next one.
 */
#include "../../core/dispatch.h"
#include "../../core/config.h"
#include "../../core/hid.h"

#define DPAD_LEFT  0x1000ull
#define DPAD_UP    0x2000ull
#define DPAD_RIGHT 0x4000ull
#define DPAD_DOWN  0x8000ull

#define HOLD_FRAMES 18u

typedef struct {
    const char *label;
    const char *value;
} Pick;

static const Pick g_boots[] = {
    {"KOKIRI", ""},
    {"HIERRO", "Armor_Adult_HeavyBoot"},
    {"HOVER", "Armor_Adult_HoverBoot"},
};
static const Pick g_masks[] = {
    {"NINGUNA", ""},
    {"KEATON", "Armor_Child_Mask_Keaton"},
    {"SKULL", "Armor_Child_Mask_Skull"},
    {"SPOOKY", "Armor_Child_Mask_Spooky"},
    {"BUNNY", "Armor_Child_Mask_Bunny"},
    {"VERDAD", "Armor_Child_Mask_Truth"},
    {"GORON", "Armor_Child_Mask_Goron"},
    {"ZORA", "Armor_Child_Mask_Zora"},
    {"GERUDO", "Armor_Child_Mask_Gerudo"},
};

extern char GAMEDATA_MGR[];   /* link.ld: main+0x4E842A8 */
u32 hud_frame_count(void);

static u32 g_hold;
static u32 g_latch;        /* a switch was made: wait for the button release */
static u32 g_release;      /* consecutive calls without the button (the same frame may call us several times) */
static u64 g_hold_btn;
static u32 g_last_frame;
u32 g_qs_dbg[8] = {0x10000000u, 0, 0, 0, 0, 0, 0, 0};   /* calls, max hold, switches, cur, ok, next, kind, buttons */
char g_qs_cur[64];

static u32 option_count(u32 kind) {
    return kind == 1u ? (u32)(sizeof(g_boots) / sizeof(g_boots[0]))
                      : (u32)(sizeof(g_masks) / sizeof(g_masks[0]));
}

static void gd_set_string(u32 index, const char *name) {
    u64 mgr = *(volatile u64 *)GAMEDATA_MGR;
    if (!mgr) return;
    u64 table = mgr + 8ull + 0x60ull * 16ull;      /* String64 */
    u32 count = *(volatile u32 *)(table + 8);
    u64 recs = *(volatile u64 *)(table + 0x10);
    if (!recs || index >= count) return;
    unsigned char *rec = (unsigned char *)(recs + (u64)index * 0x108ull);
    u64 ptr = *(volatile u64 *)(rec + 0x68);
    unsigned char *val = ptr ? (unsigned char *)ptr : rec + 0x74;
    u32 n = 0;
    while (name[n] && n < 63u) { val[n] = (unsigned char)name[n]; n++; }
    val[n] = 0;
    for (u32 i = n + 1u; i < 64u; i++) val[i] = 0;
    if (ptr) {   /* keep the record's inline buffer in step as well */
        for (u32 i = 0; i <= n; i++) rec[0x74 + i] = val[i];
        for (u32 i = n + 1u; i < 64u; i++) rec[0x74 + i] = 0;
    }
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

static u32 current_option(u32 kind) {
    const Pick *list = kind == 1u ? g_boots : g_masks;
    u32 n = option_count(kind);
    char cur[64];
    gd_get_string(kind == 1u ? 18u : 20u, cur, sizeof cur);
    for (u32 i = 0; i < 63; i++) { g_qs_cur[i] = cur[i]; if (!cur[i]) break; }
    g_qs_cur[63] = 0;
    for (u32 i = 0; i < n; i++) {
        const char *v = list[i].value;
        u32 k = 0;
        while (v[k] && v[k] == cur[k]) k++;
        if (!v[k] && !cur[k]) return i;
    }
    return 0;
}

static void equip(u32 kind, u32 sel) {
    if (kind == 1u) gd_set_string(18u, g_boots[sel].value);
    else if (kind == 2u) gd_set_string(20u, g_masks[sel].value);
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
        u32 cur = current_option(kind);
        u32 next = (cur + 1u) % option_count(kind);
        equip(kind, next);
        g_qs_dbg[2]++; g_qs_dbg[3] = cur; g_qs_dbg[4] = 1; g_qs_dbg[5] = next; g_qs_dbg[6] = kind;
        g_latch = 1;
        g_hold = 0;
    }
}
