/* Songbook: play a learned song by selecting it in the game's own songbook.
 *
 * The native songbook is the one opened with ZL / the pause-menu song list.
 * We do not call the game's internal playback routines: we inject the five
 * ocarina note buttons for the selected melody. The game recognises the song
 * with its normal note logic, so the animation, sound and effects stay native.
 *
 * Only learned songs are used: the context keeps a byte flag per song at
 * +0x264 and the selected index at +0x22c. If the selected index is 12
 * (Scarecrow's Song, which the player composes) nothing is injected.
 */
#include "../../core/dispatch.h"
#include "../../core/hid.h"
#include "../../core/config.h"

#define NOTE_MASK (BTN_A | BTN_X | BTN_Y | BTN_L | BTN_R)

typedef struct {
    unsigned char len;
    unsigned char notes[8];   /* values are HID button bits */
} Song;

/* MelodyScoreBook order (GameParameter/MelodyScoreBook), translated with the
 * remake's five note buttons: L, R, A, Y, X. */
static const Song g_songs[12] = {
    {6, {BTN_Y, BTN_X, BTN_A, BTN_Y, BTN_X, BTN_A}},                  /* Zelda's Lullaby */
    {6, {BTN_X, BTN_Y, BTN_A, BTN_X, BTN_Y, BTN_A}},                  /* Epona's Song */
    {6, {BTN_R, BTN_A, BTN_Y, BTN_R, BTN_A, BTN_Y}},                  /* Saria's Song */
    {6, {BTN_A, BTN_R, BTN_X, BTN_A, BTN_R, BTN_X}},                  /* Sun's Song */
    {6, {BTN_A, BTN_L, BTN_R, BTN_A, BTN_L, BTN_R}},                  /* Song of Time */
    {6, {BTN_L, BTN_R, BTN_X, BTN_L, BTN_R, BTN_X}},                  /* Song of Storms */
    {6, {BTN_L, BTN_X, BTN_Y, BTN_A, BTN_Y, BTN_A}},                  /* Minuet of Forest */
    {8, {BTN_R, BTN_L, BTN_R, BTN_L, BTN_A, BTN_R, BTN_A, BTN_R}},    /* Bolero of Fire */
    {5, {BTN_L, BTN_R, BTN_A, BTN_A, BTN_Y}},                         /* Serenade of Water */
    {6, {BTN_L, BTN_R, BTN_L, BTN_A, BTN_R, BTN_L}},                  /* Requiem of Spirit */
    {7, {BTN_Y, BTN_A, BTN_A, BTN_L, BTN_Y, BTN_A, BTN_R}},           /* Nocturne of Shadow */
    {6, {BTN_X, BTN_A, BTN_X, BTN_A, BTN_Y, BTN_X}},                  /* Prelude of Light */
};

#define SONGBOOK_DELAY 20u
#define NOTE_HOLD 3u
#define NOTE_GAP 4u
#define NOTE_STEP (NOTE_HOLD + NOTE_GAP)
#define NO_SONG 0xFFu

u64 g_songbook_ctx = 1;
u32 g_songbook_active;
u32 g_songbook_sel = 0xFFFFFFFFu;
u32 g_songbook_pending = NO_SONG;
u32 g_songbook_tick;
u32 g_songbook_frame;
u32 g_songbook_start;
u32 g_songbook_page;
u32 g_songbook_dbg[8] = {0x10000000u, 0x10000000u, 0x10000000u, 0x10000000u,
                         0x10000000u, 0x10000000u, 0x10000000u, 0x10000000u};

u32 hud_frame_count(void);
int player_active(void);

static int valid_ptr(u64 p) { return p > 0x10000ull && p < 0x1000000000000ull; }

static u32 read_sel(u64 ctx) {
    if (!valid_ptr(ctx)) return 0xFFFFFFFFu;
    return *(volatile u32 *)(ctx + 0x22C);
}

