/* Armory drawer: the game's own item drawer (the one R opens), listing Link's swords and shields instead of items.
 *
 * Holding the armory button (button remap) holds R for the game, so it opens its drawer exactly as for items: the
 * same window, blur and slowed game, the stick to choose, release to confirm. While the armory button opened it:
 *   - the list is built from the equipment container (category 1) instead of the items' (category 0), keeping only
 *     the swords and shields Link owns and can use at his age (child: Kokiri Sword, Deku and Hylian Shield; adult:
 *     every other, the Hylian Shield too);
 *   - each cell shows the gear's icon (the item cell code does not know them);
 *   - the cells form two rows, the swords above and the shields below; the stick moves in a row (left / right) or
 *     between the rows (up / down); the gear Link wears has the darker frame. The game's cursor stays in the middle
 *     (its list scrolls under it), so the grid moves to put the selected cell there, the others at 0.7 scale so
 *     both rows fit in the drawer's clip;
 *   - the item name goes 80 lower, under the two rows (the sort header "By type / Sort" stays: its panes are not
 *     found by name once the drawer is built, so the attempts to hide it below change nothing);
 *   - the cursor opens on the gear chosen last (else on the first of the row used last);
 *   - on release, the gear under the cursor is equipped through the game's equip request (the pause menu's path),
 *     only when the player moved the cursor: a plain press and release changes nothing.
 * The sites are calls in the drawer and list-build code, replaced by the wrappers in armory.S. Without the armory
 * button every wrapper calls the stock function unchanged. */
#include "../../core/dispatch.h"
#include "../../core/config.h"
#include "../../core/remap.h"

typedef struct {
    u64 x29, x30;
    u64 x[9];      /* x0..x8 as the site passed them (the function gets these back) */
    u64 x19, x20;  /* the caller's (read only) */
    u64 fn;        /* the function to call; 0 skips it */
    double d[4];
    u64 ret;       /* x0 returned to the site */
    u64 x22;       /* the caller's (read only) */
} BlCtx;

extern char AD_CONT_EQUIP[], AD_OWNED[], AD_PANE_SCALE[], AD_PANE_MOVE[], AD_PANE_SHOW[], AD_RET_MOVE[];
extern char AD_SORT_SHOW[], AD_CELL_AT[], AD_CURSOR_MOVE[], AD_CURSOR_SET[], AD_FIND_PANE[], AD_STICK_SLOT[], AD_EQUIP_OBJ[],
    AD_GD_READY[], AD_GD_STRING[];
extern void equip_request(void *pouch, void *name_ref, u32 kind, u32 arg3);
extern void equip_refresh(void *pouch, void *name_ref, u32 one);
extern void tex_replace(void *replacer, const char **name, u32 flag);

typedef int (*OwnedFn)(u64, u64, u32, u32);
typedef void (*ScaleFn)(void *, float, float);
typedef void (*MoveFn)(void *, float, float, float);
typedef void (*ShowFn)(void *, u32);
typedef u64 (*CellAtFn)(u64, u32);
typedef void (*CursorMoveFn)(u64, u32, u32);
typedef void (*CursorSetFn)(u64, u32);
typedef u64 (*FindPaneFn)(u64, const char *);
typedef u32 (*GdReadyFn)(u64, void *, u32);
typedef u32 (*GdStringFn)(u64, const char **, void *, u32);

/* the gear and who can use it (bit 0 child, bit 1 adult) */
#define AD_N 8
static const char AD_NAME[AD_N][28] = {
    "Weapon_Sword_Kokiri", "Weapon_Sword_Master", "Weapon_Sword_Giant", "Weapon_Sword_Biggoron",
    "Weapon_Sword_BrokenGiant", "Weapon_Shield_Deku", "Weapon_Shield_Hylian", "Weapon_Shield_Mirror"};
static const unsigned char AD_AGE[AD_N] = {1, 2, 2, 2, 2, 1, 3, 2};

