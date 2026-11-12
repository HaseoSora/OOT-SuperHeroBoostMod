#ifndef OOT_MASTER_DISPATCH_H
#define OOT_MASTER_DISPATCH_H

typedef unsigned int u32;
typedef unsigned long long u64;

/* Handler signature. `site` is the hook id from tools/hook_sites.py.
 * For input sites a0/a1/a2 are the stock reader's arguments (a0 = HID samples,
 * a1 = sample count) and stock_result is its return value.
 * For slot sites the same registers are passed through unchanged.
 *
 * The handler list is NOT a table of function pointers: this NSO has no
 * relocations, so pointers stored in data would hold link addresses. The build
 * generates mod_on_input / mod_on_slot with direct calls instead
 * (build/native/dispatch_gen.c). */

#endif
