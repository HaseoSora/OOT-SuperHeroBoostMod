/* Diagnostic entry counters for the wrappers in hooks.S.
 * Each wrapper does counter[id]++ before calling the stock function, so a value
 * above WRAP_BASE means the wrapper ran at least once in that build.
 * Stored in .data (file-backed, readable from the debug server). */
#define WRAP_BASE 0x10000000u

unsigned int g_wrap_entry[5] = {WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE};
unsigned int g_slot_entry[4] = {WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE};

/* Diagnostic: how many times each CODE_HOOK id ran (see core/hooks.S). */
unsigned int g_code_entry[32] = {
    WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE,
    WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE,
    WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE,
    WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE, WRAP_BASE,
};
