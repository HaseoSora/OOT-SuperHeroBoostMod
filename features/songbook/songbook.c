/* Songbook: play a learned song by selecting it in the game's own songbook.
 *
 * The song list only previews a melody. We copy the selected song's notes into
 * the ocarina context (display buffer +0x158, matching buffer +0x478, ring
 * index +0x25C, count +0x250) and ask the game's own matcher whether the
 * sequence is a learned song. On a match we set the same "playing" state the
 * ocarina uses, so Link performs it and the effect fires (warp, sun, storm,
 * Epona...). Notes come from MelodyScoreBook, not from a guess.
 *
 * Only learned songs are used: the context keeps a byte flag per song at
 * +0x264 and the selected index at +0x22C. Index 12 (Scarecrow's Song, which
 * the player composes) is not handled.
 */
#include "../../core/dispatch.h"
#include "../../core/config.h"

/* MelodyScoreBook note hashes as stored in the ocarina buffers. */
#define NOTE_A 1423767502u
#define NOTE_X 825411668u
#define NOTE_Y 3433458314u
#define NOTE_L 1673550086u
#define NOTE_R 2552959238u

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

#define SONGBOOK_DELAY 20u
#define NO_SONG 0xFFu

u64 g_songbook_ctx = 1;
u32 g_songbook_active;
u32 g_songbook_sel = 0xFFFFFFFFu;
u32 g_songbook_pending = NO_SONG;
u32 g_songbook_start;
u32 g_songbook_preview;      /* +0x220 when the ocarina opened (13 = none) */
u32 g_songbook_page;
u32 g_songbook_dbg[8] = {0x10000000u, 0x10000000u, 0x10000000u, 0x10000000u,
                         0x10000000u, 0x10000000u, 0x10000000u, 0x10000000u};

u32 hud_frame_count(void);

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
    g_songbook_start = hud_frame_count() + SONGBOOK_DELAY;
    g_songbook_dbg[4]++;
}

static u32 read_preview(u64 ctx) {
    if (!valid_ptr(ctx)) return 13u;
    return *(volatile u32 *)(ctx + 0x220);
}

/* Ocarina enter/leave (code hook ids 13/14). */
void songbook_on_ocarina(u32 active, void *ctx) {
    g_songbook_ctx = (u64)ctx;
    g_songbook_active = active;
    g_songbook_sel = read_sel(g_songbook_ctx);
    g_songbook_preview = read_preview(g_songbook_ctx);
    g_songbook_pending = NO_SONG;
    g_songbook_dbg[0] = 0x10000000u + active;
    g_songbook_dbg[1] = (u32)(g_songbook_ctx & 0xFFFFFFFFu);
}

/* Store hook in the song list: the stock `str w20,[x19,#0x22c]`. */
void songbook_on_select(void *ctx, u32 sel) {
    if (!g_shbcfg.songbook_enabled) return;
    g_songbook_ctx = (u64)ctx;
    g_songbook_active = 1;
    if (sel < 12u && learned(g_songbook_ctx, sel)) arm((u64)ctx, sel);
}

/* Input poll: catches selections made without the store hook. No injection. */
void songbook_on_input(u32 site, void *a0, void *a1, void *a2, u32 stock_result) {
    (void)a0;
    (void)a1;
    (void)a2;
    (void)stock_result;
    if (!g_shbcfg.songbook_enabled || !g_songbook_active || site != 3) return;
    if (!valid_ptr(g_songbook_ctx)) return;

    u32 sel = read_sel(g_songbook_ctx);
    g_songbook_dbg[2] = 0x10000000u + sel;
    g_songbook_dbg[3] = 0x10000000u + (u32)learned(g_songbook_ctx, sel);
    if (sel < 12u && sel != g_songbook_sel && learned(g_songbook_ctx, sel)) arm(g_songbook_ctx, sel);
}

/* Ocarina update entry (code hook id 15): runs right before the state machine. */
void songbook_on_update(void *ctx_) {
    u64 ctx = (u64)ctx_;
    if (!g_shbcfg.songbook_enabled) return;
    if (!valid_ptr(ctx)) return;

    u32 song_id = g_songbook_pending;
    if (song_id >= 12u) {
        /* No store hook: use the song the preview stored at +0x220, but only if
         * it changed during this ocarina session (so a normal open stays quiet). */
        u32 preview = read_preview(ctx);
        if (preview == g_songbook_preview || preview >= 12u || !learned(ctx, preview)) return;
        song_id = preview;
        g_songbook_sel = preview;
        g_songbook_start = hud_frame_count();
    }
    if (hud_frame_count() < g_songbook_start) return;

    u32 busy = *(volatile u32 *)(ctx + 0x114);
    if (busy != 0) return;
    u32 page = *(volatile u32 *)(ctx + 0x278);
    g_songbook_page = page;
    /* The game calls this state machine only on page 0 (free play). */
    if (page != 0u) return;

    const Song *song = &g_songs[song_id];
    volatile u32 *shown = (volatile u32 *)(ctx + 0x158);
    volatile u32 *played = (volatile u32 *)(ctx + 0x478);
    for (u32 i = 0; i < 8u; i++) {
        shown[i] = song->notes[i];
        played[i] = song->notes[i];
    }
    *(volatile u32 *)(ctx + 0x250) = song->len;       /* notes played */
    *(volatile u32 *)(ctx + 0x25C) = song->len & 7u;  /* ring write index */

    /* Leave the context exactly as the ocarina does after the last note:
     * state 0x0A ("note added") and the "finished playing" flag. The game's own
     * update (which runs right after this hook) then matches the melody and
     * starts the performance. */
    *(volatile u32 *)(ctx + 0x230) = 0x0Au;
    *(volatile unsigned char *)(ctx + 0x26602) |= 1u;

    g_songbook_dbg[5]++;
    g_songbook_dbg[6] = 0x10001000u + page;
    g_songbook_dbg[7] = 0x10000000u + song_id;
    g_songbook_pending = NO_SONG;
    g_songbook_preview = song_id;   /* do not replay the same preview */
}
