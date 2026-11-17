/* Songbook: play a learned song by selecting it in the game's own songbook.
 *
 * The song list only previews a melody. We copy the selected song's notes into
 * the ocarina context (display buffer +0x158, matching buffer +0x478, ring
 * index +0x25C, count +0x250), mark state 0x0A and the "finished playing" flag
 * +0x26602 so the game's own state machine recognises the melody and fires the
 * song effect.
 *
 * The ocarina UI update (main+0x3292070) is the only place that receives the
 * real context every frame; its x0 is the ocarina context.
 *
 * Only learned songs are used: a byte flag per song at +0x264 and the preview
 * song at +0x220. Index 12 (Scarecrow's Song) is not handled.
 */
#include "../../core/dispatch.h"
#include "../../core/config.h"
#include "../../core/hid.h"

#define NOTE_MASK (BTN_A | BTN_X | BTN_Y | BTN_L | BTN_R)

/* MelodyScoreBook note hashes as stored in the ocarina buffers. */
#define NOTE_A 0x0Bu
#define NOTE_X 0x10u
#define NOTE_Y 0x0Du
#define NOTE_L 0x04u
#define NOTE_R 0x07u

typedef struct {
    unsigned char len;
    unsigned int notes[8];
} Song;

static const Song g_songs[12] = {
    {6, {NOTE_Y, NOTE_X, NOTE_A, NOTE_Y, NOTE_X, NOTE_A, 0, 0}},                  /* Lullaby */
    {6, {NOTE_X, NOTE_Y, NOTE_A, NOTE_X, NOTE_Y, NOTE_A, 0, 0}},                  /* Epona */
    {6, {NOTE_R, NOTE_A, NOTE_Y, NOTE_R, NOTE_A, NOTE_Y, 0, 0}},                  /* Saria */
    {6, {NOTE_A, NOTE_R, NOTE_X, NOTE_A, NOTE_R, NOTE_X, 0, 0}},                  /* Sun */
    {6, {NOTE_A, NOTE_L, NOTE_R, NOTE_A, NOTE_L, NOTE_R, 0, 0}},                  /* Time */
    {6, {NOTE_L, NOTE_R, NOTE_X, NOTE_L, NOTE_R, NOTE_X, 0, 0}},                  /* Storms */
    {6, {NOTE_L, NOTE_X, NOTE_Y, NOTE_A, NOTE_Y, NOTE_A, 0, 0}},                  /* Minuet */
    {8, {NOTE_R, NOTE_L, NOTE_R, NOTE_L, NOTE_A, NOTE_R, NOTE_A, NOTE_R}},        /* Bolero */
    {5, {NOTE_L, NOTE_R, NOTE_A, NOTE_A, NOTE_Y, 0, 0, 0}},                       /* Serenade */
    {6, {NOTE_L, NOTE_R, NOTE_L, NOTE_A, NOTE_R, NOTE_L, 0, 0}},                  /* Requiem */
    {7, {NOTE_Y, NOTE_A, NOTE_A, NOTE_L, NOTE_Y, NOTE_A, NOTE_R}},                /* Nocturne */
    {6, {NOTE_X, NOTE_A, NOTE_X, NOTE_A, NOTE_Y, NOTE_X, 0, 0}},                  /* Prelude */
};

#define SONGBOOK_DELAY 180u
#define NO_SONG 0xFFu

u64 g_songbook_ctx = 1;
u32 g_songbook_active;
u32 g_songbook_sel = 0xFFFFFFFFu;
u32 g_songbook_pending = NO_SONG;
u32 g_songbook_start;
u32 g_songbook_armed;
u32 g_songbook_preview;
u32 g_songbook_page;
u32 g_songbook_enters;
u32 g_songbook_inj_tick;
u32 g_songbook_last_ui;
u32 g_songbook_ui_tick;      /* ocarina UI frames (the HUD frame clock stops there) */
u32 g_songbook_seen_page, g_songbook_seen_state, g_songbook_seen_busy;
u32 g_songbook_seen_preview, g_songbook_seen_arm, g_songbook_seen_at;
u32 g_songbook_dbg[8] = {0x10000000u, 0x10000000u, 0x10000000u, 0x10000000u,
                         0x10000000u, 0x10000000u, 0x10000000u, 0x10000000u};

u32 hud_frame_count(void);

/* core/link.ld */
extern int RES_OCARINA_IS_OPEN(void *ctx);
extern void RES_OCARINA_UPDATE(void *ctx);
extern void RES_OCARINA_UPDATE(void *ctx);   /* same check the UI update does first */

static int valid_ptr(u64 p) { return p > 0x10000ull && p < 0x1000000000000ull; }

static u32 read_sel(u64 ctx) {
    if (!valid_ptr(ctx)) return 0xFFFFFFFFu;
    return *(volatile u32 *)(ctx + 0x22C);
}

static int learned(u64 ctx, u32 sel) {
    if (!valid_ptr(ctx) || sel >= 12u) return 0;
    return *(volatile unsigned char *)(ctx + 0x264 + sel) == 1;
}

static void arm(u64 ctx, u32 sel) {
    g_songbook_ctx = ctx;
    g_songbook_sel = sel;
    g_songbook_pending = sel;
    g_songbook_start = g_songbook_ui_tick + SONGBOOK_DELAY;
    g_songbook_armed = g_songbook_ui_tick;
    g_songbook_dbg[4]++;
}

