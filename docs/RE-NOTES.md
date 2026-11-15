# RE notes (super-hero-boost)

Build under test: title `0400486024DEC000`, update 131072, main build id
`E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348`. The test emulator loads mods from
its configured `LoadDir` (see the `load_directory` entry in `qt-config.ini`).

## Load layout (confirmed from logs)

- main loads at `0x8043C000` (size `0x4EA0000`) in the last run.
- subsdk0 follows main at `main + 0x4EA0000`.
- subsdk9 (ours) loads at `main + 0x4F80000`, right after subsdk0.
- Our module is linked at `0x4F80000` (main-relative), so offsets in the IPS and
  in `bl`/`b` targets are main-relative. This matches the emulator.

## Static recompilations (Hookshot and Longshot)

- They are not emulators: `bin/longshot.exe` is the game built as native code, and `image.bin` holds the guest image.
  `host/mods.c` ignores `exefs` patches by design and only reads `mods/<name>/romfs`.
- The builder's module order is `rtld, main, subsdk0..subsdk9, sdk`, page aligned. Adding our `subsdk9` to
  `.longshot_exefs` places it at `main + 0x4F80000` (0x84FA0000 with main at 0x80020000), which is the module's link
  base.
- Verified with the builder's lift: subsdk9 72 functions, 100% translated, 0 untranslated; the image contains the
  config block at `0x84FB2010`. `hos_image.c` leaves subsdk9 out of the DT_INIT list (init 0), which is fine: the
  hooks enter its code directly.
- Installing means rebuilding (`nx2/make_game.py --update`), not copying files. See [LONGSHOT.md](LONGSHOT.md).
- HUD crash on a map load (HyruleField_Child): `hud_frame → plates_update → name_index` dereferenced a name pointer
  (`0x6a4cff8b47b`) from a game layout that was being rebuilt (guest LR `0x84FA6D24`). Fixed by range-checking the
  name-table entries in `name_index`/`pane_record`. (An extra HUD-init gate was tried and removed: it could leave the
  HUD off when the two init hooks ran in the other order; the pointer checks alone fix the crash without touching the
  normal drawing path.)
- The same stale layout also reaches the **game's** `find_part`/`ui_find_sub`, which do not check the names. The module
  now repairs invalid name slots (replacing them with a valid empty name) before those calls and waits two frames after
  a HUD init. The module text grew to `0x10000`, shifting the `sdk` by one page: that build recompiled 71 of 479
  chunks (stable chunk boundaries + object cache); later code changes that keep the same text size only recompile the
  module chunks.
- The valid-pointer range must cover **Longshot's** heap and stack (4.4-4.8 TB); the emulator's is below 1 TB. The first
  1 TB limit made the repair reject valid names, and the id-4 diagnostic compared the bad 7.3 TB name. 6 TB accepts
  the valid pointers and rejects `0x6a4cff8b47b`; `str_eq` and `hud_on_settext` validate their pointers too.
  Keeping the module text at `0x10000` made the following build recompile **14 of 479** chunks (4:56 in all).

## NSO for subsdk9 (fixed in F0)

- The loader needs the compressed sizes at `0x60/0x64/0x68` set to the raw
  sizes. Zero makes it read nothing for the segments (crash on load).
- No hash at `0xA0` (flags == 0). Module id at `0x40`.
- MOD0 offsets must come from real section addresses (`core/link.ld`), and data
  must be page-padded so bss starts where MOD0 says.

## Input hook sites

Five stock sites read input (`INPUT_SITES` in tools/hook_sites.py). Each calls one of five
import stubs in main:

| site | stub | status |
|---|---|---|
| 0x34694F8 | 0x3C427F0 | hooked, **never runs** in boot or gameplay |
| 0x3469524 | 0x3C42810 | hooked, never runs |
| 0x3469550 | 0x3C42820 | hooked, never runs |
| 0x346966C | 0x3C42800 | hooked, **the gameplay input path** (~60 calls/s, 16 samples, B/A bits seen) |
| 0x3469698 | 0x3C42830 | hooked, never runs |

