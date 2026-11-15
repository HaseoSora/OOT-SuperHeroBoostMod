#ifndef SHB_CONFIG_H
#define SHB_CONFIG_H

/* Runtime configuration block. It lives in the module's .data (file-backed), so the companion app
 * can change it by patching bytes in the prebuilt subsdk9 (find the magic, write the fields) without
 * compiling anything. Layout is append-only: never reorder, bump `version` only on incompatible changes. */
typedef struct {
    unsigned char magic[8];        /* "SHBCFG01" */
    unsigned int version;          /* 1 */
    unsigned int size;             /* sizeof(ShbConfig) */
    unsigned char stamina_enabled; /* 0 = stamina system off (no costs, no bar, no locks) */
    unsigned char preset;          /* 0 hardcore, 1 combat only, 2 sprint only, 3 advanced */
    unsigned char cost_jump;       /* advanced: which actions cost stamina */
    unsigned char cost_attack;
    unsigned char cost_sprint;
    unsigned char cost_block;
    unsigned char cost_shoot;
    unsigned char cost_roll;
    unsigned char combat_only;     /* advanced: costs only while in combat */
    unsigned char unused_09;       /* reserved legacy flag; always 0 */
    /* v1 additions (append-only; older apps leave the defaults) */
    unsigned short enemy_hp_pct;   /* enemy health, percent of vanilla (100 = vanilla, 150 = Hero Mode) */
    unsigned short damage_taken_pct; /* damage the player receives, percent of vanilla (200 = Hero Mode) */
    unsigned char hud_rupees;      /* always-visible rupee counter */
    unsigned char hud_clock;       /* always-visible clock */
    unsigned char clock_24h;       /* clock in 24 h format */
    unsigned char no_heart_drop;   /* informational (done through a romfs file) */
    unsigned short sprint_speed_pct; /* sprint (A held while moving) speed, percent of vanilla (100 = vanilla, default 125) */
    unsigned char songbook_enabled;  /* play a learned song by selecting it in the native songbook */
    unsigned char button_mapping;    /* buttonMapping: our own item buttons B / L / R / ZR on the HUD */
    unsigned char button_style;      /* buttonMapping buttons: 0 Switch, 1 Xbox, 2 PlayStation */
    unsigned char bm_simple;         /* buttonMapping simple layout: only the assignable buttons (no B / A / X / Y) */
    unsigned char bm_l_mode;         /* buttonMapping L: 0 assignable, 2 the game's item selector */
    unsigned char quick_boots;       /* hold D-pad down to pick the boots */
    unsigned char quick_mask;        /* hold D-pad up to pick a mask */
    unsigned char hud_collectibles; /* per-area Skulltula / heart-piece counter */
    signed short hud_x[4];          /* installer: x of the rupee, clock, skull and heart blocks (-32768 = off) */
    unsigned char reserved[18];
} ShbConfig;

extern volatile ShbConfig g_shbcfg;

#endif