u32 g_arm_held;           /* quick_select.c: the armory button holds the drawer open */
u32 g_ad_on;              /* the list being shown was built for the armory */
static unsigned char g_ad_map[AD_N];   /* list position -> gear index + 1 (0: none) */
static u64 g_ad_drawer;   /* the drawer object showing the armory list */
static u32 g_ad_moved;    /* the cursor moved since it opened */
static u32 g_ad_dirty;    /* a cell's icon pane was resized for gear: item lists put it back */
static u32 g_ad_n;        /* cells in the list built */
static u64 g_ad_cells;    /* the drawer's cell list (cell positions are ours while it shows the armory) */
static u32 g_ad_started;  /* the open's first armory frame was done (cursor placed, header hidden) */
static u32 g_ad_dir;      /* stick direction in the previous frame */
static u32 g_ad_worn;     /* gear Link wears (bit per gear index) */
static int g_ad_pick = -1;   /* gear chosen last (the cursor reopens on it) */
static u32 g_ad_row;      /* row used last */
static u64 g_ad_sortlay;  /* the layout holding the sort window */
static u64 g_ad_sortctl;  /* the sort window's controller (the game opens / closes it with AD_SORT_SHOW) */
typedef void (*SortShowFn)(u64, u32);
static u64 g_ad_hid_lay;  /* the drawer layout whose header we hid (0: none) */
static u64 g_ad_hid_pane[3];
static u32 g_ad_hid_val[3];
u64 g_ad_pp[8];           /* diagnostic: panes found (4: text, 5 sort window, 6 guide, 7 sort layout) */
u32 g_ad_pos_n;
static u32 g_ad_scaled;   /* cells were scaled for the grid: item lists put them back */           /* diagnostic: cell placements */
u32 g_ad_dbg[6];          /* diagnostic: lists built, entries kept, opens, moves, equips, blocked decides */
char g_ad_last[32];       /* diagnostic: the last gear equipped */

static int ptr_ok(u64 p) { return p >= 0x10000ull && !(p & 7ull); }

static int gear_index(const char *nm) {
    if (!nm || !ptr_ok((u64)nm & ~7ull)) return -1;
    for (int i = 0; i < AD_N; i++) {
        const char *a = AD_NAME[i];
        u32 j = 0;
        while (a[j] && a[j] == nm[j]) j++;
        if (!a[j] && !nm[j]) return i;
    }
    return -1;
}

/* the icon pane of a drawer cell (a picture part, type 0x17), or 0 */
static u64 cell_icon_pane(u64 cell) {
    u64 part = *(volatile u64 *)(cell + 0x20);
    if (!ptr_ok(part)) return 0;
    u64 pane = *(volatile u64 *)(part + 0x80);
    if (!ptr_ok(pane) || *(volatile unsigned short *)(pane + 0x13c) != 0x17) return 0;
    u64 p = *(volatile u64 *)(pane + 0x100);
    return ptr_ok(p) ? p : 0;
}

/* gear icons are drawn larger than items: the cell's icon a little smaller and centred, as the pause menu shows them */
static void cell_fit(u64 cell, u32 gear) {
    u64 p = cell_icon_pane(cell);
    if (!p) return;
    ((ShowFn)AD_PANE_SHOW)((void *)(p + 0xd10), 1);
    ((ScaleFn)AD_PANE_SCALE)((void *)(p + 0xd10), gear ? 0.6243f : 1.0f, gear ? 0.6243f : 1.0f);
    ((MoveFn)AD_PANE_MOVE)((void *)(p + 0xd10), gear ? 6.5143f : 0.0f, gear ? -5.4286f : 0.0f, 0.0f);
}