Each stub is `adrp x16 / ldr x17,[x16,#off] / add x16 / br x17`, a jump through a
GOT slot. Slots 0,1,2,4 still point at PLT0 (main+0x3C41C50, lazy binding) until
first use; slot 3 is already bound to a function in `sdk`.

### Root cause of the old "site 3 crash" (solved)

`bl STOCKn` with `.equ STOCKn, <const>` assembles to a constant offset, not a
PC-relative branch, so the wrapper jumped to `wrapper_pc + 0x3C42800`
(= subsdk9 base + constant). This was never a GOT problem. Fix: STOCK0..4,
SLOTFN, PLT0 and GOT0..4 are linker symbols in `core/link.ld`, so the
relocation is PC-relative. The first call through a still-lazy slot is
tail-called with the game's own LR (hooks.S) in case the dynamic linker finds the
caller module from LR; this part is a precaution and has not been shown to be needed.

Consequence: only site 3 sees gameplay input. The four item-button slot sites
(`bl 0x1211C00`) also never ran in the live check, so F3 needed its own RE.
## stamina (F2) status

- Stamina state machine in `features/stamina/stamina.c` (moved from `core/`).
  Values are **placeholders** written as clean-room defaults; they have not been
  balance-tested against the final gameplay tuning yet.
- Handler `features/stamina/stamina_hooks.c`: site 0 counts combat frames, charges
  the slash cost on B press, and when stamina is empty removes B/ZR from the input
  buffer at every hooked site.
- Capacity uses a fixed `LIFE_QUARTERS = 20` (5 hearts). Reading the real heart
  count from game memory is still open.
- Verified only at boot level: frame 3000 at ~76 s, no backtrace. The attack
  block itself is **not** verified in game yet (no HUD, no input playback).

## Probe result (F1)

- With sites 0, 1, 2, 4 hooked, the game runs at ~60 fps (frame 3000 at ~72 s).
- Two HLE service asserts appear in the log (`nx2:gsv 903`, `prepo:u 10500`).
  They are emulator service stubs, not from our hooks; the game keeps running.


## HUD and item buttons (F3/F4) findings

- HUD part registration: hook main+0x43A6F8 (UI resource build, x0 handle, x1 config).
  We give PlayerStatus_00 a private metadata copy with one extra part
  `Pa_ShbStamina_00` (clone of the stock gauge descriptors; CityHash64 of the
  name in tools/lib/cityhash.py, checked against all 40 stock names) and a private
  copy of the gauge file with a flat white fill tinted yellow. Frame drive from
  main+0x2B30DE0 (scheduler vtable main+0x4B05318). Verified live: bar renders under
  the hearts and tracks stamina. The magic gauge is not used.
- HID button bits are the standard ones: A 0x1, B 0x2, X 0x4, Y 0x8, L 0x40, R 0x80,
  ZL 0x100, ZR 0x200 (core/hid.h had A/B swapped until this commit).
- In this game R equips an item into the HUD item box and ZR uses it. R (and L) end
  up in slot site 3 (0x33C9AB4 -> 0x1211C00); x2 is the item index (inventory order,
  1 = deku nut, 3 = boomerang). Overriding x2 before the stock call equips that item.
  button_mapping: X/L/R -> press R (equip with override) -> hold ZR while held ->
  restore ZR's previous item. Verified: nut use pose, boomerang tutorial.
- Not done: pause-menu assignment, slot icons in the HUD, context A/ZR prompts,
  edit mode, adult/child separate sets, stamina on roll/jump action hooks.

## Controls and item icons

- Real controls on this game: X jump, A dodge/roll, Y sword, B/L/R/ZR free. The
  item buttons are B, L, R, ZR (an empty slot keeps its normal behaviour). stamina costs:
  Y = slash, A = roll; with stamina 0 in combat both are removed from the input.
- Assignment (replaces the pause-menu assignment, whose hooks 9-13 turned out to be
  UI constructors): hold ZL and press B / L / R to cycle that slot's item (ZR is not
  assignable that way: ZL+ZR is target-and-use). Assignments are not saved yet and
  there is one set (no child/adult split yet).
