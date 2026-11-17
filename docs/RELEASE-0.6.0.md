# Super Hero Boost 0.6.0

0.6.0 makes **every feature work under ReLink**, refines the **manual shield**, adds the **button positions** and
separates the **game's own button prompts** from the button mapping style. The 0.5.1 enemy speed and controls remain.

## ReLink: every feature works

ReLink's translator writes each function in address order and starts at its lowest address. A **tail call** (`b f` in
place of `bl f; ret`) to a function placed **lower** in the module made the caller's own start unreachable. Under ReLink
the input dispatcher ran only the quick select, so:

- stamina never drained (and flashed yellow on every action),
- the manual shield's **L** did nothing,
- the **button mapping assignment** did nothing,
- the **R3 / L3** controls did nothing.

The module is now built **without tail calls**, and the build fails if one appears. **Rebuild the game once with 0.6.0**
so the new module is baked into the executable.

## Manual shield

- With **Hold** targeting, only the held target button counts as a target: the game's lock-on state lingers after
  release and after attacks, which raised the shield without a target.
- With **no target**, L keeps its default game function; it is ours only while targeting or guarding, until it is
  released.

## Button positions

- New button mapping option: **Nintendo** (default), **A and B swapped** or **Xbox** (A/B and X/Y swapped), to match the
  button layout chosen in Longshot or ReLink.
- The HUD and the pause menu draw each face button, its item and its label where it is on the controller; the game's
  **Swap Jump Controls** option still applies on top.

## Game button prompts

- Separate, optional choice in the **HUD** section: **None / PlayStation / Xbox** (None by default).
- The button style now only picks the button mapping's own pictures; Longshot and ReLink already ship their own prompts.

## App

- **Play** button: opens the emulator or the recompiled game's launcher.
- The scrollbars follow the app's theme.
- On a recompiled game, the main switch of each feature shows a red **Requires rebuild** tag (sub-options do not).
- New `--bm-layout` and `--game-layout` command-line flags.
- The mod folder is `zz-Super-Hero-Boost` so its resource size table wins over other mods (the loader lets the mod
  whose path sorts last win each file); the tables of the other installed mods are merged into ours, so a costume pack
  keeps its sizes.

## Download

| Your system | File |
|---|---|
| Windows | `SuperHeroBoostConfig.exe` - the configuration app (the module payload is bundled inside). |
| Linux (x86_64) | `SuperHeroBoostConfig-linux` - `chmod +x SuperHeroBoostConfig-linux` after downloading. |
| macOS (Apple Silicon) | `SuperHeroBoostConfig-macos.dmg` - open it and drag the app to Applications. It is not signed, so the first time use right-click > Open. |
| Emulator / manual | `SuperHeroBoost-0.6.0-presets.zip` (+ `.sha256`) - all 12 named app profiles as ready-to-install mod folders, no executables. |

## Everything from 0.5.1

- **Enemy speed**: movement scales every base and attack speed together (walk, run, dash, jog, strafe, attack motions
  and the per-enemy attack speeds); **animation playback**, **attack cadence** and **projectile speed** are independent,
  each with eleven multipliers from x0.5 to x6 (plus off).
- **Controls**: target on **R3** (swaps ZL/R3; use the game's Hold targeting type) and **L3** to sprint with the game's
  own sprint animation, without rolling.
- **Manual shield**: L reserved while enabled, including hit reactions and hit-stop.
- **App**: Controls section, enemy Projectiles selector and `--enemy-proj`, `--target-r3` and `--sprint-l3`.
- The 0.5.0 fixes: Longshot crashes, DLSS/FSR on rebuild, ReLink support, builder detection on Windows, Linux and macOS
  and closing the running game before a build.

## Install

1. Requires the game on update **v131072**.
   - **Emulator**: it must load mods from `user/load/0400486024DEC000`.
   - **Longshot / Hookshot / ReLink**: use the app's target and let it detect the builder; **rebuild the game once with
     0.6.0** for the new module.
2. Back up your saves. On Windows the app closes the game before installing or rebuilding.
3. Run `SuperHeroBoostConfig.exe`, pick a profile or tune the sections, select your emulator/game folder and press
   **Install** (or **Rebuild game** for a static recompilation).
4. Emulator presets can also be installed by hand: copy the `zz-Super-Hero-Boost` folder of the chosen profile from the
   presets zip into `user/load/0400486024DEC000`.

For ReLink, do not keep a separate controller-UI mod installed: the app now installs the game's own prompts (the HUD
section) and the module's table, and warns if another mod replaces the button font or the UI atlas.

## Notes

- Translations: Spanish, English, Portuguese, French, German and Italian.
- The app checks GitHub Releases on startup and offers the new version.
- Source, issues and documentation: https://github.com/kuribox/OOT-SuperHeroBoostMod
