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
#define PART_N 8   /* >1 does not work: only one appended part is built (see docs/RE-NOTES.md) */
#define APPEND_ALL 1   /* 1 = append every part (only the first one gets listed by the
                        * engine); 0 = parts 1.. repurpose filler parts (froze the game) */
#define SLOT_N 4
#ifndef SWAP_FILL
#define SWAP_FILL 1  /* 1 = replace the gauge's fill texture with a flat white one */
#endif

#define RING_SIZE 0.45f   /* whole-ring scale (part scale) */
#define SEG_N 8   /* ring segments = appended gauge parts */
static const char *part_replaces(u32 i);
/* names live in .data as char arrays (no pointer tables: the module has no relocations) */
static char g_pnames[SEG_N][16] = {"Pa_OotSeg_00", "Pa_OotSeg_01", "Pa_OotSeg_02", "Pa_OotSeg_03",
    "Pa_OotSeg_04", "Pa_OotSeg_05", "Pa_OotSeg_06", "Pa_OotSeg_07"};
static char g_anames[SEG_N][16] = {"PaOotSeg_00", "PaOotSeg_01", "PaOotSeg_02", "PaOotSeg_03",
    "PaOotSeg_04", "PaOotSeg_05", "PaOotSeg_06", "PaOotSeg_07"};
static const u64 g_phash[SEG_N] = {HASH_PART0, HASH_PART1, HASH_PART2, HASH_PART3, HASH_PART4,
    HASH_PART5, HASH_PART6, HASH_PART7};
static const char *part_name(u32 i) { return g_pnames[i % SEG_N]; }
static u64 part_hash(u32 i) { return g_phash[i % SEG_N]; }
__attribute__((unused, noinline)) static const char *part_replaces(u32 i) { (void)i; return 0; }
static const char *asset_name(u32 i) { return g_anames[i % SEG_N]; }
/* ring centre: where Link usually stands on screen (layout units, root-relative, Y up;
 * ~0.356 px per unit at 720p). Placeholder until the ring follows his projected position. */
static const float g_part_x[1] = {0.0f};
static const float g_part_y[1] = {-330.0f};
static const float g_part_rgb[1][3] = {{1.0f, 0.85f, 0.15f}};
#define CIRCLE_CAP 40.0f

/* -------- private allocation pool (bss, never freed) -------- */
static u8 g_pool[0x100000] __attribute__((aligned(16)));
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
    if (mci < 0 || mpi < 0) { g_hud_dbg[9] = MARK | 3; return 0; }
    u8 *root = pool_clone(r, 0x228);
    u8 *first = pool_clone((const void *)((const u64 *)q(r, 0x28))[0], 68);
    if (!root || !first) { g_hud_dbg[9] = MARK | 4; return 0; }
    /* PART_N appended gauge parts (the ring segments): pane nc+k, part descriptor np+k.
     * The engine finds each part's descriptor through cdesc+0x42, so it must name np+k. */
    u8 *cdk[PART_N], *pdk[PART_N];
    for (u32 k = 0; k < PART_N; k++) {
        cdk[k] = pool_clone((const void *)((const u64 *)q(r, 0x28))[mci], 68);
        pdk[k] = pool_clone((const void *)((const u64 *)q(r, 0xC8))[mpi], 88);
        if (!cdk[k] || !pdk[k]) { g_hud_dbg[9] = MARK | 4; return 0; }
        *(u32 *)(cdk[k] + 40) = 0;                    /* parent: root pane */
        *(u32 *)(cdk[k] + 52) = nc + k + 1;           /* subtree end = own index + 1 */
        *(u32 *)(cdk[k] + 64) = 0x7FFFF;
        cdk[k][56] |= 1;
        *(unsigned short *)(cdk[k] + 0x42) = (unsigned short)(np + k);
        *(float *)(cdk[k] + 16) = RING_SIZE;
        *(float *)(cdk[k] + 20) = RING_SIZE;
        *(float *)(cdk[k] + 28) = g_part_x[0];
        *(float *)(cdk[k] + 32) = g_part_y[0];
        *(u32 *)(pdk[k] + 64) = nc + k;               /* part -> index of its pane */
    }
    *(u32 *)(first + 52) = nc + PART_N;
    for (u32 t = 0; t < 2; t++) {
        u32 off = t ? 0xC0 : 0x20, n = t ? np : nc;
        for (u32 j = 0; j < 3; j++) {
            u64 *a = pool_alloc((n + PART_N) * 8);
            if (!a) { g_hud_dbg[9] = MARK | 5; return 0; }
            memcpy(a, (const void *)q(r, off + j * 8), n * 8);
            for (u32 k = 0; k < PART_N; k++)
                a[n + k] = j == 0 ? (u64)part_name(k) : j == 1 ? (u64)(t ? pdk[k] : cdk[k]) : part_hash(k);
            if (!t && j == 1) a[0] = (u64)first;
            *(u64 *)(root + off + j * 8) = (u64)a;
        }
        *(u32 *)(root + off + 24) = n + PART_N;
    }
    extend_pools(root, PART_N);
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
        if (SWAP_FILL && str_eq(s, STOCK_TEX)) *(u64 *)(out + i) = (u64)FLAT_TEX;
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
    const float *c = g_part_rgb[0]; (void)k;
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

