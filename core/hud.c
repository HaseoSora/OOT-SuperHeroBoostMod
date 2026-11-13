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
#include "config.h"

typedef unsigned long long u64;
typedef unsigned char u8;

extern char MAIN_SCHED_VT[];
extern void *find_part(void *node, const char *name);
extern void *find_anim(void *part, const char *name);
extern void set_frame(void *anim, float frame);
extern void *memcpy(void *d, const void *s, unsigned long n);
extern long set_text(void *pane, const void *ref, int zero);   /* stock text-pane setter (main+0x439520) */
extern char GAMEDATA_MGR[];                                      /* main+0x4E842A8: GameData manager pointer slot */
extern char WORLD_MGR[];                                         /* main+0x4E7EAB0: world manager pointer slot */
int player_active(void);

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
#define PART_N 128   /* >1 does not work: only one appended part is built (see docs/RE-NOTES.md) */
#define APPEND_ALL 1   /* 1 = append every part (only the first one gets listed by the
                        * engine); 0 = parts 1.. repurpose filler parts (froze the game) */
#define SLOT_N 4
#ifndef SWAP_FILL
#define SWAP_FILL 1  /* 1 = replace the gauge's fill texture with a flat white one */
#endif

#define RING_SIZE 0.34f   /* whole-ring scale (part scale) */
#define SEG_N 128   /* ring segments = appended gauge parts */
static const char *part_replaces(u32 i);
/* names live in .data as char arrays (no pointer tables: the module has no relocations) */
static char g_pnames[SEG_N][16] = {"Pa_OotSeg_000", "Pa_OotSeg_001", "Pa_OotSeg_002", "Pa_OotSeg_003", "Pa_OotSeg_004", "Pa_OotSeg_005", "Pa_OotSeg_006", "Pa_OotSeg_007", "Pa_OotSeg_008", "Pa_OotSeg_009", "Pa_OotSeg_010", "Pa_OotSeg_011", "Pa_OotSeg_012", "Pa_OotSeg_013", "Pa_OotSeg_014", "Pa_OotSeg_015", "Pa_OotSeg_016", "Pa_OotSeg_017", "Pa_OotSeg_018", "Pa_OotSeg_019", "Pa_OotSeg_020", "Pa_OotSeg_021", "Pa_OotSeg_022", "Pa_OotSeg_023", "Pa_OotSeg_024", "Pa_OotSeg_025", "Pa_OotSeg_026", "Pa_OotSeg_027", "Pa_OotSeg_028", "Pa_OotSeg_029", "Pa_OotSeg_030", "Pa_OotSeg_031", "Pa_OotSeg_032", "Pa_OotSeg_033", "Pa_OotSeg_034", "Pa_OotSeg_035", "Pa_OotSeg_036", "Pa_OotSeg_037", "Pa_OotSeg_038", "Pa_OotSeg_039", "Pa_OotSeg_040", "Pa_OotSeg_041", "Pa_OotSeg_042", "Pa_OotSeg_043", "Pa_OotSeg_044", "Pa_OotSeg_045", "Pa_OotSeg_046", "Pa_OotSeg_047", "Pa_OotSeg_048", "Pa_OotSeg_049", "Pa_OotSeg_050", "Pa_OotSeg_051", "Pa_OotSeg_052", "Pa_OotSeg_053", "Pa_OotSeg_054", "Pa_OotSeg_055", "Pa_OotSeg_056", "Pa_OotSeg_057", "Pa_OotSeg_058", "Pa_OotSeg_059", "Pa_OotSeg_060", "Pa_OotSeg_061", "Pa_OotSeg_062", "Pa_OotSeg_063", "Pa_OotSeg_064", "Pa_OotSeg_065", "Pa_OotSeg_066", "Pa_OotSeg_067", "Pa_OotSeg_068", "Pa_OotSeg_069", "Pa_OotSeg_070", "Pa_OotSeg_071", "Pa_OotSeg_072", "Pa_OotSeg_073", "Pa_OotSeg_074", "Pa_OotSeg_075", "Pa_OotSeg_076", "Pa_OotSeg_077", "Pa_OotSeg_078", "Pa_OotSeg_079", "Pa_OotSeg_080", "Pa_OotSeg_081", "Pa_OotSeg_082", "Pa_OotSeg_083", "Pa_OotSeg_084", "Pa_OotSeg_085", "Pa_OotSeg_086", "Pa_OotSeg_087", "Pa_OotSeg_088", "Pa_OotSeg_089", "Pa_OotSeg_090", "Pa_OotSeg_091", "Pa_OotSeg_092", "Pa_OotSeg_093", "Pa_OotSeg_094", "Pa_OotSeg_095", "Pa_OotSeg_096", "Pa_OotSeg_097", "Pa_OotSeg_098", "Pa_OotSeg_099", "Pa_OotSeg_100", "Pa_OotSeg_101", "Pa_OotSeg_102", "Pa_OotSeg_103", "Pa_OotSeg_104", "Pa_OotSeg_105", "Pa_OotSeg_106", "Pa_OotSeg_107", "Pa_OotSeg_108", "Pa_OotSeg_109", "Pa_OotSeg_110", "Pa_OotSeg_111", "Pa_OotSeg_112", "Pa_OotSeg_113", "Pa_OotSeg_114", "Pa_OotSeg_115", "Pa_OotSeg_116", "Pa_OotSeg_117", "Pa_OotSeg_118", "Pa_OotSeg_119", "Pa_OotSeg_120", "Pa_OotSeg_121", "Pa_OotSeg_122", "Pa_OotSeg_123", "Pa_OotSeg_124", "Pa_OotSeg_125", "Pa_OotSeg_126", "Pa_OotSeg_127"};
static char g_anames[SEG_N][16] = {"PaOotSeg_000", "PaOotSeg_001", "PaOotSeg_002", "PaOotSeg_003", "PaOotSeg_004", "PaOotSeg_005", "PaOotSeg_006", "PaOotSeg_007", "PaOotSeg_008", "PaOotSeg_009", "PaOotSeg_010", "PaOotSeg_011", "PaOotSeg_012", "PaOotSeg_013", "PaOotSeg_014", "PaOotSeg_015", "PaOotSeg_016", "PaOotSeg_017", "PaOotSeg_018", "PaOotSeg_019", "PaOotSeg_020", "PaOotSeg_021", "PaOotSeg_022", "PaOotSeg_023", "PaOotSeg_024", "PaOotSeg_025", "PaOotSeg_026", "PaOotSeg_027", "PaOotSeg_028", "PaOotSeg_029", "PaOotSeg_030", "PaOotSeg_031", "PaOotSeg_032", "PaOotSeg_033", "PaOotSeg_034", "PaOotSeg_035", "PaOotSeg_036", "PaOotSeg_037", "PaOotSeg_038", "PaOotSeg_039", "PaOotSeg_040", "PaOotSeg_041", "PaOotSeg_042", "PaOotSeg_043", "PaOotSeg_044", "PaOotSeg_045", "PaOotSeg_046", "PaOotSeg_047", "PaOotSeg_048", "PaOotSeg_049", "PaOotSeg_050", "PaOotSeg_051", "PaOotSeg_052", "PaOotSeg_053", "PaOotSeg_054", "PaOotSeg_055", "PaOotSeg_056", "PaOotSeg_057", "PaOotSeg_058", "PaOotSeg_059", "PaOotSeg_060", "PaOotSeg_061", "PaOotSeg_062", "PaOotSeg_063", "PaOotSeg_064", "PaOotSeg_065", "PaOotSeg_066", "PaOotSeg_067", "PaOotSeg_068", "PaOotSeg_069", "PaOotSeg_070", "PaOotSeg_071", "PaOotSeg_072", "PaOotSeg_073", "PaOotSeg_074", "PaOotSeg_075", "PaOotSeg_076", "PaOotSeg_077", "PaOotSeg_078", "PaOotSeg_079", "PaOotSeg_080", "PaOotSeg_081", "PaOotSeg_082", "PaOotSeg_083", "PaOotSeg_084", "PaOotSeg_085", "PaOotSeg_086", "PaOotSeg_087", "PaOotSeg_088", "PaOotSeg_089", "PaOotSeg_090", "PaOotSeg_091", "PaOotSeg_092", "PaOotSeg_093", "PaOotSeg_094", "PaOotSeg_095", "PaOotSeg_096", "PaOotSeg_097", "PaOotSeg_098", "PaOotSeg_099", "PaOotSeg_100", "PaOotSeg_101", "PaOotSeg_102", "PaOotSeg_103", "PaOotSeg_104", "PaOotSeg_105", "PaOotSeg_106", "PaOotSeg_107", "PaOotSeg_108", "PaOotSeg_109", "PaOotSeg_110", "PaOotSeg_111", "PaOotSeg_112", "PaOotSeg_113", "PaOotSeg_114", "PaOotSeg_115", "PaOotSeg_116", "PaOotSeg_117", "PaOotSeg_118", "PaOotSeg_119", "PaOotSeg_120", "PaOotSeg_121", "PaOotSeg_122", "PaOotSeg_123", "PaOotSeg_124", "PaOotSeg_125", "PaOotSeg_126", "PaOotSeg_127"};
static const u64 g_phash[SEG_N] = {HASH_PART0, HASH_PART1, HASH_PART2, HASH_PART3, HASH_PART4, HASH_PART5, HASH_PART6, HASH_PART7, HASH_PART8, HASH_PART9, HASH_PART10, HASH_PART11, HASH_PART12, HASH_PART13, HASH_PART14, HASH_PART15, HASH_PART16, HASH_PART17, HASH_PART18, HASH_PART19, HASH_PART20, HASH_PART21, HASH_PART22, HASH_PART23, HASH_PART24, HASH_PART25, HASH_PART26, HASH_PART27, HASH_PART28, HASH_PART29, HASH_PART30, HASH_PART31, HASH_PART32, HASH_PART33, HASH_PART34, HASH_PART35, HASH_PART36, HASH_PART37, HASH_PART38, HASH_PART39, HASH_PART40, HASH_PART41, HASH_PART42, HASH_PART43, HASH_PART44, HASH_PART45, HASH_PART46, HASH_PART47, HASH_PART48, HASH_PART49, HASH_PART50, HASH_PART51, HASH_PART52, HASH_PART53, HASH_PART54, HASH_PART55, HASH_PART56, HASH_PART57, HASH_PART58, HASH_PART59, HASH_PART60, HASH_PART61, HASH_PART62, HASH_PART63, HASH_PART64, HASH_PART65, HASH_PART66, HASH_PART67, HASH_PART68, HASH_PART69, HASH_PART70, HASH_PART71, HASH_PART72, HASH_PART73, HASH_PART74, HASH_PART75, HASH_PART76, HASH_PART77, HASH_PART78, HASH_PART79, HASH_PART80, HASH_PART81, HASH_PART82, HASH_PART83, HASH_PART84, HASH_PART85, HASH_PART86, HASH_PART87, HASH_PART88, HASH_PART89, HASH_PART90, HASH_PART91, HASH_PART92, HASH_PART93, HASH_PART94, HASH_PART95, HASH_PART96, HASH_PART97, HASH_PART98, HASH_PART99, HASH_PART100, HASH_PART101, HASH_PART102, HASH_PART103, HASH_PART104, HASH_PART105, HASH_PART106, HASH_PART107, HASH_PART108, HASH_PART109, HASH_PART110, HASH_PART111, HASH_PART112, HASH_PART113, HASH_PART114, HASH_PART115, HASH_PART116, HASH_PART117, HASH_PART118, HASH_PART119, HASH_PART120, HASH_PART121, HASH_PART122, HASH_PART123, HASH_PART124, HASH_PART125, HASH_PART126, HASH_PART127};
#define PART_TOT PART_N
static const char *part_name(u32 i) { return g_pnames[i % SEG_N]; }
static u64 part_hash(u32 i) { return g_phash[i % SEG_N]; }
__attribute__((unused, noinline)) static const char *part_replaces(u32 i) { (void)i; return 0; }
static const char *asset_name(u32 i) { return g_anames[i % SEG_N]; }
/* ring centre: where Link usually stands on screen (layout units, root-relative, Y up;
 * ~0.356 px per unit at 720p). Placeholder until the ring follows his projected position. */
