# Super Hero Boost 0.8.0

0.8.0 finishes the item buttons: they show the quantity of consumables, ZR is always the game's own item, and **A
while standing still puts the sword / item away**. It adds two HUD/drop options (**hide the corner minimap** and **no
magic jar drops**), **boss speed**, an **L3 sprint toggle**, and fixes the mod's HUD buttons stealing the cursor in
shops, dialogues, the game-over screen and Farore's Wind. The 0.7.0 souls-like targeting, Souls controls profiles and
HUD labels in the game's language remain.

## Item buttons: quantities and the game's ZR

- B / L / R / ZR show the **quantity** of the consumables: sticks, nuts, bombs, seeds, bombchus, beans and arrows.
  Unique items (boomerang, hookshot, bottles, trade items ...) show no number.
- **ZR is always the game's own item** (R selector, pause menu A, the save). A B / L / R item is used through the item
  box, which goes back to the ZR item once Link stands or walks again; not while aiming, so a bow on R shoots its own
  arrow and a held item is not put away. A tap uses the item too.
- Assigning the ZR item to a button, or a button's item to ZR, swaps them for real: the game's own box takes the new ZR
  item and no item ends up on two buttons.

## Put the sword / item away with A

- With an item on B, **A while standing still** puts the sword or the item in hand away (B's own function); A still
  talks, opens and rolls as usual when you move or when there is something to use.

## Menus with invisible options (fixed)

- The mod's HUD buttons are clones of the game's item box and kept its "focusable" flag, so the cursor went onto them:
  past the Megaton Hammer on the Items page, and in shops, dialogues, the game-over screen and the Farore's Wind menu
  you had to press up / down a few times before the real options responded. They are no longer focusable.
- The songbook no longer reads the ocarina while it is closed.

## Hide the corner minimap

- New option in **HUD**: the corner map is not drawn while you play, its compass/player arrow included. The map screen
  (Minus) still works.

## No magic jar drops

- New option in **Difficulty**: dropped magic jars become green rupees, like the heart option. Both options can be on at
  the same time (the installer uses one combined file for the drop table).

## Boss speed (beta)

- Bosses and minibosses (dungeon bosses, Dark Link, Iron Knuckles, Flare Dancer, Dead Hand, the Poe sisters' Meg ...)
  are left out of the enemy speed; they now have their own **movement** and **animation** multipliers in the Beta tab,
  built the same way from your game dump.
- Some bosses move by script (Morpha, Volvagia, Bongo Bongo): animation is what speeds them up.

## L3 sprint as a toggle

- New sub-option of the L3 sprint: one press of L3 starts the sprint and the next one stops it. It also stops when
  stamina runs out, when you press A (your own roll / sprint takes over) and in dialogues and shops.

## Enemy duplicator (beta)

- Stalchildren now double as well. Each spawn zone in the maps carries its own group size (2 small, 1 big, larger
  groups by the road); the duplicator only cloned hand-placed enemies and never touched those zones. It now doubles
  every count of the spawn zones and the scene's cap on them.
- It no longer turns on spawns the game keeps off: adult Link got Stalchildren from the doubled "0" of the adult spawn.

## What 0.7.0 brought (still included)

- **Souls-like targeting:** tap the target button (ZL, or R3 with the ZL/R3 swap) to move the lock to the enemy the
  game marks in red; hold it to drop the target; with no target it locks on as usual.
- **Next target when the locked enemy dies**, independent of the manual shield, following the game's real lock.
- **Souls controls** profiles, the manual shield with the target button left to the game, the button positions and the
  HUD labels in the game's language (the app reads it; `--lang` forces one).
- The 0.6.0 ReLink fix and the enemy speed components remain.

## Updating

- **Emulator:** install 0.8.0 from the app.
- **Longshot, Hookshot and ReLink:** install 0.8.0 and **rebuild the game once**: the module changed.
- Set System > Options > Targeting Type to **Toggle** for the switch and next target.