- Item index -> ItemPattern icon frame (measured with `BUTTON_PROBE=1 python
  tools/build_core.py ...` + `tools/live_check.py --linger 110`): 0:0 1:6 2:4 3:3 4:1
  5:33 6:34 7:32 9:5 10:8 13:2 14:23 18:36 30:24 31:9. Indices that keep the previous
  frame are not owned in that save.
- PaItemBtn_00 (HUD item button) animations: ItemPattern (icon), StockNum, NumMax,
  NumMin, IsInvalid, Type, ItemChange, Select/UnSelect/Decide/Assign.
- HUD slot icons are NOT done: cloning Pa_SelectItem_00 descriptors (1 or 4 clones)
  produces panes (positions visible in the pane array) and the instances do reach
  hud_prepare, but find_part never lists them as children, so they cannot be driven.
  The stamina gauge clone works. Next idea: find what registers a part in the child
  list (find_part walks a list at owner+0x128/+0x130, entries name at +0x148) and why
  item-button instances are skipped.

## Slot circles attempt (HUD) - blocked

- Texture `Circle64_00` exists in the Common UI archive (stock), so a gauge clone with
  that texture and a full gauge draws a tinted circle (private gauge copy per part,
  distinct asset names; pool 0x40000).
- The layout accepts exactly ONE appended part (the stamina bar): with 5 appended gauge
  parts only the first is ever found by find_part (slots_bound 0). Appending item-button
  clones failed the same way, so the limit is not the part type.
- Reusing four filler parts of the stock layout (Pa_AgonyStone_00, Pa_ReplaceSubItem_00/01,
  Pa_GuideCross_00: re-parented to the root, renamed, descriptors replaced by the gauge
  ones) froze the game at 0 fps. `PART_N` in core/hud.c is back to 1 (stable). The code
  path for PART_N=5 is still in place (build_root, part_replaces).
- Ideas left: find what sizes the child list (allocation near the 0x1525B60 core init)
  and enlarge it; or draw all four circles from one private gauge file with extra panes.

## Multi-part limit investigation (HUD)

- The layout's children list (layout+0x128 sentinel, first at +0x130, entry name at +0x148) lists the
  7 stock parts plus ONLY the first appended one, even with 5 appended parts whose table counts
  (common 38, parts 12) and pane records are correct. All appended instances do reach hud_prepare
  (private gauge copies were built), so the child creation runs but the later ones are never
  registered. Per-call config copies did not help. Instance creation: loop at 0x1525CEC (panes of
  type part) -> 0x152F8F0 / 0x152F990; registration happens in the caller.
- Next candidates: 0x152F990..0x152FD60 (child layout creation) and what registers the entry
  (0x215DC0); or avoid the limit by making the single appended part a custom multi-pane layout.

## Own-layout route: what the archive shows

- `UI/Layout2Archive/Common.Product.100.Nin_Ounce_NVN2.blarc.zs` = zstd (dictionary tools data zsdic1.bin)
  of a SARC with 151 `.buil` files (tools/lib/sarc.py reads it; PlayerStatus_00.buil, PaItemBtn_00.buil,
  PaMpGauge_00.buil, PaReplaceIcon_00.buil ...). In the file, pointers are offsets; the engine adds a base.
- PlayerStatus_00.buil UIL root (file offset 0xF8) has 7 tables of (names, descs, hashes, count):
  +0x20 common panes (33), +0x40 (12), +0x60 (10), +0x80 (2), +0xA0 (0), +0xC0 parts (7), +0xE0 (0).
  Only +0x20 and +0xC0 are extended by the runtime clone; the other tables (12/10/2 entries) may hold
  per-part bindings that the second and later appended parts miss. Not yet checked.
- Item icons are NOT static textures: PaReplaceIcon_00's icon pane uses the runtime texture
  `FBLayout_00_ASTC4x4` (rendered by the game) and ItemPattern selects the item. So the icons on top of
  the slot circles have to come from engine item-button/replace-icon parts; a custom layout alone can
  draw circles, bars and placeholder art but not the item icons.