static const float g_part_x[1] = {250.0f};   /* beside Link (right), not on him */
static const float g_part_y[1] = {-300.0f};
static const float g_part_rgb[1][3] = {{0.30f, 0.85f, 0.25f}};   /* green */
#define CIRCLE_CAP 40.0f

/* -------- private allocation pool (bss, never freed) -------- */
static u8 g_pool[0x4C0000] __attribute__((aligned(16)));
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

/* ---- clock / rupee plates, drawn like the game's own number display ----
 * Text fields: 0 = clock, 1 = rupees (green), 2 = "/wallet" (white). Each field has two panes
 * (field f uses panes f and f + FLD_N): the text is written to the hidden one. */
#define FLD_N 3
#define TXT_N (FLD_N * 2)
static const char g_font_normal[] = "Normal";
static char g_tnames[TXT_N][16] = {"T_OotTxt_00", "T_OotTxt_01", "T_OotTxt_02", "T_OotTxt_03", "T_OotTxt_04", "T_OotTxt_05"};
static const u64 g_thash[TXT_N] = {HASH_TXT0, HASH_TXT1, HASH_TXT2, HASH_TXT3, HASH_TXT4, HASH_TXT5};
/* Picture panes. Each gets its own copy of the textured material of P_SubItemBg_00 with the game's
 * texture named below (all in the Common texture archive):
 *  0..3  clock plate:  fill, fill mirrored, edge, edge mirrored   (NumBaseSide_00 / _01, the plate of
 *  4..7  rupee plate:  same                                         the game's rupee counter)
 *  8     rupee icon    (Nt_RupeeIconNew_00, the game's green rupee)
 *  9     sun disc, 10..17 sun rays (Circle64_00 / White8_00_BC4L)
 *  18    moon disc, 19 moon shadow (both Circle64_00: a crescent) */
