#include "../../core/dispatch.h"

/* F1 probe: counts calls per input site. Changes nothing the game sees.
 * Site 3 is a tail call (hooks.S) and never reaches handlers. */
/* Non-zero base value so the counters live in .data (file-backed, readable
 * from the debug server like code). Live check subtracts PROBE_BASE. */
#define PROBE_BASE 0x10000000u
u32 g_probe_count[5] = {PROBE_BASE, PROBE_BASE, PROBE_BASE, PROBE_BASE, PROBE_BASE};

void probe_on_input(u32 site, void *a0, void *a1, void *a2, u32 stock_result) {
    (void)a0; (void)a1; (void)a2; (void)stock_result;
    if (site < 5) g_probe_count[site]++;
}