static void equip_at_cursor(u64 drawer, u64 pouch) {
    u64 cur = *(volatile u64 *)(drawer + 0x68);
    if (!ptr_ok(cur) || !ptr_ok(pouch)) return;
    u32 pos = *(volatile u32 *)(cur + 0x4c);
    if (pos >= AD_N || !g_ad_map[pos]) return;
    const char *nm = AD_NAME[g_ad_map[pos] - 1];
    static const char *ref[2];
    ref[0] = nm; ref[1] = (const char *)64ull;
    equip_request((void *)pouch, ref, 3u, 0u);
    equip_refresh((void *)pouch, ref, 1u);
    u32 i = 0;
    for (; i < 31u && nm[i]; i++) g_ad_last[i] = nm[i];
    g_ad_last[i] = 0;
    g_ad_dbg[4]++;
}

/* ---- the grid: row 0 the swords, row 1 the shields, each row centred ---- */
static int cell_row(u32 pos) { return g_ad_map[pos] > 5; }   /* gear index >= 5: a shield */
/* column of a cell in its row, and how many its row has */
static void cell_col(u32 pos, int *col, int *cnt) {
    int r = cell_row(pos);
    *col = 0; *cnt = 0;
    for (u32 i = 0; i < g_ad_n; i++) {
        if (!g_ad_map[i] || cell_row(i) != r) continue;
        if (i < pos) (*col)++;
        (*cnt)++;
    }
}
static void cell_xy(u32 pos, float *x, float *y) {
    int col, cnt;
    cell_col(pos, &col, &cnt);
    *x = (float)(col * 300 - (cnt - 1) * 150);
    *y = cell_row(pos) ? -280.0f : 0.0f;
}
/* the cell a stick push leads to (dir 1 left, 2 right, 3 up, 4 down) */
static u32 cell_step(u32 pos, u32 dir) {
    int col, cnt, r = cell_row(pos);
    cell_col(pos, &col, &cnt);
    if (dir == 1 || dir == 2) {
        col += dir == 1 ? -1 : 1;
        if (col < 0 || col >= cnt) return pos;
    } else {
        int want = dir == 3 ? 0 : 1;
        if (want == r) return pos;
        r = want;
    }
    u32 hit = pos;
    int k = 0;
    for (u32 i = 0; i < g_ad_n; i++) {   /* the col-th of row r, or its last */
        if (!g_ad_map[i] || cell_row(i) != r) continue;
        hit = i;
        if (k++ == col) break;
    }
    return hit;
}
static u32 stick_dir(float x, float y) {
    float ax = x < 0 ? -x : x, ay = y < 0 ? -y : y;
    if (ax >= ay) return ax >= 0.5f ? (x >= 0 ? 2u : 1u) : 0u;
    return ay >= 0.5f ? (y < 0 ? 4u : 3u) : 0u;
}

