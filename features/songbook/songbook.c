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
u32 g_songbook_armed;        /* frame when the song was selected */
u32 g_songbook_preview;      /* +0x220 when the ocarina opened (13 = none) */
u32 g_songbook_seen_page, g_songbook_seen_state, g_songbook_seen_busy;
u32 g_songbook_seen_arm, g_songbook_seen_at;
u32 g_songbook_enters;
u32 g_songbook_in_book;      /* the songbook page was shown since the last ocarina page */
u32 g_songbook_page;
u32 g_songbook_dbg[8] = {0x10000000u, 0x10000000u, 0x10000000u, 0x10000000u,
                         0x10000000u, 0x10000000u, 0x10000000u, 0x10000000u};

u32 hud_frame_count(void);

/* core/link.ld: the ocarina state machine. The game only calls it from page 0
 * when the melody is finished, so on the preview page we call it ourselves. */
extern void RES_OCARINA_UPDATE(void *ctx);

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
    u32 now = hud_frame_count();
    g_songbook_ctx = ctx;
    g_songbook_sel = sel;
    g_songbook_pending = sel;
    g_songbook_start = now + SONGBOOK_DELAY;
    g_songbook_armed = now;
    g_songbook_dbg[4]++;
}

static u32 read_preview(u64 ctx) {
    if (!valid_ptr(ctx)) return 13u;
    return *(volatile u32 *)(ctx + 0x220);
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

/* Temporary diagnostic shown on the clock plate: "A<arm> P<page>S<state>B<busy>". */
int songbook_debug_text(char *b, u32 cap) {
    (void)cap;
    u32 n = 0;
    /* runtime config bytes as the module sees them: clock24, songbook, hud_clock */
    b[n++] = 'C';
    n += put_u32(b + n, g_shbcfg.clock_24h);
    b[n++] = 'S';
    n += put_u32(b + n, g_shbcfg.songbook_enabled);
    b[n++] = 'H';
    n += put_u32(b + n, g_shbcfg.hud_clock);
    b[n] = 0;
    return 1;
}

/* Ocarina / songbook enter and leave (code hook ids 13/14). Leaving the
 * songbook must NOT drop the selection: the user releases ZL and the song is
 * played right after, on the ocarina page. */
void songbook_on_ocarina(u32 active, void *ctx) {
    u64 c = (u64)ctx;
    if (active) g_songbook_enters++;
    if (!valid_ptr(c)) return;
    g_songbook_ctx = c;
    g_songbook_active = active;
    g_songbook_sel = read_sel(c);

    u32 preview = read_preview(c);
    if (active) {
        g_songbook_preview = preview;          /* snapshot on ocarina open */
    } else if (preview != g_songbook_preview && preview < 12u && learned(c, preview)) {
        g_songbook_preview = preview;          /* song picked in the songbook */
        arm(c, preview);
    }
    g_songbook_dbg[0] = 0x10000000u + active;
    g_songbook_dbg[1] = (u32)(c & 0xFFFFFFFFu);
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

/* Per-frame hook (runs from the scheduler): the ocarina state machine is only
 * called when the "finished playing" flag is set, so we must set it from here. */
void songbook_on_frame(void) {
    if (!g_shbcfg.songbook_enabled) return;
    u64 ctx = g_songbook_ctx;
    if (!valid_ptr(ctx)) return;

    u32 now = hud_frame_count();
    if (g_songbook_active) {   /* snapshot for the debug plate while the HUD is hidden */
        g_songbook_seen_page = *(volatile u32 *)(ctx + 0x278);
        g_songbook_seen_state = *(volatile u32 *)(ctx + 0x230);
        g_songbook_seen_busy = *(volatile u32 *)(ctx + 0x114);
        g_songbook_seen_arm = g_songbook_dbg[4] - 0x10000000u;
        g_songbook_seen_at = now;
    }
    u32 page = *(volatile u32 *)(ctx + 0x278);
    g_songbook_page = page;

    if (page != 0u) {
        /* The songbook is being shown (ZL held). Remember it; when the ocarina
         * page comes back, play the song it left highlighted at +0x220. */
        g_songbook_in_book = 1;
        return;
    }
    if (g_songbook_in_book) {
        g_songbook_in_book = 0;
        u32 preview = read_preview(ctx);
        if (preview < 12u && learned(ctx, preview)) arm(ctx, preview);
    }

    u32 song_id = g_songbook_pending;
    if (song_id >= 12u) return;
    /* Do not wait forever: a selection only counts for a few seconds. */
    if (now - g_songbook_armed > 900u) {
        g_songbook_pending = NO_SONG;
        return;
    }
    if (now < g_songbook_start) return;

    u32 busy = *(volatile u32 *)(ctx + 0x114);
    if (busy != 0) return;

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
