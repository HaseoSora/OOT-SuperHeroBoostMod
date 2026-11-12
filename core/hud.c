/* Unified HUD (F4). Our own parts, drawn by the engine's UI.
 *
 * How new parts get into the engine (all done by our code):
 *  1. The game builds each UI resource through a function at main+0x43A6F8
 *     (code hook 2): x0 = handle, x1 = build config whose first pointer is the
 *     UIL resource metadata. We hand it a private copy of the PlayerStatus_00
 *     metadata with extra parts, each described by cloning a stock part
 *     descriptor (the gauge for the stamina bar, the item button for the slots).
 *     The metadata is replaced before the engine allocates the pane arrays, so
 *     the parts are registered normally and find_part() resolves them.
 *  2. The stamina part is an instance of the gauge asset; when the engine loads
 *     that instance we substitute a private copy of the gauge file with a flat
 *     white fill tinted yellow. Slot parts use the stock item-button asset.
 *  3. Each scheduler frame (code hook 0) the parts are bound lazily and their
 *     animations are driven: gauge GaugeRatio/GaugeMax/TraceRatio, item button
 *     ItemPattern (icon) and StockNum (count).
 * Features never draw: they publish values with hud_set_stamina()/hud_set_slot().
 * The magic gauge is not used and is left untouched.
 *
 * NOTE: the NSO has no relocations, so no static table may hold addresses;
 * names are returned by code (part_name) instead.
 */
#include "dispatch.h"
#include "hud_names.h"

typedef unsigned long long u64;
typedef unsigned char u8;

extern char MAIN_SCHED_VT[];
extern void *find_part(void *node, const char *name);
extern void *find_anim(void *part, const char *name);
extern void set_frame(void *anim, float frame);
extern void *memcpy(void *d, const void *s, unsigned long n);

#define MARK 0x1000000000000000ull
/* Diagnostics (in .data, read by tools/live_check.py):
 * 0 mp controller, 1 frames, 2 bar, 3 ratio, 4 max, 5 trace,
 * 6 root clones, 7 gauge clones, 8 prepare calls, 9 last pane, 10 errors, 11 slots bound */
u64 g_hud_dbg[12] = {MARK, MARK, MARK, MARK, MARK, MARK, MARK, MARK, MARK, MARK, MARK, MARK};

static const char STOCK_TEX[] = "MpGaugeCenter_00";
static const char FLAT_TEX[] = "White8_00_BC4L";
static const char CIRCLE_TEX[] = "Circle64_00";

/* parts: 0 = stamina gauge, 1..4 = item slots (order: B, L, R, ZR) */
/* Every part is a clone of the engine's gauge widget (item-button clones are never
 * registered by the engine, see docs/RE-NOTES.md). Part 0 is the stamina bar;
 * parts 1..4 are the slot circles: the gauge's fill texture is replaced by the
 * stock Circle64_00 and the gauge is kept full, so it draws a tinted circle. The
 * art is a placeholder until the real assets arrive. */
#define PART_N 1   /* >1 does not work: only one appended part is built (see docs/RE-NOTES.md) */
#define APPEND_ALL 1   /* 1 = append every part (only the first one gets listed by the
                        * engine); 0 = parts 1.. repurpose filler parts (froze the game) */
#define SLOT_N 4

static const char *part_replaces(u32 i);
static const char *part_name(u32 i) {
    if (i == 0) return "Pa_OotStamina_00";
    if (i == 1) return "Pa_OotSlotB_00";
    if (i == 2) return "Pa_OotSlotL_00";
    if (i == 3) return "Pa_OotSlotR_00";
    return "Pa_OotSlotZR_00";
}
static u64 part_hash(u32 i) {
    switch (i) {
    case 0: return HASH_PART0;
    case 1: return HASH_PART1;
    case 2: return HASH_PART2;
    case 3: return HASH_PART3;
    default: return HASH_PART4;
    }
}
/* stock filler part each slot part takes over (0 = the appended stamina part) */
/* (if-chain, not a switch: the compiler may turn a switch of strings into a table of
 * absolute pointers, which this relocation-free module cannot use) */