extern void *find_part(void *node, const char *name);   /* core/link.ld: the game's part lookup by name */
/* a pane / part by name: the game's part lookup, else the nested-part one */
static u64 ui_get(u64 lay, const char *name) {
    if (!ptr_ok(lay)) return 0;
    u64 p = (u64)find_part((void *)lay, name);
    if (!ptr_ok(p)) p = ((FindPaneFn)AD_FIND_PANE)(lay, name);
    return ptr_ok(p) ? p : 0;
}
/* hide (or put back) the sort header and its guide; the name text goes 80 lower, under the two rows */
static void header_show(u64 lay, u32 hide) {
    if (!hide && g_ad_hid_lay != lay) return;
    if (hide && ptr_ok(g_ad_sortctl)) ((SortShowFn)AD_SORT_SHOW)(g_ad_sortctl, 0);   /* "By type / Sort" closed */
    if (hide) {   /* (again at each open: the game shows its header when the drawer opens) */
        u32 again = g_ad_hid_lay == lay;
        g_ad_hid_lay = lay;
        u64 t = ui_get(lay, "T_Text_00");
        g_ad_pp[4] = t;
        if (!again) {
            g_ad_hid_pane[0] = ptr_ok(t) ? t : 0;
            if (g_ad_hid_pane[0]) g_ad_hid_val[0] = *(volatile u32 *)(t + 0x70);
        }
        if (g_ad_hid_pane[0]) {
            union { u32 u; float f; } y0 = {g_ad_hid_val[0]};
            ((MoveFn)AD_PANE_MOVE)((void *)g_ad_hid_pane[0], *(volatile float *)(g_ad_hid_pane[0] + 0x6c), y0.f - 80.0f,
                                   *(volatile float *)(g_ad_hid_pane[0] + 0x74));
        }
        static const char *const PART[2] = {"Pa_SortWindow_00", "Pa_Guide_00"};
        for (int i = 0; i < 2; i++) {
            u64 q = ui_get(lay, PART[i]);
            if (!q) q = ui_get(g_ad_sortlay, PART[i]);
            g_ad_pp[5 + i] = q; g_ad_pp[7] = g_ad_sortlay;
            if (!ptr_ok(q)) continue;
            if (!again || !g_ad_hid_pane[i + 1]) { g_ad_hid_pane[i + 1] = q; g_ad_hid_val[i + 1] = *(volatile u32 *)(q + 0xa8) & 1u; }
            ((ShowFn)AD_PANE_SHOW)((void *)q, 0);
        }
    } else {
        g_ad_hid_lay = 0;
        u64 t = g_ad_hid_pane[0];
        if (t) {
            union { u32 u; float f; } y = {g_ad_hid_val[0]};
            ((MoveFn)AD_PANE_MOVE)((void *)t, *(volatile float *)(t + 0x6c), y.f, *(volatile float *)(t + 0x74));
        }
        for (int i = 1; i < 3; i++)
            if (g_ad_hid_pane[i]) ((ShowFn)AD_PANE_SHOW)((void *)g_ad_hid_pane[i], g_ad_hid_val[i]);
    }
}
/* the sword and shield Link wears, as gear bits (the game's EquipWeapon / EquipShield strings) */
static u32 worn_gear(void) {
    u64 slot = *(volatile u64 *)AD_EQUIP_OBJ;
    u64 gd = ptr_ok(slot) ? *(volatile u64 *)slot : 0;
    if (!ptr_ok(gd)) return 0;
    u64 buf[2] = {0, 0};
    if (!(((GdReadyFn)AD_GD_READY)(gd, buf, 0x060890B0u) & 1u)) return 0;
    static const u32 HASH[2] = {0xB6F13A1Du, 0x820A7EA3u};   /* EquipWeapon, EquipShield */
    u32 m = 0;
    for (int i = 0; i < 2; i++) {
        const char *nm = 0;
        if (!(((GdStringFn)AD_GD_STRING)(gd, &nm, buf, HASH[i]) & 1u)) continue;
        int g = gear_index(nm);
        if (g >= 0) m |= 1u << g;
    }
    return m;
}
static u32 cell_pane(u64 cells, u32 i, u64 *out) {
    u64 cell = ((CellAtFn)AD_CELL_AT)(cells, i);
    if (!ptr_ok(cell)) return 0;
    u64 a = *(volatile u64 *)(cell + 0xa0);
    if (!ptr_ok(a)) return 0;
    u64 pane = *(volatile u64 *)(a + 0x80);
    if (!ptr_ok(pane) || *(volatile unsigned short *)(pane + 0x13c) != 0x17) return 0;
    *out = *(volatile u64 *)(pane + 0x100);
    return ptr_ok(*out);
}
static void cursor_to(u64 drawer, u64 cur, u32 from, u32 to) {
    *(volatile u32 *)(cur + 0x4c) = to;
    ((CursorMoveFn)AD_CURSOR_MOVE)(drawer, from, to);
    ((CursorSetFn)AD_CURSOR_SET)(drawer, to);
}

/* The drawer's frame while it shows the armory and waits for a choice: the grid's cursor and cells. Returns 1 when
 * the frame was done here (the stock update is skipped), 0 to let the game run it (opening, closing ...). */
