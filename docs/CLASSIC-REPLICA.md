# Own replica of Classic Item Slots: analysis and plan

Goal: our own version of "Classic Item Slots & Smart HUD" (sonofsilvanus, v1.4.3) inside OoT Master Mod, so the
way it is used can be our own. The upstream repository only has the README (no code); what follows comes from that
README, from the hook map of its IPS (docs/CLASSIC-HOOKS.md) and from what our own module already does.

## What Classic does (from its README and IPS)

| Feature | How Classic does it | Hook sites (main) |
|---|---|---|
| Extra item slots X/L/R (+ ZR), separate for child and adult | intercepts the stock "equip item into slot" call | 4 calls of `0x1211C00` (0x33A927C, 0x33AAC34, 0x33BD928, 0x33C9AB4) |
| Buttons pressed in game use the slot's item | rewrites the controller state it reads | 5 controller reads (0x34694F8 .. 0x3469698) |
| Assignment in the pause menu (Items tab: X / L / R on a highlighted item) | pause menu's own assignment code | the same `0x1211C00` calls + pause overlay setup |
| Put Away moves to A when standing still | input remap + "hand state" setup | 0x33D7124, 0x33D8CC4 (function entries) |
| No control guides at the bottom; A / ZR context prompts that flip N64 style | guide table edits (romfs) + control-guide setup hook | 0x0D57CE4 |
| New HUD buttons with item icons, ammo / magic counts | romfs: new panes in the HUD layout + button art as BNTX textures | HUD and pause overlay setups 0x33F6894, 0x33E64E0 |
| Assignments shown in the pause menu under the rupee counter | pause layout panes | pause overlay setup |
| Themes (diamond, slots only, N64) and an in-game layout editor (both sticks) | its own state + saved layout | input reads |

Classic ships a romfs (UI archive repacked at its exact size, BNTX button art, text edits) plus an IPS and a
`subsdk9`. Our mod coexists with it today through `--compat` (Classic owns the 5 input sites, we read input
through a PLT-stub hook).

## What we already have

- `features/classic_slots/classic_slots.c` (not shipped; release builds only `hero_core`): B / L / R / ZR slots that
  work by equipping the slot's item into the game's item box (forced item index on the stock `0x1211C00` call),
  holding ZR while the slot button is held, and restoring the previous item on release. Assignment is a test
  method (ZL + button cycles the item). Measured item index -> ItemPattern icon frame table.
- HUD know-how from the clock / rupee / ring work: our own picture and text panes in PlayerStatus_00, any texture of
  the Common archive through private material copies, tint, live tuning.
- Appended layout parts work again (128 gauge parts were instantiated before the dot-tube ring). The old blocker
  "item-button clones are never registered" predates the descriptor fixes (+0x40 / +0x42) and has not been retried.

## The hard part: item icons in our own buttons

Item icons are not static textures: PaReplaceIcon_00 / PaItemBtn_00 draw the runtime texture `FBLayout_00_ASTC4x4`
and pick the item with the `ItemPattern` animation. So the slot buttons need engine item-button parts, not plain
pictures. Plan: append `PaItemBtn_00` (or `PaReplaceIcon_00`) parts with the corrected descriptor fields and drive
`ItemPattern` / `StockNum` like the stock item box. Plain picture panes (our material copies) are enough for the
button frames, letters and backgrounds.

## Plan (phases, each testable on its own)

1. **Item-button parts in the HUD (de-risk first).** Append 1, then 4, `PaItemBtn_00` parts to PlayerStatus_00 with
   the stock descriptor layout; check find_part, drive ItemPattern (icon) and StockNum (count). If they still do not
   register, fall back to PaReplaceIcon_00 or to cloning the stock item box's whole subtree.
2. **Slot HUD.** Frames / button letters (picture panes, native textures or a small own texture), positions near
   the stock item box, child / adult sets, hide during menus (same gating as the clock).
3. **Controls without the third-party IPS.** Own the 5 input reads (our non-compat build already hooks them) and
   reuse the equip-and-hold method of classic_slots.c; keep the stamina filters in the same input pass.
4. **Pause-menu assignment.** Hook the Items tab: X / L / R on the highlighted item assigns it (find the cursor's
   item index through the stock `0x1211C00` calls made by the menu).
5. **Persistence.** Keep assignments in GameData (an unused flag/int range, or our own save-independent file) and
   per child / adult.
6. **Extras, optional:** Put Away on A, removing the bottom control guides, N64-style A / ZR prompts, layout editor.
7. **App.** "Classic (own)" vs "Classic (sonofsilvanus)" choice, button style, layout options.

Open questions to settle in phase 1: the item index -> ItemPattern table for every item (ours covers 15), how the
game shows ammo for bombs / arrows / seeds on an item button (StockNum vs a separate pane), and magic cost display.

