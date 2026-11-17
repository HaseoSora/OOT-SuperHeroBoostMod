# GameBanana update 0.8.0

GameBanana has no public write API: uploading a file or editing a submission has to go through the website while
logged in. This file is the copy-paste material for that upload.

## 1. Update: title and text

**Update name**

```
0.8.0 - item quantities, put the sword away with A & minimap option
```

**Update description**

```
0.8.0 completes the item buttons: they show the quantity of consumables, the game's own ZR item comes back after a
slot use, and A while standing still puts the sword or the item in hand away. It adds the option to hide the corner
minimap and "no magic jar drops", boss speed and an L3 sprint toggle, and fixes the mod's HUD buttons stealing the
cursor in shops, dialogues, the game-over screen and Farore's Wind.

IMPORTANT - REBUILD ONCE
The module changed: rebuild the game once with 0.8.0 (Longshot / Hookshot / ReLink) or reinstall the profile (emulator).

ITEM BUTTONS
- B / L / R / ZR show how many you have of the consumables: sticks, nuts, bombs, seeds, bombchus, beans and arrows.
  Unique items (boomerang, hookshot, bottles, trade items) show no number.
- ZR is always the game's own item (R selector, pause menu A, the save). A slot item is used through the box and the
  box goes back to the ZR item once Link stands or walks again, not while aiming; assigning ZR to a button swaps them.

PUT THE SWORD AWAY
- With an item on B, A while standing still puts the sword or the item in hand away (B's own function); A still talks,
  opens and rolls as usual when you move or when there is something to use.

MENUS FIXED
- The mod's HUD buttons kept the game's item-box "focusable" flag: in shops, dialogues, the game-over screen, Farore's
  Wind and past the Megaton Hammer on the Items page you had to press up / down a few times first. They are no longer
  focusable.

NEW OPTIONS
- HUD: hide the corner minimap while playing (the map screen still works).
- Difficulty: dropped magic jars become green rupees, like the heart option; both can be on together.
- Beta: boss speed, with its own movement and animation multipliers for bosses and minibosses.
- Controls: L3 sprint as a toggle (one press on, the next off; it stops when stamina runs out, when A is pressed and in
  dialogues).

ALSO IN 0.7.0
- Souls-like targeting, Souls controls profiles and HUD labels in the game's language.
```

## 2. File to attach to the update

`release/SuperHeroBoost-0.8.0-presets.zip` (14 named profiles, no executables).

SHA-256: `269d7929dd9f08f26e278676b470a44176c3a564fea93a95711b2e8b3f8f17db`

## 3. Submission description

Paste the contents of `docs/GAMEBANANA-DESCRIPTION.txt` (updated for 0.8.0).

## 4. Version fields

- The Mods submission **Version**: `0.8.0`.
- The Tools submission (`docs/GAMEBANANA-TOOL.md`): version `0.8.0`, with the Windows exe SHA-256
  `046f40cb94ddab8cca574dfb5fe2091291b04fb588579326260ef49ad3c1ca29`.

## 5. Checklist

- [ ] Update created with the title and text above.
- [ ] `SuperHeroBoost-0.8.0-presets.zip` attached and marked as the active file.
- [ ] `SuperHeroBoost-0.7.0-presets.zip` (file 1893817) archived.
- [ ] Submission description replaced with `docs/GAMEBANANA-DESCRIPTION.txt`.
- [ ] Version field of the submission set to `0.8.0`.
- [ ] Tools page version bumped to `0.8.0` and the exe SHA-256 updated.
