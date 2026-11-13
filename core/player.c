#include "dispatch.h"

/* Finds Link from the per-frame movement update of physics actors (hook at main+0x2C215E0,
 * x0 = actor) and turns his action-state name into events.
 * Verified live: [actor+0x270] = component table; table+0x2B8 = Life component whose resource
 * (life+0x10 -> +0x58) is named "Player" for Link; table+0x358 = player component; the current
 * action-state name is an inline string at player+0x244 ("Wait", "Move", "Jump", "Land",
 * "Rolling", "SideStep", "SideStepLand", "CutS1", "ChargeWait", "LockOnWait", ...). */
typedef unsigned long long u64;
typedef unsigned int u32;
u64 g_link_actor = 1;
u64 g_link_player = 1;
u64 g_link_table = 1;
u32 g_link_seen = 0x10000000u;
int g_link_life = 0x7777;
int g_link_maxlife = 0;   /* max life in quarter hearts (Life+0x1C18 -> record, s32 at +8) */
static u32 g_active_frame;
static int g_alive;
u32 hud_frame_count(void);

/* events (bit mask), consumed by features through player_take_events() */
#define PEV_ROLL 1u
#define PEV_SIDESTEP 2u
#define PEV_JUMP 4u
#define PEV_ATTACK 8u
#define PEV_GUARDHIT 16u
#define PEV_SHOT 32u
#define PEV_BOOMERANG 64u
#define PEV_HAMMER 128u
#define PEV_BACKFLIP 256u
static u32 g_pending;
static char g_prev[24];
static char g_cur[24] = {'W', 'a', 'i', 't'};
static char g_prev2[24], g_cur2[24];   /* upper-body state name at player+0x34C (bow / slingshot) */
u32 g_ev_count[8] = {0x10000000u};
char g_names_seen[16][24] = {{1}};
u32 g_names_n;

static u64 rd(u64 p, unsigned off) { return *(volatile u64 *)(p + off); }

static int eq(const char *a, const char *b) {
    for (int i = 0; i < 24; i++) {
        if (a[i] != b[i]) return 0;
        if (!a[i]) return 1;
    }
    return 1;
}
static int has_hit(const char *a) {
    for (int i = 0; i < 20 && a[i]; i++) if (a[i] == 'H' && a[i + 1] == 'i' && a[i + 2] == 't') return 1;
    return 0;
}
static int starts(const char *a, const char *p) {
    for (int i = 0; p[i]; i++) if (a[i] != p[i]) return 0;
    return 1;
}

static void classify(const char *n) {
    if (eq(n, "Rolling")) g_pending |= PEV_ROLL;
    else if (starts(n, "CutHammer")) g_pending |= PEV_HAMMER;
    else if (starts(n, "BowShoot") || starts(n, "SlingShoot") || starts(n, "SlingshotShoot")) g_pending |= PEV_SHOT;
    else if (starts(n, "BoomerangThrow") || eq(n, "BoomerangSt")) g_pending |= PEV_BOOMERANG;
    else if (eq(n, "SideStep")) g_pending |= PEV_SIDESTEP;
    else if (starts(n, "BackFlip")) g_pending |= PEV_BACKFLIP;
    else if (eq(n, "Jump")) g_pending |= PEV_JUMP;
    else if (starts(n, "Guard") && has_hit(n)) g_pending |= PEV_GUARDHIT;
    else if (starts(n, "Cut") || starts(n, "ChargeAttack") || starts(n, "JumpCut") || starts(n, "Stab"))
        g_pending |= PEV_ATTACK;
}

void player_track(u64 actor) {
    if (!actor) return;
    u64 comp = rd(actor, 0x270);
    if (!comp) return;
    u64 life = rd(comp, 0x2B8);
    u64 pl = rd(comp, 0x358);
    if (!life || !pl) return;
    u64 res = rd(life, 0x10);
    if (!res) return;
    const char *n = (const char *)(res + 0x58);
    if (n[0] != 'P' || n[1] != 'l' || n[2] != 'a' || n[3] != 'y' || n[4] != 'e' || n[5] != 'r' || n[6]) return;
    g_link_actor = actor;
    g_link_table = comp;
    g_link_player = pl;
    g_link_seen++;
    g_active_frame = hud_frame_count();
    {   /* life: Life+0x1C10 -> record, value s32 at +8 (0 = dead) */
        u64 rec = rd(life, 0x1C10);
        if (rec) { g_link_life = *(volatile int *)(rec + 8); g_alive = g_link_life > 0; }
        u64 mrec = rd(life, 0x1C18);
        if (mrec) g_link_maxlife = *(volatile int *)(mrec + 8);
    }

    const volatile char *s = (const volatile char *)(pl + 0x244);
    for (int i = 0; i < 23; i++) g_cur[i] = s[i];
    g_cur[23] = 0;
    {   /* second (upper-body) name: BowCharge / BowShoot, also used by the slingshot */
        const volatile char *s2 = (const volatile char *)(pl + 0x34C);
        for (int i = 0; i < 23; i++) g_cur2[i] = s2[i];
        g_cur2[23] = 0;
        if (!eq(g_cur2, g_prev2)) {
            for (int i = 0; i < 24; i++) g_prev2[i] = g_cur2[i];
            classify(g_cur2);
        }
    }
    if (!eq(g_cur, g_prev)) {
        for (int i = 0; i < 24; i++) g_prev[i] = g_cur[i];
        classify(g_cur);
        /* log first distinct names seen (diagnostic) */
        int known = 0;
        for (u32 k = 1; k < g_names_n + 1 && k < 16; k++) if (eq(g_names_seen[k], g_cur)) known = 1;
        if (!known && g_names_n < 15) {
            g_names_n++;
            for (int i = 0; i < 24; i++) g_names_seen[g_names_n][i] = g_cur[i];
        }
    }
}

u64 player_get(void) { return g_link_player == 1 ? 0 : g_link_player; }

/* pending action events since the last call */
u32 player_take_events(void) {
    u32 e = g_pending;
    g_pending = 0;
    return e;
}
/* current action-state name equals / starts with */
int player_state_is(const char *name) { return eq(g_cur, name); }

/* 1 while Link exists, is alive and his update ran within the last frames (not in menus/pause) */
int player_active(void) {
    return g_alive && (hud_frame_count() - g_active_frame) <= 2;
}

int player_max_life(void) { return g_link_maxlife; }
