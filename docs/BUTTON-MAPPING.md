# Button mapping (buttonMapping): design and notes

Super Hero Boost's own module. It adds **B, L, R and ZR** item buttons to the HUD and lets the player assign items to
them from the pause menu. It uses no third-party mod: the module, the button art and the textures are generated in this
project.

## Features

| Feature | How it works |
|---|---|
| Extra item buttons B / L / R / ZR | the slot's item is equipped into the game's item box (item index forced on the `main+0x1211C00` call) and ZR is held while the button is held |
| Button styles | three texture sets: Switch (`OotBtnS_*`), Xbox (`OotBtnX_*`) and PlayStation (`OotBtnP_*`); style byte 0 / 1 / 2 |
| Extended layout | B, L, R, ZR, X, Y, A and the sword |
| Simple layout | only the assignable B, L, R and ZR buttons; hides X, Y, A and the sword and repositions L / R / ZR in place with B centred and closer, in a zigzag, both on the HUD and on the pause menu's Items tab |
| L mode: item | L is one more item slot |
| L mode: selector | L opens the game's item selector; the L button is hidden in both layouts and the menu legend removes L |
| Pause assignment | Items tab: B / L / R on the highlighted item; an item already in another slot is swapped |
| Jump/B swap | if the game's System > Options **Swap Jump Controls** is on, the B slot moves to **X**: X triggers the item, the icon is drawn over the X button, the X button texture and the menu legend follow, the B button becomes an unlettered jump button, and the **Saltar** label moves from X to B |
| Icons | `PaItemBtn_00` parts with the item icon and its shadow, like the native item box |

The swap option is read live from GameData (OptionData struct `0x834d9d9e`, Bool member `0x3B0FC63F`, via
`read_bool` at `main+0x179F70`). It is refreshed every HUD frame and while the pause menu is open, so changing it in
**System > Options** takes effect without reinstalling.

The module is enabled by the `button_mapping` byte in the configuration (`core/config.h`): style at offset 38, simple
layout at 39 and L mode at 40.

## HUD parts

- Four clones of the native item box (`Pa_SelectItem_00`, asset `PaItemBtn_00`) are appended to `PlayerStatus_00` with
  the corrected common descriptor (`+0x40 = 0xFFFF`, `+0x42` = part index). They are created, `find_part` finds them,
  they have all 11 animations (ItemPattern, StockNum, NumMax, NumMin, IsInvalid, Type, ItemChange, Select, UnSelect,
  Decide, Assign) and they draw. `PART_N = 4`, `slots_update()` in `core/hud.c`.
- The icons are textures loaded by name at runtime. `PaItemBtn_00` contains the `Pa_ReplaceIcon_00` part, whose two
  panes (icon + shadow) use the placeholder texture `FBLayout_00_ASTC4x4`. The HUD replaces it with
  `UI/Tex/Icon/<Item_Name>.bntx.zs` and `UI/Tex/IconSh/<name>_Sh`.
- **How the game sets an icon** (native HUD at `main+0x33B7E80`):
  1. it allocates a 0x40-byte icon controller, sets its vtable (`[main+0x4C973B0] + 0x10`) and fields, links it into
     the part's list and zeroes `+0x30` / `+0x38`;
  2. `main+0xA37320(controller, part)` creates the icon and shadow texture replacers at `controller+0x30` / `+0x38`
     (0x58 bytes each, from the engine heap);
  3. `main+0xA73920(controller->+0x30, &"Item_X", 0)` and `main+0xA73920(controller->+0x38, &"Item_X_Sh", 0)`.
- Calling `main+0xA73920` on the object at `nested ReplaceIcon frame + 0x6A8` overflowed the stack (game frozen):
  that object is not a ready replacer. The direct call stays behind `SLOT_ICON_DIRECT 0`.
- **Solution (commit f5ad284 and later):** the controllers are built by the game's own routine
  `main+0x33B7DA0(widget, heap)` (the Agony Stone icon one: it looks for `Pa_ReplaceIcon_00` in `widget+0x20`, builds
  the controller and sets `Item_AgonyStone`). It is called with a stand-in widget per button **during the PlayerStatus
  HUD init** (hook 12 at `main+0x33F5D20`, x0 HUD, x1 heap): that heap only accepts allocations during the init (later
  it returned a null controller and the game crashed). Hook 11 at `main+0xA37320` captures the created controller.
  The icons are then changed at any time with `main+0xA73920` on `controller+0x30` (name) and `+0x38` (`name_Sh`).

## Item index -> icon

- `main+0x592B20(manager, &name, item)` returns the item's actor name, which is also its icon texture name.
  `manager = **(main+0x4C7E0D0)`, default name `*(main+0x4C7DAD0)` (the HUD does the same before setting its icon).
- Item index = index of the equip call `main+0x1211C00`. Read live:
  0 Item_DekuStick, 1 Item_DekuNut, 2 Item_Bomb, 3 Item_Boomerang, 4 Weapon_Range_SlingShot, 5 Item_Hookshot,
  6 Item_Longshot, 7 Item_Hammer, 9 Item_Bombchu, 10 Item_DinFire, 11 Item_FaroreWind, 12 Item_NayruLove,
  13 Item_MagicBean, 14-17, 50 Item_Bottle_<content>, 18 Item_FishingRod, 30 Weapon_Range_Bow, 31 Item_WeirdEgg ..
  44 Item_ClaimCheck (trade items), 46 Item_Arrow_Fire, 47 Item_Arrow_Ice, 48 Item_Arrow_Light
  (8, 19-29, 45: empty in this save).
- **Bottles**: the five bottle cells are item indices **14, 15, 16, 17 and 50** (grid order BottleA..BottleE), not
  normal items. Their contents are the Enum
  `Shop_SelectBottleContentItem` (`Empty, RedPotion, GreenPotion, BluePotion, BlueFire, Fish, Letter, BigPoe, Poe,
  Bug, Fairy, MaxMilk, HalfMilk`); the five content records in GameData are the unnamed Enum indices **60, 61, 62,
  63, 64** for BottleA..BottleE (confirmed live: assigning cells 14-17 sets the box to BottleA..D, and cell 50 sets
  it to BottleE). The HUD reads the slot and draws `Item_Bottle_<content>` (`Empty` -> `Item_Bottle`), so the button
  shows the bottle that was assigned even though the item index itself resolves to the current bottle (e.g.
  `Item_Bottle_RedPotion`).
- **ZR** is the game's own item box (`PlayerStatus.AssignableItem.<age>`, an Enum: `BottleA..BottleE` when it holds
  a bottle). Its own HUD icon name is stale for the 2nd..5th bottle, so the HUD takes the box's `BottleA..E` value,
  reads the matching content record (60..64) and draws the same `Item_Bottle_<content>` icon.
- `ItemPattern` is the **framing** of the icon inside the button (frame 0 draws it oversized), not the item choice;
  the measured item -> frame table is applied per item (`item_pattern()` in `core/hud.c`). `ItemChange` is the icon's
  pop-in animation (frame 0 = hidden). `Type` changes nothing visible.

## Textures

`tools/make_buttons.py` draws the three button sets with shapes and text, without game material. Each style produces
its own `OotBtn*_*` textures and the installer copies only the set for the chosen style.