## Multi-part findings (latest)

- Part instantiation (0x152F8F0) runs for all 5 appended panes, but the child frame object it receives is
  NULL for every appended part after the first (hook id 4 logs pane index and child). Handles are
  distinct and 0x6F60 apart. Growing the Common archive budget in ResourceSizeTable (tools/make_restbl.py,
  +3 MB) did not change it (possibly not applied: other mods' tables).
- Compiler trap fixed: clang turned `switch` returning strings into a lookup table of absolute pointers
  (wrong at runtime in this relocation-free module). CFLAGS now has -fno-jump-tables.
- find_anim returns a shared "not found" object (not null): compare with find_anim(part, "<nonsense>").
- Repurposing stock filler parts (Pa_AgonyStone_00, Pa_ReplaceSubItem_00/01, Pa_GuideCross_00) as item buttons
  (only their part descriptor replaced by Pa_SelectItem_00's, names/parents kept) crashes during load
  (PC=4). PART_N=1 is the stable setting; the code for >1 is still in hud.c (build_root).

## Layout file format (.buil / BFFH) - what is known

- File = header (0x00..0xA8: magic BFFH, file size at +8, section directory at +0x10), two sections
  declared by `BFSI` records at 0xA8 ("Default": data at 0xF8) and 0xD0 ("StringPool"), then the UIL root
  at 0xF8. All internal pointers are file offsets (u64); the engine rebases them at load (no visible
  relocation table: its loader knows the schema). Hence a layout writer must follow the schema exactly.
- UIL root (PlayerStatus_00): name/desc/hash tables {names, descs, hashes, count u32 @+24, 8}:
  +0x20 common panes (33, desc 68 B), +0x40 picture panes (12), +0x60 pictures (10), +0x80 text (2),
  +0xA0 (0), +0xC0 parts (7, desc 88 B), +0xE0 (0). After +0x120: array descriptors {ptr, count, size}:
  +0x130 36 entries (each -> {offset, 0, count, size}: animation/parameter blocks), +0x150 13 hashes
  (parameter names: HeartPos, AgonyStonePos, IsMpGauge, IsItemVisible, IsOpenShortCut, ...),
  +0x1D0 pool 9x16 B, +0x1E0 2x4, +0x1F0 5x8, +0x200 screen size 3840x2160 + ptr, +0x210 12x4, +0x220 32x1.
- Not found: why only one appended part per layout is built. Pane setup code at 0x1529990..0x1529D00 reads
  per-type pools via [root+0x1E8]/[root+0x1F4] indexed by a pool index taken from the part/pane
  descriptor; the appended parts reuse the gauge's descriptor, so this index may need its own pool entry
  (untested: extend the +0x1D0..+0x220 pools).

## Pool extension test (negative)

- Extending the root pools (+0x1D0, +0x1E0, +0x1F0, +0x210, +0x220: count+5, copies of the last entry) with
  five appended gauge parts changed nothing: child frame objects are still NULL for parts 2..5.
  The limit is not in those pools. PART_N stays 1 (stable). extend_pools() remains in hud.c for reference.

## Rupee counter / clock HUD (native look)
- Look copied from the game's own rupee counter: plate textures NumBaseSide_00 (fill) / NumBaseSide_01 (edge), BC4
  507x80 with a chevron on the left end; each is drawn twice (second copy mirrored, scale x = -1) so both ends get
  the chevron. Rupee icon = Nt_RupeeIconNew_00. Sun = Circle64_00 + 8 rotated White8_00_BC4L rays; moon = two
  Circle64_00 (crescent). All live in Common.Product.100.Nin_Ounce_NVN2.bntx.zs (no sun/moon texture exists there,
  nor in the title or notes resources). A third-party HUD mod draws its sun the same way (32 small panes).
- Materials: root+0x130 = {u64 *materials, count, stride}. Picture/text-list entry (+0x40 table) +0x14 = material
  index. A textured material starts with a sampler list {ptr, count}; sampler = {u32 flags, pad, u64 texture name}.
  Textures resolve by name at layout build, so a deep copy of a textured material (P_SubItemBg_00 uses #31,
  MinigameSubItemBase_00) with a new name, appended to the array, gives a picture any texture of the archive.
- Common pane desc +0x40 / +0x42: for a picture +0x40 must be 0xFFFF and +0x42 = index in the picture list. A value
  in +0x40 is an index into a by-name extra-data table ([layout+0x68], lookup main+0x14EEDA0 via 0x43AC20 /
  0x152D080) that the engine searches on every lookup: our old swapped values made it read garbage lists, which
  produced hundreds of thousands of "Unmapped Read/Write" log lines at load (black screen ~2 min, 30-100 MB log).
- Tint: pane object (record +8) +0x20 = RGBA floats, works for pictures and text panes.
- Tuning: g_hudp[] in core/hud.c; tools/hud_tune.py set/get/shot/cfg writes it live (and the HUD options).
  `g_hudp[20]`/`[21]` are the clock plate x/y, so the clock sits to the right of the rupee counter.

## Stamina ring as a dot tube (replaces the 128 gauge parts)
- The ring is now ~230 plain picture panes (P_ShbPic_020..) with the stock Circle64_00 texture: 48 dots on ring 1
  and 64 on ring 2, overlapping so they read as one continuous tube with round ends. A slightly bigger black dot
  behind each one is the empty track and the border. The fill's last dot sits at the exact fill angle (small-angle
  sin/cos rotation of the precomputed dot table), so the end moves smoothly. Yellow when exhausted.
- No gauge file copies or part instances any more (PART_N = 0): lighter to build and to draw.
- Looked at and dropped: SaveGradation_00 (128x128) is an angular (conic) gradient, the usual base for a
  threshold-filled ring, but the game only uses it for the save icon's rotating glow (PaSaveLoadIcon_00, 3
  samplers in one material); using it as a fill would need the ui shader's combiner/threshold settings.