char g_pl[40][32] = {{1}};
u32 g_pl_n = 1;

void *hud_prepare(void *handle, u8 *config) {
    g_hud_dbg[8] += 1;
    const u8 *r = (const u8 *)q(config, 0);
    if (!r || w(r, 0) != 0x004C4955u) return config;   /* "UIL\0" */
    const char *asset = (const char *)q(r, 0x18);
    const char *inst = (const char *)q(handle, 0x30);
    if (inst && asset && g_pl_n < 40 &&
        ((inst[0] == 'P' && inst[3] == 'O' && inst[4] == 'o') || (asset[0] == 'M' && asset[1] == 'p') ||
         (asset[0] == 'P' && asset[1] == 'l'))) {
        char *d = g_pl[g_pl_n++];
        for (int i = 0; i < 15; i++) { d[i] = inst[i]; d[16 + i] = asset[i]; }
    }
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
    if (kind >= 2 && kind < 7) {
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
static u64 g_frame_node;
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

/* ---- stamina ring: SEG_N appended gauge parts, each one radial tick of the ring ----
 * Every part is a private gauge copy. Its container pane (N_Gauge_01, index 1) is moved to
 * the part origin and rotated about it, so the bar (which extends left of the container's
 * origin) becomes a spoke at the wanted angle; the fill pane (P_Gauge_01, 17) is scaled
 * to show the segment's share of the value. */
/* octagon: side k is the bar of part k, tangent to a circle of apothem 190 (clockwise from the top).
 * Per side: container position (bar centre = apothem point, bar length 160) and rotation. */
static const float OCT_X[SEG_N] = {300.00f, 346.48f, 190.00f, -77.78f, -300.00f, -346.48f, -190.00f, 77.78f};
static const float OCT_Y[SEG_N] = {190.00f, -77.78f, -300.00f, -346.48f, -190.00f, 77.78f, 300.00f, 346.48f};
static const float OCT_R[SEG_N] = {0.00000f, -0.78540f, -1.57080f, -2.35619f, -3.14159f, -3.92699f, -4.71239f, -5.49779f};
typedef struct { u64 bar, ratio, max, trace, layout_arr; u32 init; float l_fill, l_show; } Seg;
static Seg g_seg[SEG_N];
u32 g_seg_ok = 0x10000000u;

u32 g_len[3] = {0x7777, 0x7777, 0x7777};

static void bind_segs(u64 parent) {
    u32 ok = 0;
    for (u32 k = 0; k < SEG_N; k++) {
        Seg *s = &g_seg[k];
        if (s->bar) { ok++; continue; }
        u64 bar = (u64)find_part((void *)parent, part_name(k));
        if (!bar) continue;
        u64 none = (u64)find_anim((void *)bar, "__no_such_anim__");
        u64 ratio = (u64)find_anim((void *)bar, "GaugeRatio");
        u64 max = (u64)find_anim((void *)bar, "GaugeMax");
        u64 trace = (u64)find_anim((void *)bar, "TraceRatio");
        if (!ratio || !max || !trace || ratio == none || max == none || trace == none) continue;
        u64 cl = ptr(bar, 0x80);
        u64 arr = cl ? ptr(cl, 0x100) : 0;
        if (!arr) continue;
        s->bar = bar; s->ratio = ratio; s->max = max; s->trace = trace; s->layout_arr = arr;
        s->l_fill = -1.0f; s->l_show = -1.0f;
        g_hud_dbg[2] = MARK | bar;
        ok++;
    }
    g_seg_ok = 0x10000000u + ok;
}

static void drive_segs(void) {
    float frac = g_cap > 0.0f ? g_value / g_cap : 0.0f;
    if (frac < 0.0f) frac = 0.0f;
    if (frac > 1.0f) frac = 1.0f;
    for (u32 k = 0; k < SEG_N; k++) {
        Seg *s = &g_seg[k];
        if (!s->bar) continue;
        if (!s->init) {
            set_frame((void *)s->max, 100.0f);      /* bar width is fixed */
            set_frame((void *)s->ratio, 473.0f);    /* fill pose = sits on the base */
            set_frame((void *)s->trace, 473.0f);
            s->init = 1;
        }
        float lit = frac * (float)SEG_N - (float)k;   /* 0..1 = this segment's fill */
        if (lit < 0.0f) lit = 0.0f;
        if (lit > 1.0f) lit = 1.0f;
        float show = g_show > 0.5f ? 1.0f : 0.0f;
        u64 arr = s->layout_arr;
        u64 c1 = arr + 1 * 0xB0;     /* container: spoke at angle k */
        *(float *)(c1 + 0x60) = show;
        *(float *)(c1 + 0x64) = show;
        *(float *)(c1 + 0x68) = OCT_R[k];      /* radians, counter-clockwise positive */
        *(float *)(c1 + 0x6C) = OCT_X[k];
        *(float *)(c1 + 0x70) = OCT_Y[k];
        *(u32 *)c1 |= 0x6F;        u64 f = arr + 17 * 0xB0;     /* fill */
        *(float *)(f + 0x60) = lit * 0.908f;
        *(float *)(f + 0x64) = 1.0f;
        *(float *)(f + 0x6C) = -380.0f;
        *(float *)(f + 0x70) = 0.0f;
        *(u32 *)f |= 0x6F;
        static const u32 HIDE[1] = {8};   /* gauge shadow window */
        u64 h = arr + (u64)HIDE[0] * 0xB0;
        *(float *)(h + 0x60) = 0.0f;
        *(float *)(h + 0x64) = 0.0f;
        *(u32 *)h |= 0x6F;
    }
}

static void hud_frame(void) {
    g_hud_dbg[1] = MARK | ++g_tick;
    if (!g_mp) return;
    if (!g_frame_node) {
        u64 owner = ptr(g_mp, 0x18);
        if (!owner) return;
        u64 parent = ptr(owner, 0x28);
        if (!parent) return;
        g_frame_node = parent;
    }
    bind_segs(g_frame_node);
    if (g_test_mode) {
        u32 p = (g_tick / 120) % 13;     /* demo sweep 0..100 until the game publishes */
        g_cap = 100.0f;
        (void)p; g_value = 60.0f;
        g_show = 1.0f;
    }
    drive_segs();
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
        g_frame_node = 0;
        for (u32 i = 0; i < SEG_N; i++) { g_seg[i].bar = 0; g_seg[i].init = 0; }
        g_hud_dbg[0] = MARK | g_mp;
    } else if (id == 0) {
        if (a0 && *(u64 *)a0 == (u64)MAIN_SCHED_VT) hud_frame();
    }
}












