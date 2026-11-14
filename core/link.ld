/* Linker script for our own subsdk9 module.
 * Placed right after subsdk0 in the stock module order.
 * All MOD0 offsets are computed here from real section addresses. */
ENTRY(_start)

__base = 0x4F80000;

SECTIONS
{
    . = __base;
    .text : ALIGN(0x1000) { *(.module) *(.text*) }
    .rodata : ALIGN(0x1000) { *(.rodata*) }
    .data : ALIGN(0x1000) {
        __dynamic_start = .;
        KEEP(*(.dynamic))
        *(.data*)
    }
    .bss : ALIGN(0x1000) {
        __bss_start = .;
        *(.bss*) *(COMMON)
        . = ALIGN(16);
        __module_object = .;
        . = . + 0x200;
        __bss_end = .;
    }

    /* main-relative addresses of the lazy-PLT0 resolver and the input stubs'
     * GOT slots (used by core/hooks.S; adrp needs a symbol, not an .equ). */
    STOCK0 = 0x3C427F0;
    STOCK1 = 0x3C42810;
    STOCK2 = 0x3C42820;
    STOCK3 = 0x3C42800;
    STOCK3B = 0x3C42804;
    STOCK4 = 0x3C42830;
    SLOTFN = 0x1211C00;
    RES_FRAME = 0x2B30DE4;
    RES_MP = 0x33BDCE4;
    RES_UI = 0x43A6FC;
    RES_SETFRAME = 0x2D2D94;
    RES_INST = 0x152F8F4;
    RES_MOVE = 0x2C215E4;
    RES_NUM = 0x33C3B14;
    show_ui = 0x2CDEF0;
    set_text = 0x439520;
    WORLD_MGR = 0x4E7EAB0;
    GAMEDATA_MGR = 0x4E842A8;
    RES_GUARD0 = 0x27F7D04;
    RES_GUARD1 = 0x27F7F94;
    RES_GUARD2 = 0x27FB0C4;
    RES_GUARD3 = 0x27FA204;
    RES_SPEED = 0x9352F4;
    RES_ICONCTRL = 0xA37324;
    RES_HUDINIT = 0x33F5D24;
    icon_widget_init = 0x33B7DA0;  /* (widget, heap): widget+0x20 = part holding Pa_ReplaceIcon_00; builds its icon controller (initial icon Item_AgonyStone) */
    tex_replace = 0xA73920;     /* (replacer, const char **name, flag): load UI/Tex/Icon/<name> into a replaceable pane texture */
    item_actor_name = 0x592B20; /* (manager, const char **out, item index): actor name of an item (Item_Boomerang ...) */
    ITEM_MGR_SLOT = 0x4C7E0D0;  /* -> pointer to the item manager pointer */
    ITEM_NAME_DEFAULT = 0x4C7DAD0; /* -> default (empty) name pointer */
    ITEM_SET_SLOT = 0x4C7E2A8;  /* -> pointer to an object whose byte +0x5C0 is the item set passed to the equip call */
    MAIN_SCHED_VT = 0x4B05318;
    find_part = 0x43C3E0;
    find_anim = 0x43C7A0;
    set_frame = 0x2D2D90;
    PLT0 = 0x3C41C50;
    GOT0 = 0x4CBF5C0;
    GOT1 = 0x4CBF5D0;
    GOT2 = 0x4CBF5D8;
    GOT3 = 0x4CBF5C8;
    GOT4 = 0x4CBF5E0;

    /* Module-relative offsets consumed by MOD0 in core/module.S */
    __dynamic_off    = __dynamic_start - __base;
    __bss_start_off  = __bss_start - __base;
    __bss_end_off    = __bss_end - __base;
    __module_object_off = __module_object - __base;
}