- Live tuning: tools/hud_tune.py set <i>=<v> --sym g_ringp (radii, thickness, border, track alpha/brightness).

## Songbook (native song list) - Nov 14

- The remake's songbook is the native one opened with ZL (and the pause-menu song list). It shows only learned songs.
- Ocarina enter/leave are function entries at `main+0x2894340` and `main+0x28947F0` (`pacibsp`, resume +4). `x0` is
  the ocarina/songbook context.
- Songbook fields in that context (observed from the song-list code): selected song index at `+0x22C`, learned flag
  byte per song at `+0x264 + index` (1 = learned), page/state at `+0x278`, UI state at `+0x230`, busy flag at
  `+0x114`.
- Song data: `GameParameter/MelodyScoreBook/Default.game__ocarina__MelodyScoreBook.bgyml`. It has 12 entries
  (Lullaby, Epona, Saria, Sun, Time, Storms, Minuet, Bolero, Serenade, Requiem, Nocturne, Prelude). Each
  `MelodyScore` is a list of note hashes.
- Note hashes map to the five remake buttons: `0xCC...` (3433458314)=Y, `0x313...` (825411668)=X,
  `0x54D...` (1423767502)=A, `0x982...` (2552959238)=R, `0x63C...` (1673550086)=L.
- `features/songbook` does not call the internal playback routines. It reads the selected index/learned flag, waits
  20 frames, then injects the note buttons for 3 frames each with 4-frame gaps through the gameplay input hook. The
  game recognises the melody with its normal logic (sound, animation, effects).
- Scarecrow's Song (index 12) is player-composed and is intentionally not injected.

## Ocarina UI and songbook flow (Nov 14, live)

- D-pad **Left** opens the ocarina. The footer shows `Ver partituras ZL`, `Tocar una nota L R Y X A`
  and `Cancelar B`. ZL is **held** to show the songbook; releasing it returns to the ocarina page.
- Ocarina context fields: page `+0x278` (0 = ocarina page, 1 = song list, 2 = preview), state `+0x230`,
  busy `+0x114`, selected song `+0x22C`, preview/highlighted song `+0x220` (13 = none), learned flags
  `+0x264 + index`.
