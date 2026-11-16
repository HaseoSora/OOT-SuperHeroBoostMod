# GameBanana update 0.5.1

GameBanana has no public write API: uploading a file or editing a submission has to go through the website while
logged in. This file is the copy-paste material for that upload.

## 1. Update: title and text

**Update name**

```
0.5.1 - Enemy speed, R3 target, L3 sprint
```

**Update description**

```
0.5.1 reworks enemy speed (harder-combat movement + a separate projectile speed) and adds the new Controls:
target with R3 and sprint while holding L3. The 0.5.0 Longshot/DLSS/ReLink fixes are included.

IMPORTANT - LONGSHOT / HOOKSHOT
There has been a lot of feedback about Longshot problems since 0.4.0: crashes while loading a save or an area, a
rebuild that stopped near 90%, DLSS disappearing after a rebuild, and the app choosing the wrong builder. 0.5.0
fixed those; 0.5.1 includes the fixes and adds the new controls, so rebuild the game once with 0.5.1. If a crash
remains, attach logs/longshot_log.txt and the new file in bug-reports/.

ENEMY SPEED
- Movement now scales every base and attack speed together (walk, run, dash, jog, strafe, attack motions and the
  per-enemy attack speeds), the harder-combat method: enemies no longer slide or overshoot.
- Animation playback, attack cadence and projectile speed are independent, each with eleven multipliers from x0.5
  to x6 (plus off).
- Attack cadence scales the interval tables and the action timeouts; projectiles are a new, separate option.
- The beta enemy profiles set all four components to x2.

CONTROLS
- Target with R3: swaps ZL and R3 (R3 targets, ZL resets the camera). Set System > Options > Targeting Type to Hold.
- Hold L3 to sprint with the game's own sprint animation, without pressing A and without rolling.
- Manual shield: L stays reserved during hit reactions and hit-stop; R3 cancels unless the target-on-R3 swap is on.

APP
- New Controls section, enemy Projectiles selector and --enemy-proj / --target-r3 / --sprint-l3 flags.
- Windows, Linux (x86_64) and macOS (Apple Silicon) builds, plus the 0.5.1 presets zip for emulators.
```

## 2. File to attach to the update

`release/SuperHeroBoost-0.5.1-presets.zip` (12 named profiles, no executables).

SHA-256: `e446b0a756972b7ba437e0462e8bce206f895e72f46a4095ea27be068aca85f6` (also in `release/SuperHeroBoost-0.5.1-presets.zip.sha256`).

## 3. Submission description

Paste the contents of `docs/GAMEBANANA-DESCRIPTION.txt` (updated for 0.5.1, with the Longshot notice at the top and
the new file names).

## 4. Version fields

- The Mods submission **Version**: `0.5.1`.
- The Tools submission (`docs/GAMEBANANA-TOOL.md`): version `0.5.1`, with the Windows exe SHA-256 and the new
  Controls/enemy options.

## 5. Checklist

- [ ] Update created with the title and text above.
- [ ] `SuperHeroBoost-0.5.1-presets.zip` attached and marked as the active file.
- [ ] `SuperHeroBoost-0.5.0-presets.zip` archived.
- [ ] Submission description replaced with `docs/GAMEBANANA-DESCRIPTION.txt`.
- [ ] Version field of the submission set to `0.5.1`.
- [ ] Tools page version bumped and the exe SHA-256 updated (if you maintain it).