__attribute__((noinline)) static const char *part_replaces(u32 i) {
    if (i == 0) return 0;
    if (i == 1) return "Pa_AgonyStone_00";
    if (i == 2) return "Pa_ReplaceSubItem_00";
    if (i == 3) return "Pa_ReplaceSubItem_01";
    return "Pa_GuideCross_00";
}

/* each private gauge copy needs its own asset name */
static const char *asset_name(u32 i) {
    switch (i) {
    case 0: return "PaOotStamina_00";
    case 1: return "PaOotSlotB_00";
    case 2: return "PaOotSlotL_00";
    case 3: return "PaOotSlotR_00";
    default: return "PaOotSlotZR_00";
    }
}

/* anchor of each part (layout units, root-relative, Y up; ~0.356 px per unit at 720p)
 * Slot circles form a diamond: ZR top, L left, R right, B bottom. */
static const float g_part_x[PART_N] = {-1560.0f, 1450.0f, 1300.0f, 1600.0f, 1450.0f};
static const float g_part_y[PART_N] = {736.0f, -300.0f, -150.0f, -150.0f, 0.0f};
/* local scale of the pane when shown (X from the descriptor, Y applied at runtime) */
static const float g_part_sx[PART_N] = {1.0f, 1.8f, 1.8f, 1.8f, 1.8f};
static const float g_part_sy[PART_N] = {1.0f, 1.7f, 1.7f, 1.7f, 1.7f};
/* tint (r, g, b) */
static const float g_part_rgb[PART_N][3] = {
    {1.0f, 0.85f, 0.15f}, {0.25f, 0.85f, 0.35f}, {0.95f, 0.8f, 0.2f},
    {0.3f, 0.55f, 1.0f}, {0.95f, 0.3f, 0.3f}};
#define CIRCLE_CAP 40.0f

/* -------- private allocation pool (bss, never freed) -------- */
static u8 g_pool[0x40000] __attribute__((aligned(16)));
static u32 g_used;

static void *pool_alloc(u32 n) {
    n = (n + 15u) & ~15u;
    if (n > sizeof(g_pool) - g_used) { g_hud_dbg[10] += 1; return 0; }
    void *p = g_pool + g_used;
    g_used += n;
    return p;
}
static void *pool_clone(const void *src, u32 n) {
    void *p = pool_alloc(n);
    if (p) memcpy(p, src, n);
    return p;
}

static u64 q(const void *p, u32 off) { return *(const u64 *)((const u8 *)p + off); }
static u32 w(const void *p, u32 off) { return *(const u32 *)((const u8 *)p + off); }
static int str_eq(const char *a, const char *b) {
    if (!a || !b) return 0;
    for (u32 i = 0; i < 96; i++) {
        if (a[i] != b[i]) return 0;
        if (!a[i]) return 1;
    }
    return 0;
}

/* name table at root+table: names[], descs[], hashes[], count at +24 */
static int name_index(const u8 *root, u32 table, const char *name) {
    u32 n = w(root, table + 24);
    if (n > 512) return -1;
    const u64 *names = (const u64 *)q(root, table);
    for (u32 i = 0; i < n; i++)
        if (str_eq((const char *)names[i], name)) return (int)i;
    return -1;
}