- Melody buffers: display notes `+0x158` (8 x u32 hash), matcher sequence `+0x478`, ring index `+0x25C`,
  total count `+0x250`. Hashes: A 1423767502, X 825411668, Y 3433458314, L 1673550086, R 2552959238.
- The ocarina state machine (`main+0x3296E20`) is called from `main+0x32923D4` **only when page 0 and the
  "finished playing" flag `+0x26602` bit 0 is set** (or `+0x273` bit 0 with another flag). Hooking that
  function is therefore useless for starting a melody: the flag has to be written from a per-frame hook.
- The matcher is `main+0x32980F0(ctx)`: compares `+0x478` with MelodyScoreBook starting at the last note
  (`+0x25C - 1`, or 7 when 0) and walks backwards. It returns 1 on a match; the caller then sets
  `busy = 2` and clears `+0x244`, `+0x265FC` and `+0x26602`.
- On the preview page the game stores the highlighted song at `+0x220`; pressing A/R/X there plays a
  preview only. The song effect needs the melody on page 0.

## Beta enemy mods (Nov 14)

Both mods are generated from the user's own dump by `tools/make_enemy_opts.py`; nothing is redistributed.

- **Duplication (Option A)**: `Banc/*.bcett.byml.zs` keeps an `Actors` array; a generic `Enemy_*` entry is
  cloned with a new `Hash`, its `Phive/Placement/ID` set to the same value, a new `SRTHash` and a small
  `Translate` offset. Entries with `Links`/`Name` and every boss/miniboss/scripted actor are skipped.
  `Scene/Component/AutoPlacementMgrParam/*.bgyml` doubles `CreateActorCountMin/MaxAtOnce` and
  `MinExistActorCountToCreate`, and halves `IntervalToCreateFrame*`. Rewritten BYMLs grow, so
  `System/Resource/ResourceSizeTable...rsizetable.zs` is patched by CRC32 (`binascii.crc32` of the
  path without `.zs`) to the new uncompressed size.
- **Speed ×2**: `Pack/Actor/Enemy_*.pack.zs` scales `BSA/MovementParam` (`Walk/Run/Dash/Escape/Special/Strafe/
  LiftWalk/WalkBackwards`) by 2, and halves `GameBalance/AttackInterval/*` plus the explicit
  `ActionSeqContainer` cooldown fields. `AttackIntervalRatio` is **not** touched: it multiplies the
  global interval table, so scaling both would give ×4.
- **Animation**: `AS/Enemy_*.root.asb.zs` (ASB, magic `ASB `): header `0x14` = element count, `0x18` =
  element array, stride `0x24`. Each element starts with a `u16` type; type **12** is the frame
  controller and its payload offset is the `u32` at element `+0x08`. The playback rate is the `f32` at
  payload `+0x04` (normally `1.0`, with 0.8/1.1/1.2 variations; `0.0` = paused/instant) and is
  multiplied by 2. Earlier attempts read a different table (`0x0C/0x10`, stride `0x30`), which is why
  they saw only zeros.

## Sprint speed, shield cost, enemy health (Nov 14)
- Sprint speed: the player's ground movement is `main+0x9352F0(player, direction, float speed)`; his own call is the
  `bl` at main+0x934990 (returns to main+0x934994). Hook 10 sits on the function entry and, only for that return
  address, multiplies s0 (saved d0) by `sprint_speed_pct` while A is held and not stripped by the stamina rules.
  Measured: run ~5.6 m/s, native sprint ~7 m/s, x2 -> ~14.5 m/s. Default 125 %. Writing position (actor+0x31C) or
  velocity (actor+0x388) does nothing (both are outputs); RollingMaxSpeed does not drive the sprint.
- Shield cost: the hit arrives during the player's hit reaction, when his movement update pauses (player_active() false
  for a few frames) and queued events were dropped. Shield hits are now a counter (player_guard_seq) kept across
  pauses shorter than 60 frames; GuardFailHit (the hit went through) no longer counts.