static int learned(u64 ctx, u32 sel) {
    if (!valid_ptr(ctx) || sel >= 12u) return 0;
    return *(volatile unsigned char *)(ctx + 0x264 + sel) == 1;
}

static int play_ready(u64 ctx) {
    if (!valid_ptr(ctx)) return 0;
    u32 state = *(volatile u32 *)(ctx + 0x230);
    u32 busy = *(volatile u32 *)(ctx + 0x114);
    return (state & ~2u) == 1u && busy == 0;
}

/* Called from the ocarina enter/leave function-entry hooks (ids 13/14). */
void songbook_on_ocarina(u32 active, void *ctx) {
    g_songbook_ctx = (u64)ctx;
    g_songbook_active = active;
    g_songbook_sel = read_sel(g_songbook_ctx);
    g_songbook_pending = NO_SONG;
    g_songbook_tick = 0;
    g_songbook_start = 0;
    g_songbook_dbg[0] = 0x10000000u + active;
    g_songbook_dbg[1] = (u32)(g_songbook_ctx & 0xFFFFFFFFu);
}

/* Called from the store hook just before the songbook writes the selected index. */
void songbook_on_select(void *ctx, u32 sel) {
    if (!g_shbcfg.songbook_enabled) return;
    g_songbook_ctx = (u64)ctx;
    g_songbook_active = 1;
    if (sel < 12u && learned(g_songbook_ctx, sel)) {
        g_songbook_sel = sel;
        g_songbook_pending = sel;
        g_songbook_tick = 0;
        g_songbook_start = hud_frame_count() + SONGBOOK_DELAY;
        g_songbook_dbg[4]++;
    }
}

void songbook_on_input(u32 site, void *a0, void *a1, void *a2, u32 stock_result) {
    (void)a2;
    if (!g_shbcfg.songbook_enabled || !g_songbook_active || site != 3 || !a0) return;
    if (!valid_ptr(g_songbook_ctx)) return;

    u32 sel = read_sel(g_songbook_ctx);
    g_songbook_dbg[2] = 0x10000000u + sel;
    g_songbook_dbg[3] = 0x10000000u + (u32)learned(g_songbook_ctx, sel);
    if (sel < 12u && learned(g_songbook_ctx, sel) && sel != g_songbook_sel) {
        g_songbook_sel = sel;
        g_songbook_pending = sel;
        g_songbook_tick = 0;
        g_songbook_start = hud_frame_count() + SONGBOOK_DELAY;
        g_songbook_dbg[4]++;
    }
    if (g_songbook_pending >= 12u) return;
    g_songbook_page = *(volatile u32 *)(g_songbook_ctx + 0x278);
    /* Page 0 is the free-play ocarina; pages 1/2 are the song list/detail. */
    if (g_songbook_page != 0 || !play_ready(g_songbook_ctx)) return;

    u32 now = hud_frame_count();
    if (now < g_songbook_start) return;
    if (now != g_songbook_frame) {
        g_songbook_frame = now;
        g_songbook_tick++;
        g_songbook_dbg[5]++;
    }

    const Song *song = &g_songs[g_songbook_pending];
    u32 step = (g_songbook_tick - 1) / NOTE_STEP;
    if (step >= song->len) {
        g_songbook_pending = NO_SONG;
        g_songbook_tick = 0;
        g_songbook_dbg[6]++;
        return;
    }
    u32 phase = (g_songbook_tick - 1) % NOTE_STEP;
    u64 mask = phase < NOTE_HOLD ? (u64)song->notes[step] : 0;

    u32 count = (u32)(unsigned long)a1;
    if (count == 0 || count > 64) count = stock_result;
    if (count == 0 || count > 64) return;
    HidView view = {a0, count, 0};
    for (u32 i = 0; i < count; i++) {
        u64 b = hid_get_buttons(&view, i);
        hid_set_buttons(&view, i, (b & ~NOTE_MASK) | mask);
    }
    g_songbook_dbg[7] = 0x10000000u + (u32)(g_songbook_tick & 0xFFu);
}