/* -------- step 1: PlayerStatus metadata with extra parts -------- */
static void extend_pools(u8 *root, u32 add);
__attribute__((unused)) static u8 *build_root_old(const u8 *r) {
    if (name_index(r, 0x20, part_name(0)) >= 0) return 0;
    u32 nc = w(r, 0x38), np = w(r, 0xD8);
    if (nc > 128 || np > 128) return 0;
    u8 *root = pool_clone(r, 0x228);
    u8 *first = pool_clone((const void *)((const u64 *)q(r, 0x28))[0], 68);
    if (!root || !first) return 0;
    /* The layout takes exactly one appended part (tested: further appended parts are
     * never listed by the engine). Part 0 is appended; parts 1.. take over filler
     * parts of the stock layout (same pane/part slot, renamed, turned into gauges). */
    u8 *cdesc[PART_N], *pdesc[PART_N];
    int cslot[PART_N], pslot[PART_N];   /* table index each part lives at */
    const u8 *mp_pdesc = (const u8 *)((const u64 *)q(r, 0xC8))[name_index(r, 0xC0, "Pa_MpGauge_00")];
    const u8 *mp_cdesc = (const u8 *)((const u64 *)q(r, 0x28))[name_index(r, 0x20, "Pa_MpGauge_00")];
    if (!mp_pdesc || !mp_cdesc) return 0;
    for (u32 k = 0; k < PART_N; k++) {
        const char *rep = APPEND_ALL ? 0 : part_replaces(k);
        int ci = rep ? name_index(r, 0x20, rep) : (int)(nc + (APPEND_ALL ? k : 0));
        int pi = rep ? name_index(r, 0xC0, rep) : (int)(np + (APPEND_ALL ? k : 0));
        if (ci < 0 || pi < 0) return 0;
        cslot[k] = ci; pslot[k] = pi;
        const u8 *sc = rep ? (const u8 *)((const u64 *)q(r, 0x28))[ci] : mp_cdesc;
        cdesc[k] = pool_clone(sc, 68);
        pdesc[k] = pool_clone(mp_pdesc, 88);       /* every part is a gauge instance */
        if (!cdesc[k] || !pdesc[k]) return 0;
        if (!rep) {
            *(u32 *)(cdesc[k] + 40) = 0;            /* parent: root pane */
            *(u32 *)(cdesc[k] + 52) = (u32)ci + 1;  /* subtree end = own index + 1 */
        } else {
            *(u32 *)(cdesc[k] + 40) = 0;            /* re-parent the leaf to the root */
        }
        *(u32 *)(cdesc[k] + 64) = 0x7FFFF;      /* visible in every root variant */
        cdesc[k][56] |= 1;
        *(float *)(cdesc[k] + 16) = g_part_sx[k];
        *(float *)(cdesc[k] + 20) = k == 0 ? 0.5f : g_part_sy[k];   /* stamina: half height */
        *(float *)(cdesc[k] + 28) = g_part_x[k];
        *(float *)(cdesc[k] + 32) = g_part_y[k];
        *(u32 *)(pdesc[k] + 64) = (u32)ci;          /* part -> index of its pane */
    }
    const u32 ADD = APPEND_ALL ? PART_N : 1;
    *(u32 *)(first + 52) = nc + ADD;            /* root subtree includes the appended panes */
    for (u32 t = 0; t < 2; t++) {
        u32 off = t ? 0xC0 : 0x20, n = t ? np : nc;
        for (u32 j = 0; j < 3; j++) {
            u64 *a = pool_alloc((n + ADD) * 8);
            if (!a) return 0;
            memcpy(a, (const void *)q(r, off + j * 8), n * 8);
            for (u32 k = 0; k < PART_N; k++) {
                u32 at = t ? (u32)pslot[k] : (u32)cslot[k];
                a[at] = j == 0 ? (u64)part_name(k)
                      : j == 1 ? (u64)(t ? pdesc[k] : cdesc[k])
                               : part_hash(k);
            }
            if (!t && j == 1) a[0] = (u64)first;
            *(u64 *)(root + off + j * 8) = (u64)a;
        }
        *(u32 *)(root + off + 24) = n + ADD;
    }
    extend_pools(root, ADD);
    g_hud_dbg[6] += 1;
    return root;
}

/* Test (multi-part): grow the per-type pools at the end of the root header
 * ({u32 count, u32 stride, u64 ptr}, 16 B each at +0x1D0,+0x1E0,+0x1F0,+0x210,+0x220) by
 * `add` entries, each a copy of the last one, in case the part/pane setup indexes them. */
static void extend_pools(u8 *root, u32 add) {
    static const u32 offs[5] = {0x1D0, 0x1E0, 0x1F0, 0x210, 0x220};
    for (u32 i = 0; i < 5; i++) {
        u32 off = offs[i];
        u32 cnt = w(root, off), stride = w(root, off + 4);
        const u8 *old = (const u8 *)q(root, off + 8);
        if (!old || cnt == 0 || cnt > 256 || stride == 0 || stride > 64) continue;
        u8 *neu = pool_alloc((cnt + add) * stride);
        if (!neu) continue;
        memcpy(neu, old, cnt * stride);
        for (u32 j = 0; j < add; j++) memcpy(neu + (cnt + j) * stride, old + (cnt - 1) * stride, stride);
        *(u64 *)(root + off + 8) = (u64)neu;
        *(u32 *)(root + off) = cnt + add;
    }
}