#define PIC_N 20
static char g_pinames[PIC_N][16] = {"P_OotPic_00", "P_OotPic_01", "P_OotPic_02", "P_OotPic_03", "P_OotPic_04",
                                     "P_OotPic_05", "P_OotPic_06", "P_OotPic_07", "P_OotPic_08", "P_OotPic_09",
                                     "P_OotPic_10", "P_OotPic_11", "P_OotPic_12", "P_OotPic_13", "P_OotPic_14",
                                     "P_OotPic_15", "P_OotPic_16", "P_OotPic_17", "P_OotPic_18", "P_OotPic_19"};
static const u64 g_pihash[PIC_N] = {HASH_PIC0, HASH_PIC1, HASH_PIC2, HASH_PIC3, HASH_PIC4, HASH_PIC5, HASH_PIC6,
                                    HASH_PIC7, HASH_PIC8, HASH_PIC9, HASH_PIC10, HASH_PIC11, HASH_PIC12, HASH_PIC13,
                                    HASH_PIC14, HASH_PIC15, HASH_PIC16, HASH_PIC17, HASH_PIC18, HASH_PIC19};
#define TEX_N 5
static char g_texn[TEX_N][24] = {"NumBaseSide_00", "NumBaseSide_01", "Nt_RupeeIconNew_00", "Circle64_00", "White8_00_BC4L"};
static const u8 g_pitex[PIC_N] = {0, 0, 1, 1, 0, 0, 1, 1, 2, 3, 4, 4, 4, 4, 4, 4, 4, 4, 3, 3};
/* pane sizes in layout units (scaled at runtime) */
static const float g_pic_w[PIC_N] = {1014, 1014, 1014, 1014, 1014, 1014, 1014, 1014, 120, 60, 9, 9, 9, 9, 9, 9, 9, 9, 76, 70};
static const float g_pic_h[PIC_N] = {160, 160, 160, 160, 160, 160, 160, 160, 120, 60, 26, 26, 26, 26, 26, 26, 26, 26, 76, 70};
/* layout units (root-relative, Y up) */
#define HUD_X (-1450.0f)
#define HUD_Y_CLOCK (-880.0f)
#define HUD_Y_RUPEE (-990.0f)
/* Look parameters (in .data so they can be tuned live with tools/hud_tune.py):
 *  0 plate centre x, 1 clock row y, 2 rupee row y, 3 plate scale x, 4 plate scale y,
 *  5 icon x (from the plate centre), 6 icon scale, 7 text x (from the plate centre), 8 text y offset,
 *  9 advance of one digit (text units), 10 fill alpha, 11 edge alpha, 12 sun ray radius,
 *  13 text scale, 14 moon shadow offset, 15 edge brightness, 16 icon override (0 by the hour, 1 sun, 2 moon),
 *  17 moon scale, 18 moon shadow scale, 19 moon shadow brightness (matches the plate)
 * Values tuned live against the look of the game's own rupee counter. */
float g_hudp[20] = {-1518.0f, -860.0f, -960.0f, 0.46f, 0.62f, -165.0f, 0.85f, 30.0f, 0.0f,
                    29.0f, 0.9f, 0.6f, 30.0f, 0.7f, 14.0f, 0.45f, 0.0f, 0.75f, 0.75f, 0.09f};
static int tbl_add(u8 *root, u32 off, const char *name, void *desc, u64 hash) {
    u32 n = w(root, off + 24);
    for (u32 j = 0; j < 3; j++) {
        u64 *a = pool_alloc((n + 1) * 8);
        if (!a) return 0;
        memcpy(a, (const void *)q(root, off + j * 8), n * 8);
        a[n] = j == 0 ? (u64)name : j == 1 ? (u64)desc : hash;
        *(u64 *)(root + off + j * 8) = (u64)a;
    }
    *(u32 *)(root + off + 24) = n + 1;
    return 1;
}

/* Materials: root+0x130 = {u64 *materials, u32 count, u32 stride}. A picture's material index is at +0x14 of its
 * entry in the picture/text list (+0x40). A textured material starts with a sampler list {u64 *samplers, count};
 * each sampler is {u32 flags, u32 pad, u64 texture name}. The texture is looked up by name in the layout
 * archive's texture file when the layout is built. This adds a deep copy of material `src` (its bytes up to the
 * next material, internal pointers rebased) whose first sampler names `tex`; returns its index or -1. */
