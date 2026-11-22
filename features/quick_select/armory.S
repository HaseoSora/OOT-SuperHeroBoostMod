/* Call-replacement wrappers for the armory drawer (tools/hook_sites.py BL_SITES).
 *
 * Each site is a `bl <stock>` in the game's item drawer code, patched to `bl <wrapper>`. The wrapper saves the
 * call's arguments in a BlCtx on the stack (features/quick_select/armory_drawer.c), with the caller's x19 / x20 /
 * x22 and frame pointer, then:
 *   1. armory_bl_pre(id, ctx) may change the arguments, the function to call (ctx->fn) or skip it (fn = 0, the
 *      result in ctx->ret);
 *   2. the function is called with the (possibly changed) arguments, its x0 stored in ctx->ret;
 *   3. armory_bl_post(id, ctx) runs after it;
 *   4. x0 = ctx->ret is returned to the site.
 * x19 / x20 / x22 / x29 are callee-saved, so the C code and the called function leave them as the caller had them. */

.macro BL_HOOK name, id, stock
    .global \name
    .type \name, %function
\name:
    sub sp, sp, #0xA0
    stp x29, x30, [sp]
    stp x0, x1, [sp, #0x10]
    stp x2, x3, [sp, #0x20]
    stp x4, x5, [sp, #0x30]
    stp x6, x7, [sp, #0x40]
    stp x8, x19, [sp, #0x50]
    str x20, [sp, #0x60]
    adrp x16, \stock
    add  x16, x16, :lo12:\stock
    str x16, [sp, #0x68]
    stp d0, d1, [sp, #0x70]
    stp d2, d3, [sp, #0x80]
    stp xzr, x22, [sp, #0x90]
    mov w0, #\id
    mov x1, sp
    bl  armory_bl_pre
    ldr x16, [sp, #0x68]
    cbz x16, 1f
    ldp x0, x1, [sp, #0x10]
    ldp x2, x3, [sp, #0x20]
    ldp x4, x5, [sp, #0x30]
    ldp x6, x7, [sp, #0x40]
    ldr x8, [sp, #0x50]
    ldp d0, d1, [sp, #0x70]
    ldp d2, d3, [sp, #0x80]
    blr x16
    str x0, [sp, #0x90]
    mov w0, #\id
    mov x1, sp
    bl  armory_bl_post
1:
    ldr x0, [sp, #0x90]
    ldp x29, x30, [sp]
    add sp, sp, #0xA0
    ret
    .size \name, . - \name
.endm

BL_HOOK hook_ad_open,    0, AD_SORT_RESTORE   /* drawer open: restores the sort option */
BL_HOOK hook_ad_cont,    1, AD_CONT_ITEMS     /* list build: the items' container */
BL_HOOK hook_ad_gdbool,  2, AD_GD_BOOL        /* list build: a GameData bool (sorted list) */
BL_HOOK hook_ad_record,  3, AD_RECORD         /* list build: an entry's record (category in x1) */
BL_HOOK hook_ad_filter,  4, AD_FILTER         /* list build: does an entry go in the list */
BL_HOOK hook_ad_cat0,    5, AD_CATEGORY       /* drawer: the container of a category (x1), at open */
BL_HOOK hook_ad_cat1,    6, AD_CATEGORY       /*   ... on a cursor move */
BL_HOOK hook_ad_cat2,    7, AD_CATEGORY
BL_HOOK hook_ad_cat3,    8, AD_CATEGORY
BL_HOOK hook_ad_decide0, 9, SLOTFN            /* drawer: put the item in the box (one path) */
BL_HOOK hook_ad_decide1, 10, hook_slot3       /*   ... (the release path; the slot hook otherwise) */
BL_HOOK hook_ad_icon,    11, AD_CELL_ICON     /* drawer: a cell's icon and count */
BL_HOOK hook_ad_sortlay, 12, AD_SORT_SHOW     /* drawer build: the layout holding the sort window */
BL_HOOK hook_ad_cellpos, 13, AD_PANE_MOVE     /* cell list layout: a cell's position */

/* The drawer's per-frame update (main+0x33C9270, was pacibsp; x0 = drawer). armory_update(drawer) returns 1 when it
 * did the frame itself (the armory grid): the stock update is skipped. Otherwise the stock function runs. */
    .global hook_ad_update
    .type hook_ad_update, %function
hook_ad_update:
    sub sp, sp, #0xA0
    stp x29, x30, [sp]
    stp x0, x1, [sp, #0x10]
    stp x2, x3, [sp, #0x20]
    stp x4, x5, [sp, #0x30]
    stp x6, x7, [sp, #0x40]
    str x8, [sp, #0x50]
    stp d0, d1, [sp, #0x60]
    stp d2, d3, [sp, #0x70]
    bl  armory_update
    mov w16, w0
    ldp x29, x30, [sp]
    ldp x0, x1, [sp, #0x10]
    ldp x2, x3, [sp, #0x20]
    ldp x4, x5, [sp, #0x30]
    ldp x6, x7, [sp, #0x40]
    ldr x8, [sp, #0x50]
    ldp d0, d1, [sp, #0x60]
    ldp d2, d3, [sp, #0x70]
    add sp, sp, #0xA0
    cbz w16, 1f
    ret
1:
    pacibsp
    b   AD_UPDATE_RESUME
    .size hook_ad_update, . - hook_ad_update
