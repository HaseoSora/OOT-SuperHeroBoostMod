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