static int add_material(u8 *root, const u8 *r, u32 src, const char *tex) {
    u32 n = w(root, 0x138), on = w(r, 0x138);
    const u64 *arr = (const u64 *)q(root, 0x130), *oarr = (const u64 *)q(r, 0x130);
    if (!arr || !oarr || src + 1 >= on || n > 256) return -1;
    u64 a = oarr[src], e = oarr[src + 1];
    if (e <= a || e - a > 0x400) return -1;
    u32 sz = (u32)(e - a);
    u8 *m = pool_clone((const void *)a, sz);
    u64 *na = pool_alloc((n + 1) * 8);
    if (!m || !na) return -1;
    for (u32 i = 0; i + 8 <= sz; i += 8) {
        u64 v = q(m, i);
        if (v >= a && v < e) *(u64 *)(m + i) = (u64)m + (v - a);
    }
    u64 sl = q(m, 0);
    if (sl < (u64)m || sl >= (u64)m + sz) return -1;
    u64 sp = *(u64 *)sl;
    if (sp < (u64)m || sp + 16 > (u64)m + sz) return -1;
    *(u64 *)(sp + 8) = (u64)tex;
    memcpy(na, arr, n * 8);
    na[n] = (u64)m;
    *(u64 *)(root + 0x130) = (u64)na;
    *(u32 *)(root + 0x138) = n + 1;
    return (int)n;
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
    u8 *cdk[PART_TOT], *pdk[PART_TOT];
    for (u32 k = 0; k < PART_TOT; k++) {
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
    *(u32 *)(first + 52) = nc + PART_TOT + PIC_N + TXT_N;
    for (u32 t = 0; t < 2; t++) {
        u32 off = t ? 0xC0 : 0x20, n = t ? np : nc;
        for (u32 j = 0; j < 3; j++) {
            u64 *a = pool_alloc((n + PART_TOT) * 8);
            if (!a) { g_hud_dbg[9] = MARK | 5; return 0; }
            memcpy(a, (const void *)q(r, off + j * 8), n * 8);
            for (u32 k = 0; k < PART_TOT; k++)
                a[n + k] = j == 0 ? (u64)part_name(k) : j == 1 ? (u64)(t ? pdk[k] : cdk[k]) : part_hash(k);
            if (!t && j == 1) a[0] = (u64)first;
            *(u64 *)(root + off + j * 8) = (u64)a;
        }
        *(u32 *)(root + off + 24) = n + PART_TOT;
    }
    /* TXT_N text panes (clock, rupees): clones of the stock T_Assign_01 text pane. A text pane is described in
     * three tables: the common pane list (+0x20, desc +0x3c = index in the picture/text list, +0x42 = index
     * in the text list), the picture/text list (+0x40) and the text list (+0x80). */
    {
        int ci = name_index(r, 0x20, "T_ShortCut_00"), bi = name_index(r, 0x40, "T_ShortCut_00"),
            ti = name_index(r, 0x80, "T_ShortCut_00");
        if (ci < 0 || bi < 0 || ti < 0) { g_hud_dbg[9] = MARK | 6; return 0; }
        u32 npane = nc + PART_TOT, nb = w(r, 0x58), nt = w(r, 0x98), np = w(r, 0x78);
        /* picture panes (plates): clones of the stock sub-item backing picture P_SubItemBg_00 */
        int pci = name_index(r, 0x20, "P_SubItemBg_00"), pbi = name_index(r, 0x40, "P_SubItemBg_00"),
            ppi = name_index(r, 0x60, "P_SubItemBg_00");
        if (pci < 0 || pbi < 0 || ppi < 0) { g_hud_dbg[9] = MARK | 6; return 0; }
        int mats[TEX_N];
        u32 src_mat = w((const void *)((const u64 *)q(r, 0x48))[pbi], 0x14);   /* P_SubItemBg_00's textured material */
        for (u32 t = 0; t < TEX_N; t++) {
            mats[t] = add_material(root, r, src_mat, g_texn[t]);
            if (mats[t] < 0) { g_hud_dbg[9] = MARK | 8; return 0; }
        }
        for (u32 k = 0; k < PIC_N; k++) {
            u8 *cd = pool_clone((const void *)((const u64 *)q(r, 0x28))[pci], 68);
            u8 *bd = pool_clone((const void *)((const u64 *)q(r, 0x48))[pbi], 0x88);
            u8 *pd = pool_clone((const void *)((const u64 *)q(r, 0x68))[ppi], 0x88);
            if (!cd || !bd || !pd) { g_hud_dbg[9] = MARK | 4; return 0; }
            *(u32 *)(bd + 0x14) = (u32)mats[g_pitex[k]];
            *(u32 *)(pd + 0x10) = nb + k;
            *(u32 *)(cd + 40) = 0;
            *(u32 *)(cd + 52) = npane + k + 1;
            *(float *)(cd + 0x10) = 0.0f; *(float *)(cd + 0x14) = 0.0f;   /* hidden until placed */
            *(float *)(cd + 28) = HUD_X;
            *(float *)(cd + 32) = HUD_Y_RUPEE;
            *(float *)(cd + 0x2C) = g_pic_w[k]; *(float *)(cd + 0x30) = g_pic_h[k];
            *(unsigned short *)(cd + 0x3c) = (unsigned short)(nb + k);
            /* like the stock picture: +0x40 = no extra-data entry (0xFFFF; any other value makes the engine search
             * a by-name list at that index on every lookup), +0x42 = index in the picture list */
            *(unsigned short *)(cd + 0x40) = 0xFFFF;
            *(unsigned short *)(cd + 0x42) = (unsigned short)(np + k);
            if (!tbl_add(root, 0x20, g_pinames[k], cd, g_pihash[k]) || !tbl_add(root, 0x40, g_pinames[k], bd, g_pihash[k]) ||
                !tbl_add(root, 0x60, g_pinames[k], pd, g_pihash[k])) { g_hud_dbg[9] = MARK | 5; return 0; }
        }
        npane += PIC_N; nb += PIC_N;
        for (u32 t = 0; t < TXT_N; t++) {
            u8 *cd = pool_clone((const void *)((const u64 *)q(r, 0x28))[ci], 68);
            u8 *bd = pool_clone((const void *)((const u64 *)q(r, 0x48))[bi], 0x88);
            u8 *td = pool_clone((const void *)((const u64 *)q(r, 0x88))[ti], 0xA8);
            if (!cd || !bd || !td) { g_hud_dbg[9] = MARK | 4; return 0; }
            /* the stock text panes use the button-glyph font "External_00": switch to the normal UI font */
            *(u64 *)(td + 0x00) = (u64)g_font_normal;
            *(u64 *)(td + 0x18) = q(td, 0x10);              /* default text: the empty string */
            *(float *)(td + 0x98) = 1500.0f;
            *(float *)(td + 0x08) = 64.0f; *(float *)(td + 0x0C) = 64.0f;
            *(float *)(cd + 0x2C) = 900.0f; *(float *)(cd + 0x30) = 90.0f;
            *(float *)(cd + 0x10) = 0.5f; *(float *)(cd + 0x14) = 0.5f;
            *(u32 *)(cd + 40) = 0;
            *(u32 *)(cd + 52) = npane + t + 1;
            *(float *)(cd + 28) = HUD_X + 40.0f;
            *(float *)(cd + 32) = (t % FLD_N) ? HUD_Y_RUPEE : HUD_Y_CLOCK;
            *(unsigned short *)(cd + 0x3c) = (unsigned short)(nb + t);
            *(unsigned short *)(cd + 0x42) = (unsigned short)(nt + t);
            if (!tbl_add(root, 0x20, g_tnames[t], cd, g_thash[t]) || !tbl_add(root, 0x40, g_tnames[t], bd, g_thash[t]) ||
                !tbl_add(root, 0x80, g_tnames[t], td, g_thash[t])) { g_hud_dbg[9] = MARK | 5; return 0; }
        }
    }
    {   /* per picture/text-list entry table (one int per entry of the +0x40 list; -1 = none): grow it */
        u32 oc = w(r, 0x210);
        const u8 *op = (const u8 *)q(r, 0x208);
        if (op && oc == w(r, 0x58)) {
            int *na = pool_alloc((oc + PIC_N + TXT_N) * 4);
            if (!na) { g_hud_dbg[9] = MARK | 5; return 0; }
            memcpy(na, op, oc * 4);
            for (u32 k = 0; k < PIC_N + TXT_N; k++) na[oc + k] = -1;
            *(u64 *)(root + 0x208) = (u64)na;
            *(u32 *)(root + 0x210) = oc + PIC_N + TXT_N;
        } else g_hud_dbg[9] = MARK | 7;
    }
    g_hud_dbg[6] += 1;
    return root;
}
/* -------- step 2: private copy of the gauge file, flat white tinted -------- */
static float *g_pal_a[SEG_N], *g_pal_b[SEG_N];   /* tint words of each private gauge copy */
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
    static const float YEL[3] = {1.0f, 0.85f, 0.10f};
    const float *c = k >= 64 ? YEL : g_part_rgb[0];   /* second set (k >= 64 = RING1_N + RING2_N) is yellow */
    float *a = (float *)(out + 0x74D8);
    if (a[0] == 1.0f && a[1] == 1.0f && a[2] == 1.0f && a[3] == 1.0f) { a[0] = c[0]; a[1] = c[1]; a[2] = c[2]; }
    float *b = (float *)(out + 0x74E8);
    if (b[1] > 0.5646f && b[1] < 0.5648f) { b[0] = c[0]; b[1] = c[1]; b[2] = c[2]; b[3] = 1.0f; }
    g_pal_a[k % SEG_N] = a;
    g_pal_b[k % SEG_N] = b;
    *(u64 *)(out + 0x110) = (u64)asset_name(k);
    g_hud_dbg[7] += 1;
    return out + 0xF8;
}