/* Current design: ONE appended part (stamina gauge, the layout takes exactly one) and
 * the slot parts are four stock filler parts turned into item buttons in place: same
 * pane slot, same name, same parent; only the part descriptor changes to the item
 * button's. They are driven by their original names. */
static u8 *build_root(const u8 *r) {
    if (name_index(r, 0x20, part_name(0)) >= 0) { g_hud_dbg[9] = MARK | 1; return 0; }
    u32 nc = w(r, 0x38), np = w(r, 0xD8);
    if (nc > 128 || np > 128) { g_hud_dbg[9] = MARK | 2; return 0; }
    int mci = name_index(r, 0x20, "Pa_MpGauge_00"), mpi = name_index(r, 0xC0, "Pa_MpGauge_00");
    int spi = name_index(r, 0xC0, "Pa_SelectItem_00");
    if (mci < 0 || mpi < 0 || spi < 0) { g_hud_dbg[9] = MARK | 3; return 0; }
    u8 *root = pool_clone(r, 0x228);
    u8 *first = pool_clone((const void *)((const u64 *)q(r, 0x28))[0], 68);
    u8 *cd0 = pool_clone((const void *)((const u64 *)q(r, 0x28))[mci], 68);
    u8 *pd0 = pool_clone((const void *)((const u64 *)q(r, 0xC8))[mpi], 88);
    if (!root || !first || !cd0 || !pd0) { g_hud_dbg[9] = MARK | 4; return 0; }
    *(u32 *)(cd0 + 40) = 0;                    /* parent: root pane */
    *(u32 *)(cd0 + 52) = nc + 1;               /* subtree end = own index + 1 */
    *(u32 *)(cd0 + 64) = 0x7FFFF;
    cd0[56] |= 1;
    *(float *)(cd0 + 16) = g_part_sx[0];
    *(float *)(cd0 + 20) = 0.5f;               /* stamina: half height */
    *(float *)(cd0 + 28) = g_part_x[0];
    *(float *)(cd0 + 32) = g_part_y[0];
    *(u32 *)(pd0 + 64) = nc;
    *(u32 *)(first + 52) = nc + 1;
    const u8 *sel_pdesc = (const u8 *)((const u64 *)q(r, 0xC8))[spi];
    /* tables: copy with one extra entry for the appended stamina part */
    u64 *tab[2][3];
    for (u32 t = 0; t < 2; t++) {
        u32 off = t ? 0xC0 : 0x20, n = t ? np : nc;
        for (u32 j = 0; j < 3; j++) {
            u64 *a = pool_alloc((n + 1) * 8);
            if (!a) { g_hud_dbg[9] = MARK | 5; return 0; }
            memcpy(a, (const void *)q(r, off + j * 8), n * 8);
            a[n] = j == 0 ? (u64)part_name(0) : j == 1 ? (u64)(t ? pd0 : cd0) : part_hash(0);
            if (!t && j == 1) a[0] = (u64)first;
            tab[t][j] = a;
            *(u64 *)(root + off + j * 8) = (u64)a;
        }
        *(u32 *)(root + off + 24) = n + 1;
    }
    /* repurpose the filler parts: only their part descriptor changes */
    for (u32 k = 1; k < PART_N; k++) {
        const char *rep = part_replaces(k);
        int ci = name_index(r, 0x20, rep), pi = name_index(r, 0xC0, rep);
        g_hud_dbg[3] = MARK | (u64)(u32)(w(r, 0x38) << 8 | w(r, 0xD8)) | ((u64)(u32)(rep ? rep[3] : 0) << 32);
        if (ci < 0 || pi < 0) {
            g_hud_dbg[9] = MARK | ((u64)k << 32) | ((u64)(u32)(ci + 1) << 16) | (u64)(u32)(pi + 1);
            return 0;
        }
        const u8 *stock_p = (const u8 *)((const u64 *)q(r, 0xC8))[pi];
        u8 *pd = pool_clone(sel_pdesc, 88);
        if (!pd) { g_hud_dbg[9] = MARK | 7; return 0; }
        *(u32 *)(pd + 64) = w(stock_p, 64);     /* keep the pane index of the original part */
        tab[1][1][pi] = (u64)pd;
        (void)ci;
    }
    g_hud_dbg[6] += 1;
    return root;
}

