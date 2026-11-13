/* Input wrappers for the five stock controller-read sites.
 *
 * Each wrapper is transparent to the game:
 *   1. saves every register the AAPCS64 caller may rely on,
 *   2. calls the stock reader exactly once (its return values are kept),
 *   3. calls the C dispatcher mod_on_input(site, a0, a1, a2, stock_result),
 *   4. restores all registers and the stock return values, then returns.
 *
 * The handler list lives in C (dispatch.c / features_gen.c), so the wrappers do
 * not know which features exist. Site ids match tools/hook_sites.py.
 */

/* STOCK0..4 and SLOTFN are linker symbols (core/link.ld): a bl/b to an .equ
 * constant would assemble as a constant offset instead of a PC-relative one. */

/* WRAP_HOOK: transparent wrapper around a stock function. `dispatch` is the C
 * function that receives (id, a0, a1, a2, stock_result) after the stock call. */
.macro WRAP_HOOK name, id, stock, dispatch, counter, got, pre, stub
    .global \name
    .type \name, %function
\name:
    .ifnb \got
    /* Lazy-bound import: while its GOT slot still holds the PLT0 resolver, the
     * first call must come from main (the dynamic linker finds the caller's
     * module from LR; from our module it computes a bad target). Tail-call with
     * the game's own LR; handlers see the later, already-bound calls. */
    adrp x16, \got
    ldr  x17, [x16, :lo12:\got]
    adrp x16, PLT0
    add  x16, x16, :lo12:PLT0
    cmp  x17, x16
    b.ne 1f
    .ifnb \stub
    adrp x16, \got
    .endif
    b    \stock
