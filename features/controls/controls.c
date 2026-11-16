/* Controls: optional button swaps that run before the other input features.
 *
 *  - target_r3: physical R3 and ZL are exchanged. R3 then holds (or toggles, per the game option)
 *    the target camera; ZL keeps R3's native function. The app recommends Hold targeting for this.
 *
 * Sprint on L3 is handled by the stamina feature (it sets the sprint flag without injecting A, so
 * Link does not roll). Only gameplay is touched: menus and loading screens keep their native buttons.
 */
#include "../../core/dispatch.h"
#include "../../core/hid.h"
#include "../../core/config.h"

#define CT_BTN_R3  0x0020ull
#define CT_BTN_ZL  0x0100ull

int player_dead(void);
int hud_ingame(void);

void controls_on_input(u32 site, void *a0, void *a1, void *a2, u32 stock_result) {
    (void)a2;
    if (site != 3 || !a0) return;
    if (!g_shbcfg.target_r3) return;
    u32 count = (u32)(unsigned long)a1;
    if (count == 0 || count > 64) count = stock_result;
    if (count == 0 || count > 64) return;
    /* Keep menus, pause and the game-over screen native. */
    if (player_dead() || !hud_ingame()) return;

    HidView view = {a0, count, 0};
    for (u32 i = 0; i < count; i++) {
        u64 b = hid_get_buttons(&view, i);
        u64 zl = b & CT_BTN_ZL, r3 = b & CT_BTN_R3;
        b &= ~(CT_BTN_ZL | CT_BTN_R3);
        if (r3) b |= CT_BTN_ZL;
        if (zl) b |= CT_BTN_R3;
        hid_set_buttons(&view, i, b);
    }
}
