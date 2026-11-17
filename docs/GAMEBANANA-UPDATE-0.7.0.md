# GameBanana update 0.7.0

GameBanana has no public write API: uploading a file or editing a submission has to go through the website while
logged in. This file is the copy-paste material for that upload.

## 1. Update: title and text

**Update name**

```
0.7.0 - souls-like target switch & Souls controls
```

**Update description**

```
0.7.0 brings souls-like targeting: while locked on, tap the target button to move the lock to the enemy the game
marks in red, hold it to drop the target, and the next enemy is locked on when the current one dies. Two Souls
controls profiles put it together with the stamina bar, R3 lock-on and the manual shield, and the mod's own HUD labels
now follow the game's language.

IMPORTANT - REBUILD ONCE
The module changed: rebuild the game once with 0.7.0 (Longshot / Hookshot / ReLink) or reinstall the profile (emulator).

SWITCH TARGET
- While locked on, tap the target button (ZL, or R3 with the ZL/R3 swap) to move the lock to the enemy the game marks
  in red: the nearest one that is not locked.
- Hold it (about 0.3 s) to drop the target; with no target the button locks on as usual.
- It works through the game's own attention list, so the camera, the lock triangles and the red marker follow.
- Its own option in Controls. Needs System > Options > Targeting Type on Toggle.

NEXT TARGET
- Its own option in Controls, independent of the manual shield.
- It follows the game's real lock and acts only when the locked enemy dies; walking near enemies, the battle stance
  or a target you drop yourself no longer lock on by themselves.

MANUAL SHIELD
- The target button always reaches the game: it used to be re-created from the player's action names, which also
  appear near enemies without a target, so the game locked on by itself.
- "Targeting" is the game's own lock; R3 still cancels when the ZL/R3 swap is off.

HUD LABELS AND ENEMY DUPLICATOR
- Jump / Attack / Roll and the pause menu's Assign: follow the game's language (the app's language is the fallback).
- The enemy duplicator doubles Stalchildren too and no longer turns on spawns the game keeps off.

ALSO IN 0.6.0
- ReLink fix, button positions and game prompts; 0.5.1's enemy speed and controls.
```

## 2. File to attach to the update

`release/SuperHeroBoost-0.7.0-presets.zip` (14 named profiles, no executables).

SHA-256: `93b236e73f1df67de68f6ce499336fa990dc25d0d4092c273d3de2f9fbb19902` (also in
`release/SuperHeroBoost-0.7.0-presets.zip.sha256`).

## 3. Submission description

Paste the contents of `docs/GAMEBANANA-DESCRIPTION.txt` (updated for 0.7.0, with the Longshot notice, the 0.7.0
changes and the new file names).

## 4. Version fields

- The Mods submission **Version**: `0.7.0`.
- The Tools submission (`docs/GAMEBANANA-TOOL.md`): version `0.7.0`, with the Windows exe SHA-256
  `18fc679315b85061c3010c2414be3da47e2024fcc7c76b678275b8eb2983ad3e` and the new targeting options.

## 5. Checklist

- [ ] Update created with the title and text above.
- [ ] `SuperHeroBoost-0.7.0-presets.zip` attached and marked as the active file.
- [ ] `SuperHeroBoost-0.6.0-presets.zip` (file 1893661) archived.
- [ ] Submission description replaced with `docs/GAMEBANANA-DESCRIPTION.txt`.
- [ ] Version field of the submission set to `0.7.0`.
- [ ] Tools page version bumped to `0.7.0` and the exe SHA-256 updated.