/* cache of replaced resources and the per-call config copies */
static struct { const u8 *src; u8 *copy; u32 kind; } g_res[140];
static u32 g_res_n;
static struct { void *handle; u8 config[0x100]; } g_calls[64];
static u32 g_calls_n;

u64 g_prep_dbg[20] = {1};   /* per part: handle, config, handle+0x28, handle+0x38 */

char g_pl[160][32] = {{1}};
u32 g_pl_n = 1;

void *hud_prepare(void *handle, u8 *config) {
    g_hud_dbg[8] += 1;
    const u8 *r = (const u8 *)q(config, 0);
    if (!r || w(r, 0) != 0x004C4955u) return config;   /* "UIL\0" */
    const char *asset = (const char *)q(r, 0x18);
    const char *inst = (const char *)q(handle, 0x30);
    if (inst && asset && g_pl_n < 160 && (str_eq(asset, "NumDisplay_00") || (asset[0] == 'P' && asset[1] == 'a' && asset[2] == 'N' && asset[3] == 'u') ||
                                         str_eq(asset, "PlayerStatus_00") || (asset[0] == 'N' && asset[1] == 'u'))) {
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
        if (g_res_n == 140) return config;
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
#define RING1_N 30
#define RING2_N 34
#define SET_N 64   /* segments per colour set */
#define RING_SX1 0.1951f
#define RING_SX2 0.2429f
#define BAR_T1 1.6f           /* main ring fill thickness factor (natural height 32) */
#define BAR_T2 1.0f           /* outer ring: thinner */
#define BORDER_W 12.0f       /* dark border, outward only (no black lines inside the ring) */
static const float OCT_X[64] = {58.53f, 82.20f, 102.28f, 117.89f, 128.34f, 133.19f, 132.21f, 125.46f, 113.22f, 96.04f, 74.66f, 50.01f, 23.18f, -4.67f, -32.31f, -58.53f, -82.20f, -102.28f, -117.89f, -128.34f, -133.19f, -132.21f, -125.46f, -113.22f, -96.04f, -74.66f, -50.01f, -23.18f, 4.67f, 32.31f, 72.87f, 106.47f, 136.44f, 161.77f, 181.59f, 195.22f, 202.21f, 202.30f, 195.52f, 182.07f, 162.42f, 137.24f, 107.39f, 73.88f, 37.85f, 0.54f, -36.79f, -72.87f, -106.47f, -136.44f, -161.77f, -181.59f, -195.22f, -202.21f, -202.30f, -195.52f, -182.07f, -162.42f, -137.24f, -107.39f, -73.88f, -37.85f, -0.54f, 36.79f};
static const float OCT_Y[64] = {120.00f, 105.21f, 85.82f, 62.68f, 36.80f, 9.31f, -18.59f, -45.67f, -70.76f, -92.75f, -110.69f, -123.80f, -131.49f, -133.43f, -129.55f, -120.00f, -105.21f, -85.82f, -62.68f, -36.80f, -9.31f, 18.59f, 45.67f, 70.76f, 92.75f, 110.69f, 123.80f, 131.49f, 133.43f, 129.55f, 189.60f, 172.98f, 150.47f, 122.84f, 91.02f, 56.11f, 19.28f, -18.20f, -55.07f, -90.06f, -121.98f, -149.74f, -172.41f, -189.21f, -199.56f, -203.12f, -199.76f, -189.60f, -172.98f, -150.47f, -122.84f, -91.02f, -56.11f, -19.28f, 18.20f, 55.07f, 90.06f, 121.98f, 149.74f, 172.41f, 189.21f, 199.56f, 203.12f, 199.76f};
static const float OCT_R[64] = {0.00000f, -0.20944f, -0.41888f, -0.62832f, -0.83776f, -1.04720f, -1.25664f, -1.46608f, -1.67552f, -1.88496f, -2.09440f, -2.30383f, -2.51327f, -2.72271f, -2.93215f, -3.14159f, -3.35103f, -3.56047f, -3.76991f, -3.97935f, -4.18879f, -4.39823f, -4.60767f, -4.81711f, -5.02655f, -5.23599f, -5.44543f, -5.65487f, -5.86431f, -6.07375f, 0.00000f, -0.18480f, -0.36960f, -0.55440f, -0.73920f, -0.92400f, -1.10880f, -1.29360f, -1.47840f, -1.66320f, -1.84800f, -2.03280f, -2.21759f, -2.40239f, -2.58719f, -2.77199f, -2.95679f, -3.14159f, -3.32639f, -3.51119f, -3.69599f, -3.88079f, -4.06559f, -4.25039f, -4.43519f, -4.61999f, -4.80479f, -4.98959f, -5.17439f, -5.35919f, -5.54399f, -5.72879f, -5.91359f, -6.09839f};
typedef struct { u64 bar, ratio, max, trace, layout_arr, part_pane; u32 init; float l_fill, l_show; } Seg;
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
        s->part_pane = pane_record(parent, part_name(k));
        s->l_fill = -1.0f; s->l_show = -1.0f;
        g_hud_dbg[2] = MARK | bar;
        ok++;
    }
    g_seg_ok = 0x10000000u + ok;
}

static u32 g_tired;
void hud_set_tired(u32 t) { g_tired = t; }

/* ---- world anchor: project Link (beside his chest) to the screen like the native 3D-anchored UI ----
 * Link: physics actor position f32[3] at actor+0x31C. Camera: view = [[[[CAMMGR]]+0x28]]+0x78 with
 * CAMMGR = main+0x4C86BC0; matrix f32[3][4] row-major at view+0x08 (row0 right, row1 up, row2 back,
 * translation in column 3; the camera looks along -row2). Layout units: 3596 x 2022 for 16:9. */
extern u64 g_link_actor;
static float g_anchor_x, g_anchor_y, g_anchor_s;
static u32 g_anchor_ok;
u32 g_anchor_dbg[6] = {0x10000000u};
#define ANCHOR_TAN_HALF_FOV 0.4663f   /* tan(25 deg): 50 deg vertical FOV */
#define ANCHOR_ASPECT 1.7778f
#define ANCHOR_SIDE 0.54f             /* metres to the camera's right of Link */
#define ANCHOR_HEIGHT 0.55f           /* metres above his feet */
#define ANCHOR_REF_DIST 4.0f          /* camera radius at which the ring has RING_SIZE */

