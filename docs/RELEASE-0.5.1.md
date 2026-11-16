# Super Hero Boost 0.5.1

This release reworks enemy speed (movement that scales every speed together, a separate projectile speed), adds the
**Controls** section (target on **R3**, **L3** sprint) and keeps the 0.5.0 Longshot, DLSS/FSR and ReLink fixes.

## Longshot / Hookshot

0.5.0 fixed the crashes introduced in 0.4.0 (the machine-outliner flags in the HUD). 0.5.1 includes those fixes and
adds the controls and enemy options, so **rebuild the game once with 0.5.1**. If a crash remains, attach
`logs/longshot_log.txt` and the new file in `bug-reports/`. DLSS/FSR are kept on rebuild; ReLink is supported.

## Download

| Your system | File |
|---|---|
| Windows | `SuperHeroBoostConfig.exe` - the configuration app (the module payload is bundled inside). |
| Linux (x86_64) | `SuperHeroBoostConfig-linux` - `chmod +x SuperHeroBoostConfig-linux` after downloading. |
| macOS (Apple Silicon) | `SuperHeroBoostConfig-macos.dmg` - open it and drag the app to Applications. It is not signed, so the first time use right-click > Open. |
| Emulator / manual | `SuperHeroBoost-0.5.1-presets.zip` (+ `.sha256`) - all 12 named app profiles as ready-to-install mod folders, no executables. |

## What's new

**Enemy speed reworked**
- Movement now scales every base and attack speed together: walk, run, dash, jog, strafe, attack motions and the
  per-enemy attack speeds, so enemies no longer slide or overshoot.
- **Animation playback**, **attack cadence** and **projectile speed** are independent, each with eleven multipliers
  from x0.5 to x6 (plus off).
- Attack cadence scales the interval tables and the action timeouts; projectile speed is a new, separate option.
- The beta enemy profiles set all four components to x2.
- The enemy data is generated from your own dump and installed as romfs files; reinstall the profile to update it.

**Controls**
- **Target with R3**: swaps ZL and R3, so R3 holds or toggles the target camera and ZL resets it. Recommended with
  the game's **Hold** targeting type.
- **Hold L3** to sprint: uses the game's sprint flag and animation, without pressing A and without rolling.
- Both are personal preferences, off by default, and not part of a profile.

**Manual shield**
- L stays reserved while the shield is enabled: it never triggers its item/selector/default function, including
  during shield-hit reactions and hit-stop.
- R3 cancels targeting unless the target-on-R3 swap is enabled.

**App**
- New **Controls** section, enemy **Projectiles** selector and `--enemy-proj`, `--target-r3` and `--sprint-l3`
  command-line flags.
- The enemy-speed generator uses one data layout for movement, animation, attack cadence and projectiles in a single
  manifest; reinstall the profile after updating.

## Everything from 0.5.0

- Longshot 0.4.0 crashes fixed (the module is built without the machine outliner).
- DLSS and FSR are kept when rebuilding; the SDK is read from the launcher and a missing DLSS SDK stops the build
  instead of silently removing DLSS.
- ReLink support and the correct builder for Longshot, Hookshot and ReLink on Windows, Linux and macOS.
- The app closes a running copy of the game before and during the build, instead of stopping near 90%.
- Manual shield, Swap Jump Controls button mapping and the quick-select clock cleanup.
- Full backup/restore on uninstall, including the ReLink files; generated caches are deleted, not copied.

## Install

1. Requires the game on update **v131072**.
   - **Emulator**: it must load mods from `user/load/0400486024DEC000`.
   - **Longshot / Hookshot / ReLink**: use the app's target and let it detect the builder; rebuild once with 0.5.1.
2. Back up your saves. On Windows the app closes the game before installing or rebuilding.
3. Run `SuperHeroBoostConfig.exe`, pick a profile or tune the sections, select your emulator/game folder and press
   **Install** (or **Rebuild game** for a static recompilation).
4. Emulator presets can also be installed by hand: copy the `00-Super-Hero-Boost` folder of the chosen profile from
   the presets zip into `user/load/0400486024DEC000`.

## Notes

- Translations: Spanish, English, Portuguese, French, German and Italian.
- The app checks GitHub Releases on startup and offers the new version.
- Source, issues and documentation: https://github.com/kuribox/OOT-SuperHeroBoostMod