- Enemy health: works (g_hp_log). Small enemies with MaxLife 1 scale to 3; the large enemy with MaxLife 6 only takes
  damage on its root (IsHeadshotOnlyDamage, bone Tail_1). The starting sword has EquipmentPerformance 1.
- Stamina refill wait: 0.8 s, 1.8 s in combat, 2.5 s after exhaustion.

## Great Fairy rewards and Farore's Wind outdoors (Nov 14)
- Fountain -> flow mapping (from `Banc/<stage>/*_Dynamic.bcett.byml`, `MapIconFacilityIsOpen`):
  `HyruleCastle` -> `Dm_FairyFountain_Power`; `DeathMountainTrail` -> `Dm_FairyFountain_Din`;
  `DeathMountainCrater` -> `Dm_FairyFountain_Wisdom`; `DesertColossus` -> `Dm_FairyFountain_Nayru`;
  `ZoraFountain` -> `Dm_FairyFountain_Frore`; `GanonCastle` -> `Dm_FairyFountain_Courage`.
- Each flow carries two item strings: a `SwitchEvent` param `GameDataName = IsGet.<item>` (already received?)
  and a `SubFlowEvent` to `Dm_SY_GetInEvent:GetInEvent_Demo_NotLookatObjectEntry` with `ActorName = <item>`.
  The reward line is an `EventTalk` param `MessageId = EventFlowMsg/<fountain>:<fountain>_0004`.
  `Dm_FairyFountain_Power/Wisdom/Nayru` can be remapped by changing those three only; the `evfl` Python library
  rewrites the file and is byte-identical when nothing changes. The `ForbidSetWarpPointArea` actor only appears in
  FireTemple, so it is unrelated to the outdoor rule.
- Farore's Wind: `Event/EventFlow/WarpEvent.bfevfl` entry `FaroreWind_SetWarpPoint` starts with a
  `SwitchEvent` on `EventQueryIsForbidSetWarpPoint`: `0` = `DisableSetWarpPoint` (real forbidden area),
  `1` = `DisableSetWarpPointDungeon` (message "you cannot place a warp point outside a dungeon"),
  `2` = set the point. Pointing case 1 at the same event as case 2 allows outdoor points; case 0 stays blocked.
  The `FaroreWind_Warp` entry has no dungeon check, only the MP check.
- `Mals/<lang>.Product.110.sarc.zs` holds `EventFlowMsg/*.msbt`. The Din fairy's sister overview (messages 7/9/10)
  still names the original rewards; fixing it needs an MSBT TXT2 rebuild (not done in this beta).

## Area collectible HUD counter (Nov 14)
- Current area: GameData `Sequence_CurrentBanc` is **String64 index 31** (`HyruleField_Child`, `Market_Child`,
  ...); the live string is at `+0x74` of a 0x108-byte record, same layout as the quick-select equipment slots.
- Gold Skulltulas: `IsGoldSkullDead` is a **Struct** with 100 Bool members. The member name is
  `IsGoldSkullDead_<placement hash as unsigned decimal>` and the full Bool entry is
  `IsGoldSkullDead.IsGoldSkullDead_<hash>`. Those Bool entries are also in the GameDataList's `Bool` section,
  so the live value is the Bool table record at index `position in that section` (stride 0x18, live byte at +0x16).
  114 Gold Skulltula actors map to 100 unique flags (adult/child Banc variants repeat some).
- **Those flags are runtime only** (Nov 15): the game sets them when the token drops and starts every Banc load
  with all of them false, so counting them alone reads 0 after leaving an area and coming back (heart flags are
  real save flags and survive). The durable record is the save entry **`Game`**, type `Bool64bitKey`, hash
  `0xA3DB7114`: a header u64 (`0x00283696ACC3DD10`), then the collected actor hashes **ascending**, then a 0.
  Live copy = the loaded `progress.sav` image: `gmd::GameDataMgr` (main+0x4E842A8) holds it in the save
  descriptor array at **+0xE80** (0x80-byte stride; magic `0x01020304` at +0, data offset u32 at +8). The entry's
  offset comes from the save index (`(u32 hash, u32 value)` pairs from +0x20 up to that data offset).
  `hud.c` caches the key array, binary-searches it per Skulltula and also remembers pickups seen this session,
  so a new token counts at once and still counts after the reload.
