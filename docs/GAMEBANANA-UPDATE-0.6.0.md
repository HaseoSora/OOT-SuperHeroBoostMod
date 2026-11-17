# GameBanana update 0.6.0

GameBanana has no public write API: uploading a file or editing a submission has to go through the website while
logged in. This file is the copy-paste material for that upload.

## 1. Update: title and text

**Update name**

```
0.6.0 - ReLink fixed, button positions & game prompts
```

**Update description**

```
0.6.0 makes every feature work under ReLink, refines the manual shield, adds the button positions and separates the
game's own button prompts. The 0.5.1 enemy speed and controls remain.

IMPORTANT - REBUILD ONCE
The module changed: rebuild the game once with 0.6.0 (Longshot / Hookshot / ReLink) or reinstall the profile (emulator).
For Longshot and Hookshot, the 0.5.0 crash fixes, DLSS/FSR and the builder detection remain.

RELINK - EVERY FEATURE WORKS
ReLink's translator writes each function in address order and starts at its lowest address. A backward tail call made
the caller's own start unreachable, so the input dispatcher ran only the quick select: stamina never drained (and
flashed yellow on every action), the manual shield's L, the button mapping assignment and R3/L3 did nothing. The module
is now built without tail calls and the build fails if one appears. Rebuild the game once.

MANUAL SHIELD
- With Hold targeting only the held target button counts as a target (the game's lock-on state lingers after release
  and after attacks, which raised the shield without a target).
- With no target, L keeps its default game function; it is ours only while targeting or guarding, until released.

BUTTON POSITIONS
- New option: Nintendo (default), A and B swapped or Xbox (A/B and X/Y swapped), to match Longshot or ReLink.
- The HUD and the pause menu draw each face button, its item and its label where it is on the controller; the game's
  Swap Jump Controls still applies on top.

GAME BUTTON PROMPTS
- Separate, optional choice in the HUD section: None / PlayStation / Xbox (None by default).
- The button style only picks the button mapping's own pictures; Longshot and ReLink already ship their own prompts.

APP
- Play button, themed scrollbars and a red "Requires rebuild" tag on a recompiled game.
- New --bm-layout and --game-layout flags.
- Windows, Linux (x86_64) and macOS (Apple Silicon) builds, plus the 0.6.0 presets zip for emulators.

ALSO IN 0.5.1
- Enemy speed: all movement speeds together, separate animation, attack cadence and projectiles.
- Controls: target on R3, sprint while holding L3.
```

## 2. File to attach to the update

`release/SuperHeroBoost-0.6.0-presets.zip` (12 named profiles, no executables).

SHA-256: `7aab3b39413838143b6db945af8a5916d1c8387069d5448340e622499793fe11` (also in `release/SuperHeroBoost-0.6.0-presets.zip.sha256`).

## 3. Submission description

Paste the contents of `docs/GAMEBANANA-DESCRIPTION.txt` (updated for 0.6.0, with the Longshot notice and the ReLink
fix at the top and the new file names).

## 4. Version fields

- The Mods submission **Version**: `0.6.0`.
- The Tools submission (`docs/GAMEBANANA-TOOL.md`): version `0.6.0`, with the Windows exe SHA-256 and the new app
  options (Play, rebuild tags, button positions, game prompts).

## 5. Checklist

- [ ] Update created with the title and text above.
- [ ] `SuperHeroBoost-0.6.0-presets.zip` attached and marked as the active file.
- [ ] `superheroboost-051-presets.zip` archived.
- [ ] Submission description replaced with `docs/GAMEBANANA-DESCRIPTION.txt`.
- [ ] Version field of the submission set to `0.6.0`.
- [ ] Tools page version bumped and the exe SHA-256 updated (if you maintain it).
