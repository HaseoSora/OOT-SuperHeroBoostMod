"""Hook sites in the stock `main` module (build E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348).

Each site is a `bl` in the stock game that reads controller input. The shared
input path (see docs/CLASSIC-HOOKS.md, sites 4..8) calls one of five stock
readers. Our module replaces each `bl` with a `bl` into its own wrapper, which
calls the stock reader exactly once and then runs our handlers.

Addresses are main-relative (main base = 0), the same space the module is
linked in (module base 0x4F80000 is main+0x4F80000).
"""

# (site in main, wrapper symbol in core/hooks.S, stock reader called by the site)
INPUT_SITES = (
    (0x34694F8, "hook_input0", 0x3C427F0),
    (0x3469524, "hook_input1", 0x3C42810),
    (0x3469550, "hook_input2", 0x3C42820),
    (0x346966C, "hook_input3", 0x3C42800),
    (0x3469698, "hook_input4", 0x3C42830),
)

# Classic extra-button sites: each is `bl 0x1211c00` in the stock game. The
# function at 0x1211c00 is a normal function (prologue pacibsp/stp), not a stub.
SLOT_STOCK = 0x1211C00
SLOT_SITES = (
    (0x33A927C, "hook_slot0", SLOT_STOCK),
    (0x33AAC34, "hook_slot1", SLOT_STOCK),
    (0x33BD928, "hook_slot2", SLOT_STOCK),
    (0x33C9AB4, "hook_slot3", SLOT_STOCK),
)

# Function-entry sites: the stock instruction at `site` is `pacibsp` (0xD503237F).
# The patch is `b <wrapper>`; the wrapper runs our code, then executes pacibsp and
# branches back to site+4 (see CODE_HOOK in core/hooks.S).
# (site, wrapper symbol, id)
CODE_SITES = (
    (0x2B30DE0, "hook_code_frame", 0),   # per-frame scheduler update (x0 = scheduler)
    (0x33BDCE0, "hook_code_mp", 1),      # magic-gauge controller init (x0 = controller)
    (0x2D2D90, "hook_code_setframe", 3), # set_frame(anim, frame): observe UI animation frames
    (0x2C215E0, "hook_code_move", 5),    # physics-actor movement update (x0 = actor), every frame
    (0x27F7D00, "hook_guard0", 6),       # ExecutePlayerReactionGuard slot 10 (shield took a hit)
    (0x27F7F90, "hook_guard1", 7),       # ExecutePlayerReactionGuard slot 11
    (0x27FB0C0, "hook_guard2", 8),       # ExecutePlayerReactionGuardJustRepelled slot 10
    (0x27FA200, "hook_guard3", 9),       # ExecutePlayerReactionGuardBreak slot 10
    (0x9352F0, "hook_code_speed", 10),   # ground movement (x0 player, x1 direction, s0 speed): sprint multiplier
    (0xA37320, "hook_code_iconctrl", 11),  # icon controller init (x0 controller, x1 heap): Classic replica icons
    (0x33F5D20, "hook_code_hudinit", 12),  # PlayerStatus HUD init (x0 HUD, x1 heap): heap for our icon controllers
    (0x2CBD20, "hook_code_menusel", 14),  # pause-menu Items caption update (x0 panel: +0x90 item index): highlighted item
    (0x439520, "hook_code_settext", 13),   # text-pane text setter (x0 pane, x1 {chars, len}): A action label
    (0x152F8F0, "hook_code_inst", 4),   # part instance creation (x1 layout, x2 pane): diagnostics
    (0x43A6F8, "hook_ui", 2),            # UI resource build (x0 = handle, x1 = config)
)
PACIBSP = 0xD503237F

# Sites we do NOT patch yet. Site 3 (0x346966C) crashes the game when our module
# calls its stock reader (0x3C42800), even as a plain tail call: the import stub
# jumps through a GOT slot that resolves to subsdk9-relative garbage. Until that is
# understood the game keeps the stock `bl` there. Details: docs/RE-NOTES.md.
DISABLED_SITES = frozenset()