u32 g_ad_fail[4];   /* diagnostic: the armory frame's last refusal (step, value), frames done, frames refused */
#define AD_FAIL(k, v) do { g_ad_fail[0] = (k); g_ad_fail[1] = (u32)(v); g_ad_fail[3]++; return 0; } while (0)
int armory_update(u64 d) {
    if (!g_ad_drawer || d != g_ad_drawer || !g_ad_on || !g_ad_n) {
        if (g_ad_on && g_ad_drawer) AD_FAIL(1, d == g_ad_drawer);
        return 0;
    }
    u64 a = *(volatile u64 *)(d + 0x60), l = *(volatile u64 *)(d + 0x20), s = *(volatile u64 *)(d + 0x18);
    if (!ptr_ok(a) || *(volatile u32 *)(a + 0x10)) AD_FAIL(2, ptr_ok(a) ? *(volatile u32 *)(a + 0x10) : 0xEEEE);
    if (!ptr_ok(l) || *(volatile unsigned char *)(l + 0x3a) != 2) AD_FAIL(3, ptr_ok(l) ? *(volatile unsigned char *)(l + 0x3a) : 0xEEEE);
    if (!ptr_ok(s) || (*(volatile unsigned char *)(s + 0x1a5) & 0x80) || *(volatile unsigned char *)(s + 0x1a6) != 2)
        AD_FAIL(4, ptr_ok(s) ? *(volatile unsigned short *)(s + 0x1a5) : 0xEEEE);
    if (*(volatile unsigned char *)(d + 0x29c) & 1) AD_FAIL(5, 1);
    u64 cur = *(volatile u64 *)(d + 0x68);
    if (!ptr_ok(cur)) AD_FAIL(6, 0);
    u64 cells = *(volatile u64 *)(cur + 0x30);
    if (!ptr_ok(cells)) AD_FAIL(7, 0);
    u32 n = *(volatile u32 *)(cells + 0x124);
    u32 at = *(volatile u32 *)(cur + 0x4c);
    if (n == 0 || n > AD_N || n != g_ad_n || at >= n) AD_FAIL(8, n | g_ad_n << 8 | at << 16);
    u64 pane[AD_N];
    for (u32 i = 0; i < n; i++)
        if (!g_ad_map[i] || !cell_pane(cells, i, &pane[i])) AD_FAIL(9, i | g_ad_map[i] << 8);
    if (!g_ad_started) {   /* first frame: header away, cursor on the gear chosen last (or the row used last) */
        g_ad_started = 1;
        g_ad_worn = worn_gear();
        header_show(l, 1);
        u32 to = n;
        for (u32 i = 0; i < n && to == n; i++) if (g_ad_pick >= 0 && g_ad_map[i] == g_ad_pick + 1) to = i;
        for (u32 i = 0; i < n && to == n; i++) if ((u32)cell_row(i) == g_ad_row) to = i;
        if (to < n && to != at) { cursor_to(d, cur, at, to); at = to; }
    }
    /* the stick: one step per push */
    u64 cs = *(volatile u64 *)AD_STICK_SLOT;
    cs = ptr_ok(cs) ? *(volatile u64 *)(cs + 0xc0) : 0;
    u32 dir = 0;
    if (ptr_ok(cs)) {
        dir = stick_dir(*(volatile float *)(cs + 0x120), *(volatile float *)(cs + 0x124));
        if (!dir) dir = stick_dir(*(volatile float *)(cs + 0x128), *(volatile float *)(cs + 0x12c));
    }
    if (dir && dir != g_ad_dir) {
        u32 to = cell_step(at, dir);
        if (to != at) {
            cursor_to(d, cur, at, to);
            at = to;
            g_ad_moved = 1;
            g_ad_pick = g_ad_map[at] - 1;
            g_ad_row = (u32)cell_row(at);
            g_ad_dbg[3]++;
        }
    }
    g_ad_dir = dir;
    /* cells: shown, the worn gear's frame; the cursor over the selected one */
    for (u32 i = 0; i < n; i++) {
        u32 g = g_ad_map[i] - 1u;
        ((ShowFn)AD_PANE_SHOW)((void *)(pane[i] + 0xd10), 1);
        ((ShowFn)AD_PANE_SHOW)((void *)(pane[i] + 0x630), (g_ad_worn >> g) & 1u);
    }
    g_ad_fail[2]++;
    return 1;
}

