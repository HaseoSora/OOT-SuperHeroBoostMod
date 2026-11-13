#ifndef OOT_CONFIG_H
#define OOT_CONFIG_H

/* Runtime configuration block. It lives in the module's .data (file-backed), so the companion app
 * can change it by patching bytes in the prebuilt subsdk9 (find the magic, write the fields) without
 * compiling anything. Layout is append-only: never reorder, bump `version` only on incompatible changes. */
typedef struct {
    unsigned char magic[8];        /* "OOTMCFG1" */
    unsigned int version;          /* 1 */
    unsigned int size;             /* sizeof(OotConfig) */
    unsigned char stamina_enabled; /* 0 = stamina system off (no costs, no bar, no locks) */
    unsigned char preset;          /* 0 hardcore, 1 combat only, 2 sprint only, 3 advanced */
    unsigned char cost_jump;       /* advanced: which actions cost stamina */
    unsigned char cost_attack;
    unsigned char cost_sprint;
    unsigned char cost_block;
    unsigned char cost_shoot;
    unsigned char cost_roll;
    unsigned char combat_only;     /* advanced: costs only while in combat */
    unsigned char classic_slots;   /* informational (the app decides which files to install) */
    /* v1 additions (append-only; older apps leave the defaults) */
    unsigned short enemy_hp_pct;   /* enemy health, percent of vanilla (100 = vanilla, 150 = Hero Core / Hero Mode) */
    unsigned short damage_taken_pct; /* damage Link receives, percent of vanilla (200 = Hero Mode) */
    unsigned char hud_rupees;      /* always-visible rupee counter */
    unsigned char hud_clock;       /* always-visible clock */
    unsigned char clock_24h;       /* clock in 24 h format */
    unsigned char no_heart_drop;   /* informational (done through a romfs file) */
    unsigned char reserved[36];
} OotConfig;

extern volatile OotConfig g_ootcfg;

#endif