- Heart pieces: `HeartPieceAnchor` actors with `Dynamic.HeartPieceAnchor_GameDataPath` name a Bool flag
  (e.g. `DeathMountain_Enemy_Scrub_Business_HeartPiece_01`); 21 anchors / 16 unique flags. Several
  `Obj_Heart_Piece` actors have anchors with no path (chest/minigame pieces), so the counter currently covers
  only the map-anchored pieces. The rest would need the chest/scene flag source.
- `tools/make_collectibles.py` scans the Bancs and writes `build/collectibles_data.h` (43 Banc names,
  135 Bool indexes + the 135 aligned 64-bit actor hashes) before the core build; `hud.c` includes it and reads
  the Bool table and the save key set live. If the dump is missing it writes an empty table and the plate stays
  hidden.

## Equipment slots: value **and** copy (Nov 15)
- The `PlayerStatus.Equip*` String64 records hold three SafeStrings: default (+0x24), **value** (+0x74, pointer
  at +0x68) and **copy** (+0xC4, pointer at +0xB8). Writing only the value updates the menu icon but Link keeps
  the gear he had; the apply path needs the copy as well. Writing both makes the change take effect at once
  (verified with the mask: Bunny -> Lens of Truth removes the ears, back restores them) and keeps the save
  consistent. `quick_select.c` writes both groups.
- Ownership for the "only if you have it" rule: `IsGet.<actor name>` in the Bool table, looked up through
  `core/gd_index.h`'s `GD_ISGET` (hash = murmur3("IsGet." + actor)); `hud_owns_name()` does the lookup.
## buttonMapping: per-save assignments (Nov 2026)

- Save files: mount `save:`, `slot_00`..`slot_11/progress.sav` (+ `caption.sav`), `account.sav`, `option.sav`.
  The game opens `progress.sav` with mode 1 when it loads that save and mode 6 (write | append) when it saves,
  and it rotates between slots (loaded slot_02, saved to slot_04). Then it commits the mount.
- Hook: the `nn::fs::OpenFile` import stub, main+0x3C42590 (`adrp x16` re-run from our wrapper with the
  `GOT_FSOPEN` page, then main+0x3C42594). Our own file `slot_NN/ootmaster.bin` (16 bytes: "OOTM", version 1,
  child B/L/R, adult B/L/R) is written right when the game opens that slot's progress.sav to write, and read
  when it opens it to read. Other nn::fs stubs used: CloseFile 0x3C425B0, CreateFile 0x3C425D0, WriteFile
  0x3C425E0, SetFileSize 0x3C42940, ReadFile(size_t *out, ...) 0x3C43050 (all main+, game 1.1.1).
- GameData Bool table (k = 0): 0x18-byte records in GameDataList order, live value at +0x16.
  `Sequence_IsChildhood` = 1 while Link is a child; `IsGet.<actor name>` = the item is owned.
  `core/gd_index.h` (tools/gen_gd_index.py) holds their indices for GameDataList.Product.110.
- `PlayerStatus.AssignableItem.Child` / `.Adult` (Enum) are the game's own item box (ZR) per age.
- The item box (ZR) per age is `PlayerStatus.AssignableItem.Child` / `.Adult` (Enum table k = 6, 0x38-byte
  records, live value at +0x1C = murmur3 of the value name). Writing "Empty" there empties the box and the HUD
  follows. The value -> item actor comes from RSDB `PouchActorInfo` (`AssignableItem` column), in
  `core/gd_index.h` (`GD_ACTOR_BOX`). The HUD controller path (+0x150 -> +0x1F0 -> +0x38) is not reliable
  for the box name (garbage in some saves); it is only the fallback now.
- In the pause menu, A sets the box only when the menu closes (GameData unchanged until then).
