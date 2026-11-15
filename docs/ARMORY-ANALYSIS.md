# Hyrule Armory Sync: analysis and the boots/masks selector

Analysis of the third-party **Hyrule Armory Sync v1.0** module (`subsdk5` + IPS for main, update v131072,
Build ID `E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348`) to see how it adds the sword/shield drawer and whether
the same mechanism can add **boots** and **masks**.

Addresses below are guest addresses for the lift (`main` base `0x80000000`). The Armory module is linked at
**`0x4E97000`**: text `0x0..0x20EC`, rodata `0x3000`, data `0x4000`, bss `0x200`.

## Short version

The mod does **not** draw a custom drawer. It switches the **native item drawer** to the game's **equipment
array** and filters that array to swords/shields. The game's equipment array already contains the tunics, masks
and boots (its name table is at `main+0x3F13610`). The drawer code supports 1-8 rows and the native equip path
is unchanged. Therefore a boots/masks selector is mostly **letting the other equipment rows through**, not
writing a new UI.

## How the module is loaded

- `main` is patched at 6 text call sites and several data/rodata sites. The text sites branch to **stubs** in a
  rodata cave (`main+0x3C47450..0x3C47920`).
- Each stub loads a function pointer from the Armory module's GOT (`0x4E9B000 + 0x58/0x68/0x80/0x88/0x90`)
  and branches to it; if the pointer is null it branches back to the original game function. The module's init
  (`0x4E97020`) finds the `main` base by scanning memory, verifies the patched instruction words and fills the
  GOT. This makes the mod self-relocating and lets it fall back cleanly when the module is absent.
- The module calls `main` functions as `main_base + constant` (e.g. `main+0x33ABED0`, `main+0xA7ACD4`); it does
  not need a relocation table for those.

## The drawer mode switch

The item drawer's list builder is in `main+0x80A6DBC0`. Its first call (`main+0x80A6E150`) chooses the data
source:

- normal items: `main+0xA6F730`;
- equipment array: `main+0xA6F790`.

The mod's hook replaces that call: holding **L/L1** switches the getter to the equipment array. The rest of the
builder then iterates the array and calls the "add row/item" helpers (`0x80A6EF20`, `0x80596AF0`), which the mod
also hooks.

The mod's **filter table** is at `0x4E97C00`, eight `0x20`-byte entries:

| flag | name |
|---|---|
| `0x01` | `Weapon_Sword_Kokiri` |
| `0x02` | `Weapon_Sword_Master` |
| `0x02` | `Weapon_Sword_Giant` |
| `0x02` | `Weapon_Sword_Biggoron` |
| `0x02` | `Weapon_Sword_BrokenGiant` |
| `0x01` | `Weapon_Shield_Deku` |
| `0x03` | `Weapon_Shield_Hylian` |
| `0x02` | `Weapon_Shield_Mirror` |

Flag bit 0 = child, bit 1 = adult. The hook at `0x4E97984` scans this table and only adds a name that matches.
That is the **only** reason the drawer shows just swords and shields.

## The game's equipment array

`main+0x3F13610` holds the full equipment name table in array order:

- swords: `Weapon_Sword_Kokiri`, `_Master`, `_Giant`, `_Biggoron`, `_BrokenGiant`
- shields: `Weapon_Shield_Deku`, `_Hylian`, `_Mirror`
- tunics: `Obj_Armor_Child_Normal`, `Armor_Adult_Normal`, `Armor_Adult_Goron`, `Armor_Adult_Zora`
- masks: `Armor_Child_Mask_Keaton`, `_Skull`, `_Spooky`, `_Bunny`, `_Truth`, `_Goron`, `_Zora`, `_Gerudo`,
  `_Amiibo0`, `_Amiibo1`, `Armor_GlassTruth`
- boots: `Armor_Adult_HoverBoot`, `Armor_Adult_HeavyBoot`

The array therefore has **5 rows** (swords, shields, tunics, masks, boots). The mod's drawer hook keeps a
row mask (`0x160`) with four bits per row and an item-presence mask (`0x144`), and the drawer code accepts 1-8
rows (`cmp w8, #7`). Five rows fit.

## Drawer, cursor and equip

- The drawer hooks are in `main+0x833C8B80`, `0x833C8FB0`, `0x833C9620` and `0x833F9560`; the module's
  `0x4E98294`/`0x4E985D8` functions reuse the native grid: `0x168`/`0xB4` row/tile constants, the native
  cursor panes `N_Cursor_00` / `P_CursorSh_00`, the arrows `N_Arrow_00/01`, and the text/guide panes
  `T_Text_00`, `Pa_SortWindow_00`, `Pa_Guide_00`.
- The native equip request enters at `main+0x80A7ACD0` (`pacibsp`) and its body starts at `+0xA7ACD4`; the
  arguments are `equip(pouch, name_ref, kind, arg3)`. The mod's pre-hook at `0x4E97458` logs the request
  (`[equip-probe] ...`) and tail-calls the original body. The native drawer already does the equip; the mod
  only logs/validates it.
- The module adds "Unequip Sword"/"Unequip Shield" cells at `0x4E98DEC/DF0`; a full equipment drawer would need
  equivalent cells for the other rows, or the player can unequip from the pause menu.

## Test patch

`release/HyruleArmorySync-all-equipment-test.zip` (local test, not a release) replaces the filter with "accept
every name, use the game's item index":

- At `0x4E979F8` the eight-entry name check is replaced by
  `ldr w10, [sp, #0x20]` (the game's item index) and a branch to the mask update at `0x4E97A4C`.
- The module text SHA-256 in the NSO header (`0xA0`) is recomputed.
- No IPS change.

Put its `exefs/subsdk5` next to the original IPS in Lichii (back up the original first) and hold **L/L1**.
If the native equipment array is used as expected, the drawer should show the extra rows (tunics, masks,
boots). This validates the approach before porting it to our module.

## What this means for our mod

- **Native drawer route (recommended)**: switch the drawer to the equipment array and accept the rows we want
  (masks/boots, or all equipment). The game provides the icons, cursor, grid and equip path, so there is no
  custom UI or equip request to reverse-engineer. The Armory module proves the mode switch and row masks work.
- **Custom HUD route (fallback)**: draw our own boots/mask row and apply the selection through the native equip
  path (`main+0xA7ACD0`) using the `pouch` object and a `name_ref`; writing the GameData `EquipBoot` /
  `EquipHeadArmor` string alone does not update the live equipment array immediately.
- The current `quick-select` feature writes the String64 records directly; that is why it needs the equip path
  (or the native drawer) to apply a selection at once.