void armory_bl_pre(u32 id, BlCtx *c) {
    switch (id) {
    case 0:   /* drawer open: the item sort option is not restored for the armory */
        if (g_arm_held) c->fn = 0;
        return;
    case 1:   /* list build starts: the armory's when its button holds the drawer */
        g_ad_on = g_arm_held && remap_on();
        for (int i = 0; i < AD_N; i++) g_ad_map[i] = 0;
        g_ad_n = 0;
        if (g_ad_on) { c->fn = (u64)AD_CONT_EQUIP; g_ad_dbg[0]++; }
        return;
    case 2:   /* a sorted-list flag: the armory list keeps the container's order */
        if (g_ad_on) { c->fn = 0; c->ret = 0; }
        return;
    case 3:   /* entry record: from the equipment category */
        if (g_ad_on) c->x[1] = 1;
        return;
    case 4: { /* keep an entry: owned gear of our list Link can use at his age (x4 bit 0: child) */
        if (!g_ad_on) return;
        c->fn = 0; c->ret = 0;
        u64 ref = c->x[1];
        if (!ptr_ok(ref)) return;
        int g = gear_index(*(const char *volatile *)ref);
        if (g < 0) return;
        if (!(AD_AGE[g] & ((c->x[4] & 1) ? 1 : 2))) return;
        if (((OwnedFn)AD_OWNED)(c->x[0], c->x[1], 1u, 0u) < 1) return;
        u32 pos = *(volatile u32 *)(c->x[0] + 0x498);
        if (pos >= AD_N) return;
        g_ad_map[pos] = (unsigned char)(g + 1);
        g_ad_n = pos + 1;
        g_ad_dbg[1]++;
        c->ret = 1;
        return;
    }
    case 5:   /* the drawer reads its list at open */
        g_ad_started = 0; g_ad_dir = 0; g_ad_cells = 0;
        if (g_ad_on) {
            c->x[1] = 1; g_ad_drawer = c->x19; g_ad_moved = 0; g_ad_dbg[2]++;
            u64 cur = *(volatile u64 *)(c->x19 + 0x68);
            if (ptr_ok(cur)) g_ad_cells = *(volatile u64 *)(cur + 0x30);
        } else {
            g_ad_drawer = 0;
            if (g_ad_hid_lay && g_ad_hid_lay == *(volatile u64 *)(c->x19 + 0x20)) {   /* items again: as the game had it */
                header_show(g_ad_hid_lay, 0);
            }
        }
        return;
    case 6:   /* ... and on a cursor move (called from the drawer's move code) */
        if (!g_ad_on) return;
        c->x[1] = 1;
        if (g_ad_drawer && c->x19 == g_ad_drawer && ptr_ok(c->x29) &&
            (*(volatile u64 *)(c->x29 + 8) & 0xFFFFFFFFFFFFull) == (u64)AD_RET_MOVE) {
            g_ad_moved = 1;
            g_ad_dbg[3]++;
        }
        return;
    case 7:
    case 8:
        if (g_ad_on) c->x[1] = 1;
        return;
    case 9:   /* the armory drawer never puts gear in the item box */
        if (g_ad_drawer && c->x19 == g_ad_drawer) { c->fn = 0; g_ad_dbg[5]++; }
        return;
    case 10:  /* release: equip the gear under the cursor if the player chose one */
        if (!g_ad_drawer || c->x19 != g_ad_drawer) return;
        c->fn = 0;
        if (g_ad_moved) { g_ad_moved = 0; equip_at_cursor(c->x19, c->x[0]); }
        return;
    case 12:  /* the layout with the sort window and its guide */
        g_ad_sortlay = *(volatile u64 *)(c->x19 + 0x28);
        g_ad_sortctl = c->x[0];
        return;
    case 13: { /* a cell's place in the list: the armory grid's */
        if (!g_ad_on || !g_ad_cells || c->x19 != g_ad_cells || !ptr_ok(c->x22)) {
            if (g_ad_scaled && ptr_ok(c->x[0])) ((ScaleFn)AD_PANE_SCALE)((void *)c->x[0], 1.0f, 1.0f);
            return;
        }
        u32 n = *(volatile u32 *)(g_ad_cells + 0x124);
        if (n == 0 || n > AD_N) return;
        u32 idx = *(volatile u32 *)(c->x22 + 0x38) == 2 ? *(volatile u32 *)(c->x22 + 0x34)
                                                       : *(volatile u32 *)(c->x22 + 0x2c);
        if (idx >= n || !g_ad_map[idx]) return;
        /* the game's cursor stays in the middle (its list scrolls under it): the grid moves so that the selected
         * cell is where the game puts it, the others around it */
        u64 cur = g_ad_drawer ? *(volatile u64 *)(g_ad_drawer + 0x68) : 0;
        u32 sel = ptr_ok(cur) ? *(volatile u32 *)(cur + 0x4c) : 0;
        if (sel >= n || !g_ad_map[sel]) sel = idx;
        float x, y, sx, sy;
        cell_xy(idx, &x, &y);
        cell_xy(sel, &sx, &sy);
        g_ad_pos_n++;
        /* the drawer clips what is far from its middle: the other cells smaller, so both rows fit */
        if (ptr_ok(c->x[0])) {
            float k = idx == sel ? 1.0f : 0.7f;
            ((ScaleFn)AD_PANE_SCALE)((void *)c->x[0], k, k);
            g_ad_scaled = 1;
        }
        if (idx != sel && cell_row(idx) == cell_row(sel)) x += x < sx ? -15.0f : 15.0f;   /* room for the big one */
        *(float *)&c->d[0] = x - sx;
        *(float *)&c->d[1] = *(float *)&c->d[1] + (y - sy);
        return;
    }
    case 11:  /* a cell's icon: no count under gear */
        if (g_ad_on) c->x[2] = 0xFFFFFFFFull;
        return;
    }
}

