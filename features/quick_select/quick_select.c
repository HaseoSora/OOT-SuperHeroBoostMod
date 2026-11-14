/* Quick select (beta): hold D-pad Down/Up to pick boots / mask without the pause menu.
 *
 * The equipment slots are GameData strings, the same ones the pause menu writes:
 *   PlayerStatus.EquipBoot      (String64 index 18 of the type)
 *   PlayerStatus.EquipHeadArmor (String64 index 20)
 * Record layout (gdlive): table = mgr + 8 + 0x60*16, +0x08 count, +0x10 records;
 * record stride 0x108, live string at +0x74 (64 bytes). Writing it applies at once.
 */
#include "../../core/dispatch.h"
#include "../../core/config.h"
#include "../../core/hid.h"

#define DPAD_LEFT  0x1000ull
#define DPAD_UP    0x2000ull
#define DPAD_RIGHT 0x4000ull
#define DPAD_DOWN  0x8000ull
#define DPAD_ALL   (DPAD_LEFT | DPAD_UP | DPAD_RIGHT | DPAD_DOWN)

#define HOLD_FRAMES 18u

typedef struct {
    const char *label;
    const char *value;
} Pick;

static const Pick g_boots[] = {
    {"NINGUNA", ""},
    {"KOKIRI", "Item_NormalBoot"},
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

static u32 g_kind;        /* 0 closed, 1 boots, 2 mask */
static u32 g_sel;
static u32 g_hold;
static u64 g_hold_btn;
static u64 g_prev;
static u32 g_last_frame;

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
    unsigned char *val = (unsigned char *)(recs + (u64)index * 0x108ull + 0x74ull);
    u32 n = 0;
    while (name[n] && n < 63u) { val[n] = (unsigned char)name[n]; n++; }
    val[n] = 0;
    for (u32 i = n + 1u; i < 64u; i++) val[i] = 0;
}

static void equip(u32 kind, u32 sel) {
    if (kind == 1u) gd_set_string(18u, g_boots[sel].value);
    else if (kind == 2u) gd_set_string(20u, g_masks[sel].value);
}

static void suppress_dpad(const HidView *v) {
    for (u32 i = 0; i < v->count; i++) {
        u64 b = hid_get_buttons(v, i);
        hid_set_buttons(v, i, b & ~DPAD_ALL);
    }
}

/* HUD clock plate text while the selector is open. */
int quick_select_text(char *b, u32 cap) {
    (void)cap;
    if (g_kind == 0) return 0;
    const Pick *p = (g_kind == 1u ? g_boots : g_masks) + g_sel;
    u32 n = 0;
    const char *pre = g_kind == 1u ? "BOTAS " : "MASC ";
    while (*pre && n < 14u) b[n++] = *pre++;
    const char *lab = p->label;
    while (*lab && n < 14u) b[n++] = *lab++;
    b[n] = 0;
    return 1;
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

    u32 now = hud_frame_count();
    u64 pressed = 0;
    u32 new_frame = (now != g_last_frame);
    if (new_frame) {
        pressed = buttons & ~g_prev;
        g_prev = buttons;
        g_last_frame = now;
    }

    if (g_kind == 0) {
        if ((buttons & DPAD_DOWN) && g_shbcfg.quick_boots && !(buttons & DPAD_UP)) {
            if (g_hold_btn != DPAD_DOWN) g_hold = 0;
            g_hold_btn = DPAD_DOWN;
            if (new_frame) g_hold++;
        } else if ((buttons & DPAD_UP) && g_shbcfg.quick_mask) {
            if (g_hold_btn != DPAD_UP) g_hold = 0;
            g_hold_btn = DPAD_UP;
            if (new_frame) g_hold++;
        } else {
            g_hold = 0;
            g_hold_btn = 0;
        }
        if (g_hold >= HOLD_FRAMES) {
            g_kind = g_hold_btn == DPAD_DOWN ? 1u : 2u;
            g_sel = 0;
            suppress_dpad(&view);
        }
        return;
    }

    /* open: navigate with Left/Right, equip when the held button is released */
    if (pressed & DPAD_LEFT) g_sel = (g_sel + option_count(g_kind) - 1u) % option_count(g_kind);
    if (pressed & DPAD_RIGHT) g_sel = (g_sel + 1u) % option_count(g_kind);
    if (!(buttons & g_hold_btn)) {
        equip(g_kind, g_sel);
        g_kind = 0;
        g_hold = 0;
        return;
    }
    suppress_dpad(&view);
}