/* -------- step 2: private copy of the gauge file, flat white tinted -------- */
static u8 *build_gauge(const u8 *r, u32 k) {
    const u8 *base = r - 0xF8;
    u32 n = w(base, 8);
    if (w(base, 0) != 0x48464642u || n < 0x7500 || n > 0x10000) return 0;
    u8 *out = pool_clone(base, n);
    if (!out) return 0;
    /* the file stores absolute pointers into itself: rebase them */
    for (u32 i = 0; i + 8 <= n; i += 8) {
        u64 v = q(out, i);
        if (v >= (u64)base && v < (u64)base + n) *(u64 *)(out + i) = (u64)out + (v - (u64)base);
    }
    for (u32 i = 0; i + 8 <= n; i += 8) {
        u64 v = q(out, i);
        if (v < (u64)out || v >= (u64)out + n) continue;
        const char *s = (const char *)v;
        if (str_eq(s, STOCK_TEX)) *(u64 *)(out + i) = (u64)FLAT_TEX;
        /* sparkle / flash / particle textures of the gauge become circles: the panes that
         * use them are repositioned as the slot circles (drive_circles) */
        else if (str_eq(s, "MpKiraKira_00") || str_eq(s, "MpKiraKira_01") || str_eq(s, "MpKiraKira_02") ||
                 str_eq(s, "MpGaugeFlash_01") || str_eq(s, "MpGaugeGlowParticle_00") ||
                 str_eq(s, "MpGaugeGlowParticle_01") || str_eq(s, "MpGaugeGlow_00") ||
                 str_eq(s, "MpGaugeGlow_01") || str_eq(s, "Kumo64_00_BC4L") ||
                 str_eq(s, "Half8_00_ASTC4x4") || str_eq(s, "Half8_01_BC4L"))
            *(u64 *)(out + i) = (u64)CIRCLE_TEX;
    }
    /* palette words (verified before touching): our tint instead of green */
    const float *c = g_part_rgb[k];
    float *a = (float *)(out + 0x74D8);
    if (a[0] == 1.0f && a[1] == 1.0f && a[2] == 1.0f && a[3] == 1.0f) { a[0] = c[0]; a[1] = c[1]; a[2] = c[2]; }
    float *b = (float *)(out + 0x74E8);
    if (b[1] > 0.5646f && b[1] < 0.5648f) { b[0] = c[0]; b[1] = c[1]; b[2] = c[2]; b[3] = 1.0f; }
    *(u64 *)(out + 0x110) = (u64)asset_name(k);
    g_hud_dbg[7] += 1;
    return out + 0xF8;
}

/* cache of replaced resources and the per-call config copies */
static struct { const u8 *src; u8 *copy; u32 kind; } g_res[16];
static u32 g_res_n;
static struct { void *handle; u8 config[0x100]; } g_calls[64];
static u32 g_calls_n;

u64 g_prep_dbg[20] = {1};   /* per part: handle, config, handle+0x28, handle+0x38 */

void *hud_prepare(void *handle, u8 *config) {
    g_hud_dbg[8] += 1;
    const u8 *r = (const u8 *)q(config, 0);
    if (!r || w(r, 0) != 0x004C4955u) return config;   /* "UIL\0" */
    const char *asset = (const char *)q(r, 0x18);
    const char *inst = (const char *)q(handle, 0x30);
    u32 kind = str_eq(asset, "PlayerStatus_00") ? 1 : 0;
    if (!kind)
        for (u32 k = 0; k < PART_N; k++)
            if (str_eq(inst, part_name(k))) { kind = 2 + k; break; }   /* gauge copy for part k */
    if (!kind) return config;
    u8 *rep = 0;
    u32 i;
    for (i = 0; i < g_res_n; i++)
        if (g_res[i].src == r && g_res[i].kind == kind) { rep = g_res[i].copy; break; }
    if (i == g_res_n) {
        if (g_res_n == 16) return config;
        rep = kind == 1 ? build_root(r) : build_gauge(r, kind - 2);
        if (!rep) return config;
        g_res[i].src = r; g_res[i].copy = rep; g_res[i].kind = kind;
        g_res_n++;
    }
    if (kind >= 2) {
        u32 s = (kind - 2) * 4;
        g_prep_dbg[s] = (u64)handle; g_prep_dbg[s + 1] = (u64)config;
        g_prep_dbg[s + 2] = q(handle, 0x28); g_prep_dbg[s + 3] = q(handle, 0x38);
    }
    /* A fresh config copy per call: the engine may keep the pointer, and the same
     * handle address can be reused for different parts. */
    u8 *cfg = pool_alloc(0x100);
    if (!cfg) return config;
    memcpy(cfg, config, 0x100);   /* the +0x80 field must survive */
    *(u64 *)cfg = (u64)rep;
    (void)g_calls_n; (void)g_calls;
    return cfg;
}

