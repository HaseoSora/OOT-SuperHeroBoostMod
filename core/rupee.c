#include "dispatch.h"
#include "config.h"

typedef unsigned long long u64;
typedef unsigned int u32;
int player_active(void);
void show_ui(u64 ctl, int show);          /* stock: show/hide a UI object with its own animation (linker symbol) */

/* Always-visible rupee counter: the game's own numeric item display (the one that pops up when the wallet changes)
 * is kept open. Its update function (main+0x33C3B10, hooked) gives us the controller; while Link is in the world we
 * ask the stock show routine to open it. The "hide when idle" branch is removed by rupee.ips (only installed when
 * the option is on). */
u64 g_num_ctl;
u32 g_num_calls;
u32 g_num_dbg[8];     /* diagnostic: +0xd0 mode, +0xd4, +0xd8, +0x158, +0x160, +0x161 at the last call */

void rupee_update(u64 ctl) {
    g_num_ctl = ctl;
    g_num_calls++;
    const volatile unsigned char *b = (const volatile unsigned char *)ctl;
    g_num_dbg[0] = *(const volatile u32 *)(b + 0xd0);
    g_num_dbg[1] = *(const volatile u32 *)(b + 0xd4);
    g_num_dbg[2] = *(const volatile u32 *)(b + 0xd8);
    g_num_dbg[3] = b[0x158];
    g_num_dbg[4] = b[0x160];
    g_num_dbg[5] = b[0x161];
    if (g_ootcfg.hud_rupees && player_active()) show_ui(ctl, 1);
}