void armory_bl_post(u32 id, BlCtx *c) {
    if (id != 11) return;
    u64 cell = c->x[0];
    if (!ptr_ok(cell)) return;
    if (!g_ad_on) {   /* an item list: the icon pane as the game made it */
        if (g_ad_dirty) cell_fit(cell, 0);
        return;
    }
    u64 ref = c->x[1];
    if (!ptr_ok(ref)) return;
    const char *nm = *(const char *volatile *)ref;
    if (gear_index(nm) < 0) return;
    cell_fit(cell, 1);
    g_ad_dirty = 1;
    u64 rep = *(volatile u64 *)(cell + 0x80);
    if (!ptr_ok(rep)) return;
    static const char *name1, *name2;
    static char shadow[40];
    u32 i = 0;
    for (; i < 31u && nm[i]; i++) shadow[i] = nm[i];
    shadow[i++] = '_'; shadow[i++] = 'S'; shadow[i++] = 'h'; shadow[i] = 0;
    name1 = nm; name2 = shadow;
    u64 icon = *(volatile u64 *)(rep + 0x30), shade = *(volatile u64 *)(rep + 0x38);
    if (ptr_ok(icon)) tex_replace((void *)icon, &name1, 1u);
    if (ptr_ok(shade)) tex_replace((void *)shade, &name2, 1u);
}