/* -------- step 3: per-frame drive -------- */
static void observe_stock_box(u64 parent);

static u64 g_mp;
static u64 g_frame_node, g_bar, g_ratio, g_max, g_trace, g_pane;
static float g_value = 50.0f, g_cap = 100.0f, g_show = 1.0f;
static float g_last_value = -1.0f, g_last_cap = -1.0f, g_last_show = -1.0f;
static u32 g_test_mode = 1;
static u32 g_tick;

/* slot parts */
typedef struct {
    u64 part, ratio, max, trace, pane;
    float icon, count, show;            /* wanted */
    float l_show, l_icon;               /* last applied */
    u32 done;
} SlotPart;
static SlotPart g_slot[SLOT_N];

void hud_set_stamina(float value, float cap, float show) {
    g_value = value; g_cap = cap; g_show = show;
    g_test_mode = 0;
}

/* slot i (0..3): icon = ItemPattern frame, count = StockNum (<0 hides the number),
 * show = 0/1 */
void hud_set_slot(u32 i, float icon, float count, float show) {
    if (i >= SLOT_N) return;
    g_slot[i].icon = icon; g_slot[i].count = count; g_slot[i].show = show;
}

static u64 ptr(u64 p, u32 off) { return *(u64 *)(p + off); }

static u64 pane_record(u64 frame, const char *name) {
    u64 layout = ptr(frame, 0x80);
    if (!layout) return 0;
    const u8 *r = (const u8 *)ptr(layout, 0xF8);
    if (!r) return 0;
    int i = name_index(r, 0x20, name);
    return i < 0 ? 0 : ptr(layout, 0x100) + (u64)i * 0xB0;
}

static void set_pane_show(u64 pane, float scale_y) {
    *(float *)(pane + 0x64) = scale_y;   /* local Y scale: 0 hides */
    *(u32 *)pane |= 0x6F;                /* mark the pane dirty */
}

u64 g_bind_dbg[4] = {MARK, MARK, MARK, MARK};   /* slot 0: part, pat, num, pane */
float g_pos_dbg[8];

static void bind_slots(u64 parent) {
    if (PART_N <= 1) return;   /* slot parts only exist when stock parts are repurposed */
    for (u32 i = 0; i < SLOT_N; i++) {
        SlotPart *s = &g_slot[i];
        if (s->part) continue;
        const char *nm = part_name(i + 1);
        u64 part = (u64)find_part((void *)parent, nm);
        if (!part) continue;
        /* find_anim returns a shared "not found" object instead of null: reject it */
        u64 none = (u64)find_anim((void *)part, "__no_such_anim__");
        u64 pat = (u64)find_anim((void *)part, "ItemPattern");   /* icon (stored in .ratio) */
        if (pat == none) pat = 0;
        u64 num = (u64)find_anim((void *)part, "StockNum");      /* count (stored in .max) */
        u64 pane = pane_record(parent, nm);
        g_hud_dbg[10 - 0] += 0;
        if (i == 0) { g_bind_dbg[0] = MARK | part; g_bind_dbg[1] = MARK | pat; g_bind_dbg[2] = MARK | num; g_bind_dbg[3] = MARK | pane; }
        if (!pat || !pane) continue;
        s->part = part; s->ratio = pat; s->max = num; s->pane = pane;
        s->l_show = -1e9f; s->l_icon = -1e9f;
        s->done = 0;
        g_hud_dbg[11] += 1;
    }
}

/* Slot item buttons (stock item-button parts): placed once, icon = ItemPattern frame,
 * visible only while assigned. */
