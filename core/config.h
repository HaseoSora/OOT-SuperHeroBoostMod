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
    unsigned char reserved[44];
} OotConfig;

extern volatile OotConfig g_ootcfg;

#endif