static void anchor_update(void) {
    g_anchor_ok = 0;
    if (g_link_actor == 1) return;
    u64 base = (u64)MAIN_SCHED_VT - 0x4B05318ull;
    u64 slot = *(volatile u64 *)(base + 0x4C86BC0ull);
    if (!slot) return;
    u64 mgr = *(volatile u64 *)slot;
    if (!mgr) return;
    g_anchor_dbg[1] = *(volatile u32 *)(mgr + 0x20);
    if (*(volatile u32 *)(mgr + 0x20) == 0) return;
    u64 cams = *(volatile u64 *)(mgr + 0x28);
    if (!cams) return;
    u64 cam0 = *(volatile u64 *)cams;
    if (!cam0) return;
    u64 view = *(volatile u64 *)(cam0 + 0x78);
    if (!view) return;
    if (*(volatile u64 *)view != base + 0x4BF8A88ull) { g_anchor_dbg[2]++; return; }
    const volatile float *m = (const volatile float *)(view + 0x08);   /* rows at +0, +4, +8 floats (stride 4) */
    const volatile float *pos = (const volatile float *)(g_link_actor + 0x31C);
    float rx = m[0], ry = m[1], rz = m[2];
    float px = pos[0] + rx * ANCHOR_SIDE;
    float py = pos[1] + ANCHOR_HEIGHT + ry * ANCHOR_SIDE;
    float pz = pos[2] + rz * ANCHOR_SIDE;
    float xc = m[0] * px + m[1] * py + m[2] * pz + m[3];
    float yc = m[4] * px + m[5] * py + m[6] * pz + m[7];
    float zc = m[8] * px + m[9] * py + m[10] * pz + m[11];
    float d = -zc;
    g_anchor_dbg[3] = (u32)(int)(d * 100.0f);
    if (d < 0.3f || d > 60.0f) return;
    float nx = xc / (d * ANCHOR_TAN_HALF_FOV * ANCHOR_ASPECT);
    float ny = yc / (d * ANCHOR_TAN_HALF_FOV);
    if (nx < -1.3f || nx > 1.3f || ny < -1.3f || ny > 1.3f) return;
    g_anchor_x = nx * 1798.0f;
    g_anchor_y = ny * 1011.0f;
    float sc = RING_SIZE * (ANCHOR_REF_DIST / d);
    if (sc < 0.12f) sc = 0.12f;
    if (sc > 0.9f) sc = 0.9f;
    g_anchor_s = sc;
    g_anchor_ok = 1;
    g_anchor_dbg[0]++;
    g_anchor_dbg[4] = (u32)(int)(g_anchor_x);
    g_anchor_dbg[5] = (u32)(int)(g_anchor_y);
}
static void drive_segs(void) {
    /* main ring: first 75 stamina (RING1_N segments); outer ring: what the 4th..20th hearts add,
     * 2 segments per heart (RING2_N), only the segments the current hearts unlock are shown. */
    float v1 = g_value < 75.0f ? g_value : 75.0f;
    float lit1_all = v1 / 75.0f * (float)RING1_N;
    float per2 = 75.0f / (float)RING2_N;                       /* stamina per outer segment */
    int avail2 = (int)((g_cap - 75.0f) / per2 + 0.5f);
    if (avail2 < 0) avail2 = 0;
    if (avail2 > RING2_N) avail2 = RING2_N;
    float lit2_all = g_value > 75.0f ? (g_value - 75.0f) / per2 : 0.0f;
    for (u32 k = 0; k < SEG_N; k++) {
        Seg *s = &g_seg[k];
        if (!s->bar) continue;
        if (!s->init) {
            set_frame((void *)s->max, 100.0f);      /* bar width is fixed */
            set_frame((void *)s->ratio, 473.0f);    /* fill pose = sits on the base */
            set_frame((void *)s->trace, 473.0f);
            s->init = 1;
        }
        u32 idx = k % SET_N;
        u32 ring2 = idx >= RING1_N;
        u32 j = ring2 ? idx - RING1_N : idx;
        float lit = (ring2 ? lit2_all : lit1_all) - (float)j;   /* 0..1 = this segment's fill */
        if (lit < 0.0f) lit = 0.0f;
        if (lit > 1.0f) lit = 1.0f;
        int unlocked = !ring2 || (int)j < avail2;
        float show = (g_show > 0.5f && g_anchor_ok && unlocked && ((k >= SET_N) == (g_tired != 0))) ? 1.0f : 0.0f;
        if (s->part_pane && g_anchor_ok) {   /* the whole ring moves with Link */
            u64 pp = s->part_pane;
            *(float *)(pp + 0x60) = g_anchor_s;
            *(float *)(pp + 0x64) = g_anchor_s;
            *(float *)(pp + 0x6C) = g_anchor_x;
            *(float *)(pp + 0x70) = g_anchor_y;
            *(u32 *)pp |= 0x6F;
        }
        u64 arr = s->layout_arr;
        u64 c1 = arr + 1 * 0xB0;     /* container: bar tangent to its circle */
        *(float *)(c1 + 0x60) = show * (ring2 ? RING_SX2 : RING_SX1);
        *(float *)(c1 + 0x64) = show;
        *(float *)(c1 + 0x68) = OCT_R[idx];      /* radians, counter-clockwise positive */
        *(float *)(c1 + 0x6C) = OCT_X[idx];
        *(float *)(c1 + 0x70) = OCT_Y[idx];
        *(u32 *)c1 |= 0x6F;
        u64 f = arr + 17 * 0xB0;     /* fill */
        *(float *)(f + 0x60) = lit * 1.025f;   /* full fill = the base length (1.07 x 160) so no dark gaps at the joints */
        float bt = ring2 ? BAR_T2 : BAR_T1;
        *(float *)(f + 0x64) = bt;
        *(float *)(f + 0x6C) = -380.0f - 5.6f;
        *(float *)(f + 0x70) = 0.0f;
        *(u32 *)f |= 0x6F;
        /* dark base: as thick as the fill plus a border that only sticks out OUTWARD (+y), so it never
         * paints over the neighbouring lit segments inside the ring */
        for (u32 bi = 0; bi < 2; bi++) {
            u64 bp = arr + (u64)(11 + bi) * 0xB0;
            *(float *)(bp + 0x60) = show * 1.07f;
            *(float *)(bp + 0x64) = show * (bt * 32.0f + BORDER_W) / 32.0f;
            *(float *)(bp + 0x6C) = -380.0f - 5.6f;
            *(float *)(bp + 0x70) = BORDER_W * 0.5f;
            *(u32 *)bp |= 0x6F;
        }
        static const u32 HIDE[1] = {8};   /* gauge shadow window */
        u64 h = arr + (u64)HIDE[0] * 0xB0;
        *(float *)(h + 0x60) = 0.0f;
        *(float *)(h + 0x64) = 0.0f;
        *(u32 *)h |= 0x6F;
    }
}