static void drive_slots(void) {
    for (u32 i = 0; i < SLOT_N; i++) {
        SlotPart *s = &g_slot[i];
        if (!s->part) continue;
        if (!s->done) {
            *(float *)(s->pane + 0x6C) = g_part_x[i + 1];   /* authored translation */
            *(float *)(s->pane + 0x70) = g_part_y[i + 1];
            *(u32 *)s->pane |= 0x6F;
            s->done = 1;
        }
        if (s->l_show != s->show) {
            set_pane_show(s->pane, s->show > 0.5f ? 1.0f : 0.0f);
            s->l_show = s->show;
        }
        if (s->l_icon != s->icon) { set_frame((void *)s->ratio, s->icon); s->l_icon = s->icon; }
    }
}

/* Slot circles: four picture panes inside the stamina part's own layout. Panes of the
 * child layout (index = order in PaMpGauge): 6 and 7 particles, 14 flash, 19 sparkle. */
#define CIRCLE_D 150.0f
static const u32 CIRCLE_PANE[SLOT_N] = {3, 4, 18, 15};
static void drive_circles(void) {
    if (!g_bar) return;
    u64 cl = ptr(g_bar, 0x80);
    if (!cl) return;
    u64 arr = ptr(cl, 0x100);
    u32 cnt = *(unsigned short *)(cl + 0x13C);
    if (!arr || cnt < 20) return;
    for (u32 i = 0; i < SLOT_N; i++) {
        u64 p = arr + (u64)CIRCLE_PANE[i] * 0xB0;
        float on = g_slot[i].show > 0.5f ? 1.0f : 0.0f;
        float w_ = *(float *)(p + 0x58), h_ = *(float *)(p + 0x5C);
        if (w_ < 1.0f || h_ < 1.0f) continue;
        *(float *)(p + 0x60) = on * CIRCLE_D / w_;
        *(float *)(p + 0x64) = on * CIRCLE_D / h_;
        /* local position = layout target minus the part's own anchor */
        *(float *)(p + 0x6C) = g_part_x[i + 1] - g_part_x[0];
        *(float *)(p + 0x70) = g_part_y[i + 1] - g_part_y[0];
        *(u32 *)p |= 0x6F;
    }
}

static void hud_frame(void) {
    g_hud_dbg[1] = MARK | ++g_tick;
    if (!g_mp) return;
    if (!g_bar) {
        u64 owner = ptr(g_mp, 0x18);
        if (!owner) return;
        u64 parent = ptr(owner, 0x28);
        if (!parent) return;
        u64 bar = (u64)find_part((void *)parent, part_name(0));
        g_hud_dbg[2] = MARK | bar;
        if (!bar) return;
        u64 ratio = (u64)find_anim((void *)bar, "GaugeRatio");
        u64 max = (u64)find_anim((void *)bar, "GaugeMax");
        u64 trace = (u64)find_anim((void *)bar, "TraceRatio");
        g_hud_dbg[3] = MARK | ratio;
        g_hud_dbg[4] = MARK | max;
        g_hud_dbg[5] = MARK | trace;
        u64 pane = pane_record(parent, part_name(0));
        g_hud_dbg[9] = MARK | pane;
        if (!ratio || !max || !trace || !pane) return;
        observe_stock_box(parent);
        g_frame_node = parent; g_bar = bar; g_ratio = ratio; g_max = max; g_trace = trace;
        g_pane = pane;
        g_last_value = g_last_cap = g_last_show = -1.0f;
    }
    bind_slots(g_frame_node);
    drive_slots();
    drive_circles();
    if (g_test_mode) {
        u32 t = g_tick % 240;
        g_value = (t < 120 ? t : 240 - t) * (100.0f / 120.0f);
        g_cap = 100.0f;
        g_show = 1.0f;
    }
    if (g_last_show != g_show) {
        /* The part's own pane stays visible (it also carries the slot circles); only the
         * bar container (child pane 1, N_Gauge_01) is hidden by scaling it to zero. */
        set_pane_show(g_pane, 1.0f);
        u64 cl = ptr(g_bar, 0x80);
        u64 arr = cl ? ptr(cl, 0x100) : 0;
        if (arr) {
            u64 c1 = arr + 1 * 0xB0;
            *(float *)(c1 + 0x60) = g_show;
            *(float *)(c1 + 0x64) = g_show;
            *(u32 *)c1 |= 0x6F;
        }
        g_last_show = g_show;
    }
    if (g_last_cap != g_cap) {
        set_frame((void *)g_max, g_cap);
        g_last_cap = g_cap;
    }
    if (g_last_value != g_value) {
        u64 transform = ptr(g_ratio, 0x20);
        float length = (float)*(u32 *)(ptr(transform, 0) + 0x28);
        float frame = length - g_value;
        if (frame < 0.0f) frame = 0.0f;
        set_frame((void *)g_ratio, frame);
        set_frame((void *)g_trace, frame);
        g_last_value = g_value;
    }
}