/* Ocarina enter/leave (ids 13/14): only used to count/debug. The real context
 * comes from the UI update hook (id 16). */
void songbook_on_ocarina(u32 active, void *ctx) {
    (void)ctx;
    if (active) g_songbook_enters++;
    g_songbook_active = active;
    g_songbook_dbg[0] = 0x10000000u + active;
}

/* Store hook in the song list: the stock `str w20,[x19,#0x22c]`. */
void songbook_on_select(void *ctx, u32 sel) {
    if (!g_shbcfg.songbook_enabled) return;
    g_songbook_ctx = (u64)ctx;
    if (sel < 12u && learned(g_songbook_ctx, sel)) arm((u64)ctx, sel);
}

static u64 button_for_note(u32 code) {
    if (code == 0x0Bu) return BTN_A;
    if (code == 0x10u) return BTN_X;
    if (code == 0x0Du) return BTN_Y;
    if (code == 0x04u) return BTN_L;
    if (code == 0x07u) return BTN_R;
    return 0;
}

/* Input hook: detects selections and, once armed, plays the melody by pressing
 * the same note buttons the player would press (the path the game performs). */
void songbook_on_input(u32 site, void *a0, void *a1, void *a2, u32 stock_result) {
    (void)a2;
    if (!g_shbcfg.songbook_enabled || site != 3 || !a0) return;
    /* Only while the ocarina is open: its context is freed when it closes, and that memory is reused by other
     * menus (shops, dialogues, game over ...). Reading a "selection" there armed a song whose notes then took
     * A / X / Y / L / R away from the player in that menu until the melody was over. */
    if (!g_songbook_active) {
        g_songbook_pending = NO_SONG;
        g_songbook_inj_tick = 0;
        return;
    }
    u64 ctx = g_songbook_ctx;
    if (!valid_ptr(ctx)) return;

    u32 sel = read_sel(ctx);
    if (sel < 12u && sel != g_songbook_sel && learned(ctx, sel)) arm(ctx, sel);

    if (g_songbook_pending >= 12u) { g_songbook_inj_tick = 0; return; }
    u32 count = (u32)(unsigned long)a1;
    if (count == 0 || count > 64) count = stock_result;
    if (count == 0 || count > 64) return;

    u32 t = ++g_songbook_inj_tick;
    if (t < 150u) return;                       /* let the native preview finish */
    const Song *song = &g_songs[g_songbook_pending];
    u32 step = (t - 150u) / 7u, phase = (t - 150u) % 7u;
    if (step >= song->len) {
        g_songbook_pending = NO_SONG;
        g_songbook_inj_tick = 0;
        return;
    }
    u64 mask = phase < 3u ? button_for_note(song->notes[step]) : 0;
    HidView view = {a0, count, 0};
    for (u32 i = 0; i < count; i++) {
        u64 b = hid_get_buttons(&view, i);
        hid_set_buttons(&view, i, (b & ~NOTE_MASK) | mask);
    }
    g_songbook_dbg[5]++;
    g_songbook_dbg[7] = 0x10000000u + g_songbook_pending;
}

/* Ocarina UI update entry (code hook id 16): x0 is the real ocarina context. */
void songbook_on_ui(void *ctx_) {
    u64 ctx = (u64)ctx_;
    if (!g_shbcfg.songbook_enabled) return;
    if (!valid_ptr(ctx)) return;
    if (!RES_OCARINA_IS_OPEN((void *)ctx)) return;

    u32 now = hud_frame_count();
    u32 tick = ++g_songbook_ui_tick;
    u32 page = *(volatile u32 *)(ctx + 0x278);
    u32 state = *(volatile u32 *)(ctx + 0x230);
    u32 busy = *(volatile u32 *)(ctx + 0x114);
    u32 preview = *(volatile u32 *)(ctx + 0x220);

    g_songbook_ctx = ctx;
    g_songbook_active = 1;
    g_songbook_page = page;
    g_songbook_seen_page = page;
    g_songbook_seen_state = state;
    g_songbook_seen_busy = busy;
    g_songbook_seen_preview = preview;
    g_songbook_seen_arm = g_songbook_dbg[4] - 0x10000000u;
    g_songbook_seen_at = now;

    if (now - g_songbook_last_ui > 30u) {
        /* New ocarina session, but keep a song selected moments ago: the UI hook
         * is not called while the songbook is shown, so a gap is normal. */
        g_songbook_preview = preview;
        if (g_songbook_pending < 12u && now - g_songbook_armed > 900u)
            g_songbook_pending = NO_SONG;
    } else if (preview != g_songbook_preview) {
        g_songbook_preview = preview;
        if (preview < 12u && learned(ctx, preview)) arm(ctx, preview);
    }
    g_songbook_last_ui = now;

}

/* Per-frame hook: the ocarina UI update stops when the ocarina closes. */
void songbook_on_frame(void) {
    if (!g_shbcfg.songbook_enabled) return;
    u32 now = hud_frame_count();
    if (g_songbook_active && now - g_songbook_last_ui > 10u) g_songbook_active = 0;
}

static u32 put_u32(char *b, u32 v) {
    char t[12];
    u32 n = 0;
    do {
        t[n++] = (char)('0' + v % 10u);
        v /= 10u;
    } while (v);
    for (u32 i = 0; i < n; i++) b[i] = t[n - 1 - i];
    return n;
}