## Phase 1 results (Nov 14)

- **Appended item-button parts work.** Four clones of the stock item box (`Pa_SelectItem_00`, asset `PaItemBtn_00`)
  appended to PlayerStatus_00 (common desc `+0x40 = 0xFFFF`, `+0x42` = part index, like the old gauge parts) are
  created, found by `find_part`, have all 11 animations (ItemPattern, StockNum, NumMax, NumMin, IsInvalid, Type,
  ItemChange, Select, UnSelect, Decide, Assign) and draw, with a clean log. `PART_N = 4`, `slots_update()` in hud.c.
- **Item icons are textures loaded by name at runtime.** `PaItemBtn_00` contains the part `Pa_ReplaceIcon_00`,
  whose two panes (icon + shadow) use the placeholder texture `FBLayout_00_ASTC4x4`. The HUD replaces it with
  `UI/Tex/Icon/<Item_Name>.bntx.zs` (129 icons in the dump: `Item_Boomerang`, `Item_Bomb`, `Item_DekuNut`, ...) and
  `UI/Tex/IconSh/<name>_Sh`. ItemPattern alone shows a placeholder (a button-glyph "L").
- **How the game sets an icon** (stock HUD at main+0x33B7E80, same pattern used by Classic's module):
  1. allocate a 0x40-byte icon controller, set its vtable (`[main+0x4C973B0] + 0x10`) and fields, link it into
     the part's list, zero `+0x30` / `+0x38`;
  2. `main+0xA37320(controller, part)` creates the texture replacers for the part's icon and shadow panes at
     `controller+0x30` / `+0x38` (it allocates through the engine heap, 0x58 bytes each);
  3. `main+0xA73920(controller->+0x30, &"Item_X", 0)` and `main+0xA73920(controller->+0x38, &"Item_X_Sh", 0)`.
- Calling `main+0xA73920` on the object found at `nested ReplaceIcon frame + 0x6A8` recursed until the stack
  overflowed (game frozen): that object is not a ready replacer. The direct call is kept behind
  `SLOT_ICON_DIRECT 0`.
- **Solved (commit f5ad284 and later):** the controllers are built by the game's own routine
  `main+0x33B7DA0(widget, heap)` (the Agony Stone icon setup: finds `Pa_ReplaceIcon_00` in `widget+0x20`, builds the
  controller, initial icon `Item_AgonyStone`). We call it with a stand-in widget per button **during the PlayerStatus
  HUD init** (hook 12 on `main+0x33F5D20`, x0 HUD, x1 heap): that heap only accepts allocations during the init
  (later calls got a null controller and crashed). Hook 11 on `main+0xA37320` captures the controller it creates.
  Icons are then set any time with `main+0xA73920` on `controller+0x30` (name) and `+0x38` (`name_Sh`).

## Item index -> icon (Nov 14)

- `main+0x592B20(manager, &name, item)` returns the item's actor name, which is also its icon texture name.
  `manager = **(main+0x4C7E0D0)`, default name `*(main+0x4C7DAD0)` (the HUD does the same before setting its icon).
- Item index = the index of the equip call `main+0x1211C00`. Read live:
  0 Item_DekuStick, 1 Item_DekuNut, 2 Item_Bomb, 3 Item_Boomerang, 4 Weapon_Range_SlingShot, 5 Item_Hookshot,
  6 Item_Longshot, 7 Item_Hammer, 9 Item_Bombchu, 10 Item_DinFire, 11 Item_FaroreWind, 12 Item_NayruLove,
  13 Item_MagicBean, 14 Item_Bottle_<content>, 18 Item_FishingRod, 30 Weapon_Range_Bow, 31 Item_WeirdEgg ..
  44 Item_ClaimCheck (trade items), 46 Item_Arrow_Fire, 47 Item_Arrow_Ice, 48 Item_Arrow_Light
  (8, 15-17, 19-29, 45: empty in this save).
- `ItemPattern` is the per-item **framing** of the icon in the button (frame 0 draws it oversized), not the item
  choice; the measured item -> frame table is applied per item (`item_pattern()` in hud.c). `ItemChange` is the
  icon's pop-in animation (frame 0 = hidden). `Type` changes nothing visible.

## Next (requested): button backgrounds, Jump and context A
- Each slot icon must sit on the **button it is assigned to** (B / L / R / X look, like Classic), plus a **Jump**
  button and the **context A** (attack / talk / open ...). Candidates: the game's own `PaABtn_00` part and the
  `DoCommand*` textures (A action command UI), button glyphs of the External_00 font (`T_Assign_00` in the item
  button), or our own textures loaded through the same icon mechanism (Classic ships `UI/Tex/Icon/Mod_HudButton*`).