/* ---- clock / rupee plates ---- */
u64 g_txt_dbg[8] = {MARK, MARK, MARK, MARK, MARK, MARK, MARK, MARK};
static char g_tbuf[TXT_N][16];      /* ASCII: the engine's text setter takes 8-bit text + byte length */
static char g_tlast[FLD_N][16];
static u32 g_tfront[FLD_N], g_tpend[FLD_N], g_twait[FLD_N];
/* Setting the text of a pane leaves it blank for a frame. Each field has two panes: the new text goes to the
 * hidden one, and after it has been drawn a few frames the two swap (shown = Y scale > 0, hidden = 0). */
static void tint_rec(u64 rec, float r, float g, float b, float a) {
    u64 obj = *(u64 *)(rec + 8);   /* pane object: RGBA tint as four floats at +0x20 */
    if (obj < 0x10000) return;
    float *c = (float *)(obj + 0x20);
    c[0] = r; c[1] = g; c[2] = b; c[3] = a;
}
static void place(u64 rec, float x, float y, float sx, float sy, float rot) {
    *(float *)(rec + 0x60) = sx; *(float *)(rec + 0x64) = sy; *(float *)(rec + 0x68) = rot;
    *(float *)(rec + 0x6C) = x; *(float *)(rec + 0x70) = y;
    *(u32 *)rec |= 0x6F;   /* mark the pane dirty */
}
/* field f: shown text at (x, y) in colour rgb; on = 0 hides both panes */
static void put_text(u64 frame, u32 f, const char *ascii, float x, float y, u32 on, const float *rgb) {
    u64 rf = pane_record(frame, g_tnames[f + FLD_N * g_tfront[f]]);
    u64 rb = pane_record(frame, g_tnames[f + FLD_N * (g_tfront[f] ^ 1)]);
    g_txt_dbg[f] = MARK | rf;
    if (!rf || !rb) return;
    float ts = g_hudp[13];
    tint_rec(rf, rgb[0], rgb[1], rgb[2], 1.0f);
    tint_rec(rb, rgb[0], rgb[1], rgb[2], 1.0f);
    if (g_tpend[f] && ++g_twait[f] >= 4) {   /* the hidden pane has drawn its new text: swap */
        u64 t = rf; rf = rb; rb = t;
        g_tfront[f] ^= 1; g_tpend[f] = 0;
    }
    place(rf, x, y, ts, on ? ts : 0.0f, 0.0f);
    place(rb, x, y, ts, 0.0f, 0.0f);
    if (g_tpend[f]) return;
    u32 n = 0;
    while (ascii[n] && n < 15) n++;
    int same = 1;
    for (u32 i = 0; i <= n; i++) if (g_tlast[f][i] != ascii[i]) same = 0;
    if (same) return;
    char *dst = g_tbuf[f + FLD_N * (g_tfront[f] ^ 1)];
    for (u32 i = 0; i < n; i++) dst[i] = ascii[i];
    dst[n] = 0;
    struct { const void *s; u32 len, z; long long m1; } ref = {dst, n, 0, -1};
    set_text((void *)rb, &ref, 0);
    g_tpend[f] = 1; g_twait[f] = 0;
    for (u32 i = 0; i <= n; i++) g_tlast[f][i] = ascii[i];
    g_txt_dbg[3 + f] += 1;
}
u32 g_clk_dbg[4];   /* 0 GameData seconds, 1 world-object seconds */
static int world_seconds(void) {
    /* GameData World_CurrentDateTime (UInt64 table k = 24, record 5, 0x30 bytes each, value at +0x20):
     * day count in the high 32 bits, seconds of the day in the low 32 bits. */
    int gd = -1, wo = -1;
    u64 mgr = *(u64 *)GAMEDATA_MGR;
    if (mgr) {
        u32 cnt = *(u32 *)(mgr + 8 + 0x60 * 24 + 8);
        u64 rec = *(u64 *)(mgr + 8 + 0x60 * 24 + 0x10);
        if (rec && cnt >= 6) gd = (int)(*(u64 *)(rec + 5 * 0x30 + 0x20) & 0xFFFFFFFFu);
    }
    /* the world clock object (same value, read through the game's own accessor) */
    u64 wm = *(u64 *)WORLD_MGR;
    u64 obj = wm ? *(u64 *)(wm + 0x578) : 0;
    if (obj) {
        typedef int (*fn_t)(u64);
        fn_t fn = (fn_t) * (u64 *)(*(u64 *)obj + 0x30);
        wo = fn(obj);
    }
    g_clk_dbg[0] = (u32)gd; g_clk_dbg[1] = (u32)wo;
    return wo >= 0 ? wo : gd;
}
static u32 put_int(char *p, int v) {
    char d[8]; u32 nd = 0, k = 0;
    if (v < 0) v = 0;
    if (v > 9999) v = 9999;
    for (;; v /= 10) { d[nd++] = (char)('0' + v % 10); if (v < 10) break; }
    while (nd) p[k++] = d[--nd];
    return k;
}
/* sun rays: unit directions every 45 degrees, clockwise from the top */
static const float RAY_DX[8] = {0.0f, 0.70711f, 1.0f, 0.70711f, 0.0f, -0.70711f, -1.0f, -0.70711f};
static const float RAY_DY[8] = {1.0f, 0.70711f, 0.0f, -0.70711f, -1.0f, -0.70711f, 0.0f, 0.70711f};
u32 g_hud_show[2] = {0x10000000u, 0x10000000u};   /* clock, rupees: 1 = drawn this frame */
static u64 g_pic_rec[PIC_N];
static u32 g_plates_shown;
/* the layout was rebuilt: drop cached pane records and force the texts to be set again */
static void plates_reset(void) {
    for (u32 k = 0; k < PIC_N; k++) g_pic_rec[k] = 0;
    for (u32 f = 0; f < FLD_N; f++) { g_tlast[f][0] = (char)0xFF; g_tpend[f] = 0; g_tfront[f] = 0; }
    g_plates_shown = 0;
}
static void plates_hide(u64 frame) {
    for (u32 k = 0; k < PIC_N; k++) place(g_pic_rec[k], g_hudp[0], g_hudp[2], 0.0f, 0.0f, 0.0f);
    for (u32 t = 0; t < TXT_N; t++) {
        u64 rec = pane_record(frame, g_tnames[t]);
        if (rec) place(rec, g_hudp[0], g_hudp[2], 0.0f, 0.0f, 0.0f);
    }
}
static void plates_update(u64 frame) {
    for (u32 k = 0; k < PIC_N; k++)
        if (!g_pic_rec[k]) g_pic_rec[k] = pane_record(frame, g_pinames[k]);
    for (u32 k = 0; k < PIC_N; k++) if (!g_pic_rec[k]) return;
    u32 active = player_active() != 0;
    u32 clk = active && g_ootcfg.hud_clock, rup = active && g_ootcfg.hud_rupees;
    /* outside gameplay (loading, menus, cutscenes) nothing is touched except hiding the plates once:
     * setting texts there costs the engine a slow lookup per call */
    if (!clk && !rup) {
        g_hud_show[0] = g_hud_show[1] = 0x10000000u;
        if (g_plates_shown) { plates_hide(frame); g_plates_shown = 0; }
        return;
    }
    g_plates_shown = 1;
    const float *P = g_hudp;
    int sec = clk ? world_seconds() : -1;
    if (sec < 0) clk = 0;
    g_hud_show[0] = 0x10000000u + clk; g_hud_show[1] = 0x10000000u + rup;
    /* plates: fill + edge, each drawn twice (mirrored) so both ends get the chevron */
    for (u32 row = 0; row < 2; row++) {
        u32 on = row ? rup : clk;
        float y = row ? P[2] : P[1];
        for (u32 j = 0; j < 4; j++) {
            u64 rec = g_pic_rec[row * 4 + j];
            float sx = P[3] * ((j & 1) ? -1.0f : 1.0f);
            place(rec, P[0], y, on ? sx : 0.0f, on ? P[4] : 0.0f, 0.0f);
            if (j < 2) tint_rec(rec, 0.0f, 0.0f, 0.0f, P[10]);
            else tint_rec(rec, P[15], P[15], P[15], P[11]);
        }
    }
    /* rupee icon */
    place(g_pic_rec[8], P[0] + P[5], P[2], rup ? P[6] : 0.0f, rup ? P[6] : 0.0f, 0.0f);
    tint_rec(g_pic_rec[8], 1.0f, 1.0f, 1.0f, 1.0f);
    /* sun (06:00-18:00) or moon */
    if (sec < 0) sec = 0;
    sec %= 86400;
    u32 day = sec >= 6 * 3600 && sec < 18 * 3600;
    if (P[16] > 0.5f) day = P[16] < 1.5f;
    u32 sun = clk && day, moon = clk && !day;
    float ix = P[0] + P[5], iy = P[1];
    static const float SUN[3] = {1.0f, 0.86f, 0.42f};
    place(g_pic_rec[9], ix, iy, sun ? 1.0f : 0.0f, sun ? 1.0f : 0.0f, 0.0f);
    tint_rec(g_pic_rec[9], SUN[0], SUN[1], SUN[2], 1.0f);
    for (u32 j = 0; j < 8; j++) {
        u64 rec = g_pic_rec[10 + j];
        /* the pane is turned clockwise by the ray's angle (rotation is counter-clockwise positive) */
        place(rec, ix + RAY_DX[j] * P[12], iy + RAY_DY[j] * P[12], sun ? 1.0f : 0.0f, sun ? 1.0f : 0.0f,
              -0.785398f * (float)j);
        tint_rec(rec, SUN[0], SUN[1], SUN[2], 1.0f);
    }
    /* crescent: a pale disc partly covered by a smaller disc in the plate's own colour, shifted up-right */
    float ms = moon ? P[17] : 0.0f, ss = moon ? P[18] : 0.0f;
    place(g_pic_rec[18], ix, iy, ms, ms, 0.0f);
    tint_rec(g_pic_rec[18], 0.97f, 0.93f, 0.72f, 1.0f);
    place(g_pic_rec[19], ix + P[14], iy + P[14] * 0.6f, ss, ss, 0.0f);
    tint_rec(g_pic_rec[19], P[19], P[19], P[19], 1.0f);

    static const float WHITE[3] = {1.0f, 1.0f, 1.0f};
    static const float GREEN[3] = {0.38f, 0.95f, 0.25f};
    /* text panes are centre-aligned: P[7] is the centre of the text area (right of the icon) */
    float tx = P[0] + P[7], ty = P[8];
    {   /* clock */
        char b[16]; u32 n = 0;
        int h = sec / 3600, m = (sec / 60) % 60, hh = h;
        if (!g_ootcfg.clock_24h) { hh = h % 12; if (!hh) hh = 12; }
        if (g_ootcfg.clock_24h || hh >= 10) b[n++] = (char)('0' + hh / 10);
        b[n++] = (char)('0' + hh % 10);
        b[n++] = ':'; b[n++] = (char)('0' + m / 10); b[n++] = (char)('0' + m % 10);
        if (!g_ootcfg.clock_24h) { b[n++] = ' '; b[n++] = h < 12 ? 'A' : 'P'; b[n++] = 'M'; }
        b[n] = 0;
        put_text(frame, 0, b, tx, P[1] + ty, clk, WHITE);
    }
    {   /* rupees: GameData Int table (k = 2), records 0x28 bytes, live value at +0x1C.
         * 962 = PlayerStatus.CurrentRupee, 976 = wallet capacity (member "Rupee" of the ammo/rupee caps). */
        int cur = 0, mx = 200;
        u64 mgr = *(u64 *)GAMEDATA_MGR;
        if (mgr) {
            u32 cnt = *(u32 *)(mgr + 8 + 0x60 * 2 + 8);
            u64 rec = *(u64 *)(mgr + 8 + 0x60 * 2 + 0x10);
            if (rec && cnt >= 977) { cur = *(int *)(rec + 962 * 0x28 + 0x1C); mx = *(int *)(rec + 976 * 0x28 + 0x1C); }
        }
        if (mx <= 0) mx = 200;
        char a[16], b[16];
        u32 na = put_int(a, cur), nb = 0;
        a[na] = 0;
        b[nb++] = '/';
        nb += put_int(b + nb, mx);
        b[nb] = 0;
        /* "1234/5000" centred on tx as a whole: green part and white part side by side (fixed digit advance;
        * ("/" is narrower than a digit: it counts as SLASH_W digits) */
        const float SLASH_W = 0.55f;
        float wa = (float)na, wb = (float)(nb - 1) + SLASH_W;
        float x0 = tx - P[9] * (wa + wb) * 0.5f;
        put_text(frame, 1, a, x0 + P[9] * wa * 0.5f, P[2] + ty, rup, GREEN);
        put_text(frame, 2, b, x0 + P[9] * (wa + wb * 0.5f), P[2] + ty, rup, WHITE);
    }
}
static void txt_update(u64 frame) {
    plates_update(frame);
}

u32 hud_frame_count(void) { return g_tick; }
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
    txt_update(g_frame_node);
    anchor_update();
    if (g_test_mode) {
        u32 p = (g_tick / 120) % 13;     /* demo sweep 0..100 until the game publishes */
        g_cap = 100.0f;
        (void)p; g_value = 60.0f;
        g_show = 1.0f;
        g_tired = (g_tick / 480) & 1;   /* demo: alternate green / yellow */
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

void player_track(u64 actor);
void player_guard_event(u32 id);
void hud_on_code(u32 id, void *a0, void *a1, void *a2, void *regs) {
    (void)a1; (void)a2;
    if (id == 5) { player_track((u64)a0); return; }
    if (id >= 6 && id <= 9) { player_guard_event(id); return; }
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
        plates_reset();
        g_hud_dbg[0] = MARK | g_mp;
    } else if (id == 0) {
        if (a0 && *(u64 *)a0 == (u64)MAIN_SCHED_VT) hud_frame();
    }
}