/* -------- observation of the stock item box (to learn icon frames) -------- */
#define FL_N 24
typedef struct { u32 tag; float frame; } FrameLog;
FrameLog g_fl[FL_N] = {{0x7FFFFFFFu, 0.0f}};
u32 g_fl_n = 0x10000000u;
static u64 g_stock_pat, g_stock_num;
u64 g_stock_dbg[4] = {MARK, MARK, MARK, MARK};
static float g_last_tagged[3] = {-1e9f, -1e9f, -1e9f};

static void observe_stock_box(u64 parent) {
    if (g_stock_pat) return;
    u64 box = (u64)find_part((void *)parent, "Pa_SelectItem_00");
    g_stock_dbg[0] = MARK | box;
    if (!box) return;
    g_stock_pat = (u64)find_anim((void *)box, "ItemPattern");
    g_stock_num = (u64)find_anim((void *)box, "StockNum");
    g_stock_dbg[1] = MARK | g_stock_pat;
    g_stock_dbg[2] = MARK | g_stock_num;
}

/* last frame the game put on the stock icon/count animations (read by classic) */
float g_last_pat_frame = -1.0f, g_last_num_frame = -1.0f;
u32 g_pat_changes;

static void on_set_frame(u64 anim, float frame) {
    u32 tag = 0;
    if (anim && anim == g_stock_pat) { tag = 1; g_last_pat_frame = frame; g_pat_changes++; }
    else if (anim && anim == g_stock_num) { tag = 2; g_last_num_frame = frame; }
    if (!tag || g_last_tagged[tag] == frame) return;
    g_last_tagged[tag] = frame;
    FrameLog *e = &g_fl[(g_fl_n - 0x10000000u) % FL_N];
    g_fl_n++;
    e->tag = tag;
    e->frame = frame;
}

u32 g_inst_log[32] = {0x7FFFFFFFu};   /* pane indices passed to part instantiation */
u32 g_inst_n = 0x10000000u;
u64 g_inst_child[32] = {1};
#define INST_LOG g_inst_log

void hud_on_code(u32 id, void *a0, void *a1, void *a2, void *regs) {
    (void)a1; (void)a2;
    if (id == 4) {   /* part instance creation: log the pane index being instantiated */
        u64 layout = (u64)a1, pane = (u64)a2;
        u64 arr = layout ? ptr(layout, 0x100) : 0;
        const u8 *lr = layout ? (const u8 *)ptr(layout, 0xF8) : 0;
        if (!lr || !str_eq((const char *)q(lr, 0x18), "PlayerStatus_00")) return;
        {   /* child frame object the caller prepared: x0 -> [x0+8] -> [0]; null = creation failed */
            u64 o = (u64)a0, c = 0;
            if (o && ptr(o, 8)) c = ptr(ptr(o, 8), 0);
            g_inst_child[(g_inst_n - 0x10000000u) % 32] = c;
        }
        INST_LOG[(g_inst_n - 0x10000000u) % 32] = arr ? (u32)((pane - arr) / 0xB0) : 0xFFFFFFFFu;
        g_inst_n++;
        return;
    }
    if (id == 3) {
        on_set_frame((u64)a0, *(float *)((u8 *)regs + 0xB0));   /* saved d0 low word = s0 */
        return;
    }
    if (id == 1) {
        g_mp = (u64)a0;
        g_bar = 0;
        for (u32 i = 0; i < SLOT_N; i++) g_slot[i].part = 0;
        g_hud_dbg[0] = MARK | g_mp;
    } else if (id == 0) {
        if (a0 && *(u64 *)a0 == (u64)MAIN_SCHED_VT) hud_frame();
    }
}












