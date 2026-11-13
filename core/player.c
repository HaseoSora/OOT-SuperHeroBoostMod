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
static char g_prev2[24], g_cur2[24];
static u32 g_combat_frame;   /* last frame a hostile enemy was near Link */   /* upper-body state name at player+0x34C (bow / slingshot) */
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
static int has_word(const char *a, const char *w) {
    for (int i = 0; i < 20 && a[i]; i++) { int k = 0; while (w[k] && a[i + k] == w[k]) k++; if (!w[k]) return 1; }
    return 0;
}
static int starts(const char *a, const char *p) {
    for (int i = 0; p[i]; i++) if (a[i] != p[i]) return 0;
    return 1;
}

u32 g_ev[5];   /* test counters: roll group, jump, attack, guard hit, shot (events seen, costed or not) */
/* A shield hit can be seen twice (the game's reaction node and the state name): one hit = one event. */
u32 g_guard_calls[4];          /* diagnostic: calls of each hooked reaction node */
static u32 g_guard_frame;
static void guard_hit(void) {
    u32 f = hud_frame_count();
    if (g_guard_frame && f - g_guard_frame < 40u) return;
    g_guard_frame = f ? f : 1;
    g_pending |= PEV_GUARDHIT;
    g_ev[3]++;
}
void player_guard_event(u32 id) { g_guard_calls[id - 6]++; guard_hit(); }
char g_guard_names[16][24];  /* diagnostic: every distinct state name that starts with "Guard" */
u32 g_guard_n;
static void classify(const char *n) {
    if (starts(n, "Guard") || starts(n, "Shield")) {
        int known = 0;
        for (u32 k = 0; k < g_guard_n && k < 16; k++) if (eq(g_guard_names[k], n)) known = 1;
        if (!known && g_guard_n < 16) { for (int i = 0; i < 24; i++) g_guard_names[g_guard_n][i] = n[i]; g_guard_n++; }
    }
    if (eq(n, "Rolling")) { g_pending |= PEV_ROLL; g_ev[0]++; }
    else if (starts(n, "CutHammer")) { g_pending |= PEV_HAMMER; g_ev[2]++; }
    else if (starts(n, "BowShoot") || starts(n, "SlingShoot") || starts(n, "SlingshotShoot")) { g_pending |= PEV_SHOT; g_ev[4]++; }
    else if (starts(n, "BoomerangThrow") || eq(n, "BoomerangSt")) { g_pending |= PEV_BOOMERANG; g_ev[2]++; }
    else if (eq(n, "SideStep")) { g_pending |= PEV_SIDESTEP; g_ev[0]++; }
    else if (starts(n, "BackFlip")) { g_pending |= PEV_BACKFLIP; g_ev[0]++; }
    else if (eq(n, "Jump")) { g_pending |= PEV_JUMP; g_ev[1]++; }
    else if (starts(n, "Guard") && (has_hit(n) || has_word(n, "Break") || has_word(n, "Reaction") || has_word(n, "Repel"))) guard_hit();
    else if (starts(n, "Cut") || starts(n, "ChargeAttack") || starts(n, "JumpCut") || starts(n, "Stab"))
        { g_pending |= PEV_ATTACK; g_ev[2]++; }
}

/* ---- combat = a hostile enemy close to Link ----
 * Every physics actor passes through player_track each frame. An actor whose Life resource is named
 * "Enemy_*" (friendly shopkeepers excluded), still alive, within ENEMY_RADIUS of Link marks combat;
 * the state then lasts 5 seconds after the last such enemy (grace, like the original design). */
#define ENEMY_RADIUS 10.0f
u32 g_enemy_dbg[4] = {0x10000000u};        /* enemies seen, close ones, ... */
float g_enemy_min2 = 1.0e8f;               /* squared distance of the nearest alive enemy seen (diagnostic) */
/* Awareness: an enemy counts as "fixed on Link" when it is within ENEMY_RADIUS and either already on top of him
 * (<= ENEMY_TOUCH) or has been getting closer during the last ENEMY_CHASE_FRAMES. Per-enemy memory (by actor
 * pointer) compares the squared distance over a short window. */
#define ENEMY_TOUCH 3.0f
#define ENEMY_CHASE_FRAMES 120u
#define ENEMY_WINDOW 6u
typedef struct { u64 actor; float d2; u32 stamp; u32 chase; } EnemyMem;
static EnemyMem g_em[24];
u32 g_enemy_chasing;       /* diagnostic: enemies currently counted as aware (last evaluation) */

static void enemy_check(u64 actor, u64 comp, u64 life, const char *n) {
    (void)comp;
    if (!(n[0] == 'E' && n[1] == 'n' && n[2] == 'e' && n[3] == 'm' && n[4] == 'y' && n[5] == '_')) return;
    if (starts(n, "Enemy_Scrub_Business")) return;          /* friendly shopkeeper */
    g_enemy_dbg[0]++;
    if (g_link_actor == 1) return;
    u64 rec = rd(life, 0x1C10);
    if (rec && *(volatile int *)(rec + 8) <= 0) return;      /* dead (ragdoll still updating) */
    const volatile float *e = (const volatile float *)(actor + 0x31C);
    const volatile float *l = (const volatile float *)(g_link_actor + 0x31C);
    float dx = e[0] - l[0], dy = e[1] - l[1], dz = e[2] - l[2];
    float d2 = dx * dx + dy * dy + dz * dz;
    if (d2 < g_enemy_min2) g_enemy_min2 = d2;
    if (d2 >= ENEMY_RADIUS * ENEMY_RADIUS) return;
    u32 f = hud_frame_count();
    EnemyMem *m = 0, *oldest = &g_em[0];
    for (int i = 0; i < 24; i++) {
        if (g_em[i].actor == actor) { m = &g_em[i]; break; }
        if (g_em[i].stamp < oldest->stamp) oldest = &g_em[i];
    }
    if (!m) { m = oldest; m->actor = actor; m->d2 = d2; m->stamp = f; m->chase = 0; }
    if (f - m->stamp >= ENEMY_WINDOW) {
        if (d2 < m->d2 - 0.4f) m->chase = f ? f : 1;   /* closer than a moment ago */
        m->d2 = d2;
        m->stamp = f;
    }
    int aware = d2 < ENEMY_TOUCH * ENEMY_TOUCH || (m->chase && f - m->chase < ENEMY_CHASE_FRAMES);
    if (aware) {
        g_enemy_dbg[1]++;
        g_combat_frame = f ? f : 1;
    }
}

void player_track(u64 actor) {
    if (!actor) return;
    u64 comp = rd(actor, 0x270);
    if (!comp) return;
    u64 life = rd(comp, 0x2B8);
    u64 pl = rd(comp, 0x358);
    if (!life) return;
    u64 res = rd(life, 0x10);
    if (!res) return;
    const char *n = (const char *)(res + 0x58);
    if (n[0] != 'P' || n[1] != 'l' || n[2] != 'a' || n[3] != 'y' || n[4] != 'e' || n[5] != 'r' || n[6]) {
        enemy_check(actor, comp, life, n);
        return;
    }
    if (!pl) return;
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

/* a hostile enemy was within ENEMY_RADIUS of Link in the last 5 seconds */
void player_mark_combat(void) { u32 f = hud_frame_count(); g_combat_frame = f ? f : 1; }

int player_in_combat(void) {
    return g_combat_frame != 0 && (hud_frame_count() - g_combat_frame) < 300u;
}