1:
    .endif
    stp x29, x30, [sp, #-0x200]!
    stp x19, x20, [sp, #0x10]
    stp x21, x22, [sp, #0x20]
    stp x23, x24, [sp, #0x30]
    stp x25, x26, [sp, #0x40]
    stp x27, x28, [sp, #0x50]
    mov x19, x0
    mov x20, x1
    mov x21, x2
    /* entry counter (diagnostic): counter[\id]++ , uses only x16/x17 (scratch) */
    adrp x16, \counter
    add  x16, x16, :lo12:\counter + (4 * \id)
    ldr  w17, [x16]
    add  w17, w17, #1
    str  w17, [x16]
    .ifnb \pre
    /* pre-call hook: \pre(id, x0, x1, x2) returns the x2 to pass to the stock call */
    stp x0, x1, [sp, #0x60]
    stp x2, x3, [sp, #0x70]
    stp x4, x5, [sp, #0x80]
    stp x6, x7, [sp, #0x90]
    str x8, [sp, #0xA0]
    mov w0, #\id
    mov x1, x19
    mov x2, x20
    mov x3, x21
    bl  \pre
    mov x21, x0
    ldp x0, x1, [sp, #0x60]
    ldp x2, x3, [sp, #0x70]
    ldp x4, x5, [sp, #0x80]
    ldp x6, x7, [sp, #0x90]
    ldr x8, [sp, #0xA0]
    mov x2, x21
    .endif
    .ifnb \stub
    adrp x16, \got
    .endif
    bl  \stock
    stp x0, x1, [sp, #0x60]
    stp x2, x3, [sp, #0x70]
    stp x4, x5, [sp, #0x80]
    stp x6, x7, [sp, #0x90]
    str x8, [sp, #0xA0]
    stp x9, x10, [sp, #0xB0]
    stp x11, x12, [sp, #0xC0]
    stp x13, x14, [sp, #0xD0]
    stp x15, x16, [sp, #0xE0]
    stp x17, x18, [sp, #0xF0]
    stp d0, d1, [sp, #0x100]
    stp d2, d3, [sp, #0x110]
    stp d4, d5, [sp, #0x120]
    stp d6, d7, [sp, #0x130]
    stp d8, d9, [sp, #0x140]
    stp d10, d11, [sp, #0x150]
    stp d12, d13, [sp, #0x160]
    stp d14, d15, [sp, #0x170]
    stp d16, d17, [sp, #0x180]
    stp d18, d19, [sp, #0x190]
    stp d20, d21, [sp, #0x1A0]
    stp d22, d23, [sp, #0x1B0]
    stp d24, d25, [sp, #0x1C0]
    stp d26, d27, [sp, #0x1D0]
    stp d28, d29, [sp, #0x1E0]
    stp d30, d31, [sp, #0x1F0]
    mov w0, #\id
    mov x1, x19
    mov x2, x20
    mov x3, x21
    ldr w4, [sp, #0x60]
    bl  \dispatch
    ldp x0, x1, [sp, #0x60]
    ldp x2, x3, [sp, #0x70]
    ldp x4, x5, [sp, #0x80]
    ldp x6, x7, [sp, #0x90]
    ldr x8, [sp, #0xA0]
    ldp x9, x10, [sp, #0xB0]
    ldp x11, x12, [sp, #0xC0]
    ldp x13, x14, [sp, #0xD0]
    ldp x15, x16, [sp, #0xE0]
    ldp x17, x18, [sp, #0xF0]
    ldp d0, d1, [sp, #0x100]
    ldp d2, d3, [sp, #0x110]
    ldp d4, d5, [sp, #0x120]
    ldp d6, d7, [sp, #0x130]
    ldp d8, d9, [sp, #0x140]
    ldp d10, d11, [sp, #0x150]
    ldp d12, d13, [sp, #0x160]
    ldp d14, d15, [sp, #0x170]
    ldp d16, d17, [sp, #0x180]
    ldp d18, d19, [sp, #0x190]
    ldp d20, d21, [sp, #0x1A0]
    ldp d22, d23, [sp, #0x1B0]
    ldp d24, d25, [sp, #0x1C0]
    ldp d26, d27, [sp, #0x1D0]
    ldp d28, d29, [sp, #0x1E0]
    ldp d30, d31, [sp, #0x1F0]
    ldp x19, x20, [sp, #0x10]
    ldp x21, x22, [sp, #0x20]
    ldp x23, x24, [sp, #0x30]
    ldp x25, x26, [sp, #0x40]
    ldp x27, x28, [sp, #0x50]
    ldp x29, x30, [sp]
    add sp, sp, #0x200
    ret
    .size \name, . - \name
.endm

.macro INPUT_HOOK name, id, stock, got
    WRAP_HOOK \name, \id, \stock, mod_on_input, g_wrap_entry, \got
.endm

INPUT_HOOK hook_input0, 0, STOCK0, GOT0
INPUT_HOOK hook_input1, 1, STOCK1, GOT1
INPUT_HOOK hook_input2, 2, STOCK2, GOT2
INPUT_HOOK hook_input3, 3, STOCK3, GOT3
INPUT_HOOK hook_input4, 4, STOCK4, GOT4

/* Compat build: the five call sites belong to another mod (Classic), so patch the shared PLT stub
 * instead. Its first instruction (adrp x16, GOT3) becomes a branch here; the wrapper redoes the adrp
 * and enters the stub at +4 (STOCK3B). */
WRAP_HOOK hook_stub3, 3, STOCK3B, mod_on_input, g_wrap_entry, GOT3,, 1

/* Function-entry hooks: the patched instruction was `pacibsp`. Save everything,
 * call mod_on_code(id, x0, x1, x2), restore, run pacibsp, resume at site+4. */
.macro CODE_HOOK name, id, resume
    .global \name
    .type \name, %function
\name:
    sub sp, sp, #0x120
    stp x29, x30, [sp, #0x00]
    stp x0, x1, [sp, #0x10]
    stp x2, x3, [sp, #0x20]
    stp x4, x5, [sp, #0x30]
    stp x6, x7, [sp, #0x40]
    stp x8, x9, [sp, #0x50]
    stp x10, x11, [sp, #0x60]
    stp x12, x13, [sp, #0x70]
    stp x14, x15, [sp, #0x80]
    stp x16, x17, [sp, #0x90]
    stp x19, x20, [sp, #0xA0]
    stp d0, d1, [sp, #0xB0]
    stp d2, d3, [sp, #0xC0]
    stp d4, d5, [sp, #0xD0]
    stp d6, d7, [sp, #0xE0]
    mov x3, x2
    mov x2, x1
    mov x1, x0
    mov x4, sp                 /* saved registers: d0 at +0xB0, x0 at +0x10 ... */
    mov w0, #\id
    bl  mod_on_code
    ldp x29, x30, [sp, #0x00]
    ldp x0, x1, [sp, #0x10]
    ldp x2, x3, [sp, #0x20]
    ldp x4, x5, [sp, #0x30]
    ldp x6, x7, [sp, #0x40]
    ldp x8, x9, [sp, #0x50]
    ldp x10, x11, [sp, #0x60]
    ldp x12, x13, [sp, #0x70]
    ldp x14, x15, [sp, #0x80]
    ldp x16, x17, [sp, #0x90]
    ldp x19, x20, [sp, #0xA0]
    ldp d0, d1, [sp, #0xB0]
    ldp d2, d3, [sp, #0xC0]
    ldp d4, d5, [sp, #0xD0]
    ldp d6, d7, [sp, #0xE0]
    add sp, sp, #0x120
    pacibsp
    b   \resume
    .size \name, . - \name
.endm

/* UI resource build hook (main+0x43A6F8, was pacibsp): x0 = handle, x1 = config.
 * hud_prepare(handle, config) returns the config to use; it replaces x1. */
    .global hook_ui
    .type hook_ui, %function
hook_ui:
    sub sp, sp, #0x100
    stp x0, x1, [sp]
    stp x2, x3, [sp, #16]
    stp x4, x5, [sp, #32]
    stp x6, x7, [sp, #48]
    str x30, [sp, #64]
    stp q0, q1, [sp, #80]
    stp q2, q3, [sp, #112]
    stp q4, q5, [sp, #144]
    stp q6, q7, [sp, #176]
    bl  hud_prepare
    mov x16, x0
    ldp x0, x1, [sp]
    mov x1, x16
    ldp x2, x3, [sp, #16]
    ldp x4, x5, [sp, #32]
    ldp x6, x7, [sp, #48]
    ldr x30, [sp, #64]
    ldp q0, q1, [sp, #80]
    ldp q2, q3, [sp, #112]
    ldp q4, q5, [sp, #144]
    ldp q6, q7, [sp, #176]
    add sp, sp, #0x100
    pacibsp
    b   RES_UI
    .size hook_ui, . - hook_ui

CODE_HOOK hook_code_frame, 0, RES_FRAME
CODE_HOOK hook_code_mp, 1, RES_MP
CODE_HOOK hook_code_setframe, 3, RES_SETFRAME
CODE_HOOK hook_code_inst, 4, RES_INST
CODE_HOOK hook_code_move, 5, RES_MOVE
/* Link's shield-hit reaction nodes (ExecutePlayerReactionGuard enter/update, GuardJustRepelled, GuardBreak). */
CODE_HOOK hook_guard0, 6, RES_GUARD0
CODE_HOOK hook_guard1, 7, RES_GUARD1
CODE_HOOK hook_guard2, 8, RES_GUARD2
CODE_HOOK hook_guard3, 9, RES_GUARD3

/* Classic extra-button sites: four `bl 0x1211c00` calls. 0x1211c00 is a normal
 * function (not an import stub), so these use the same wrapper, with their own
 * dispatcher (mod_on_slot) and handler table. */
WRAP_HOOK hook_slot0, 0, SLOTFN, mod_on_slot, g_slot_entry,, mod_pre_slot
WRAP_HOOK hook_slot1, 1, SLOTFN, mod_on_slot, g_slot_entry,, mod_pre_slot
WRAP_HOOK hook_slot2, 2, SLOTFN, mod_on_slot, g_slot_entry,, mod_pre_slot
WRAP_HOOK hook_slot3, 3, SLOTFN, mod_on_slot, g_slot_entry,, mod_pre_slot

