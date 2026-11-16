# Super Hero Boost 0.5.0

This release fixes the Longshot crashes introduced in 0.4.0, keeps DLSS/FSR when the game is rebuilt, adds ReLink,
finds the right builder on Windows, Linux and macOS, and closes a running game instead of stopping the build at its
final step.

## Longshot notice

There has been a lot of feedback about Longshot since 0.4.0: crashes while loading a save or an area, a rebuild that
stopped near 90% with "Longshot is still running from this folder", DLSS disappearing after a rebuild, and the app
picking a ReLink or Hookshot builder for a Longshot game. This update is meant to fix all of those. The module
changed, so **rebuild the game once with 0.5.0** (Install / Rebuild game); after that `image.bin` contains the fixed
module. If a crash remains, attach `logs/longshot_log.txt` and the new file in `bug-reports/` to the report.

## Download

| Your system | File |
|---|---|
| Windows | `SuperHeroBoostConfig.exe` - the configuration app (the module payload is bundled inside). |
| Linux (x86_64) | `SuperHeroBoostConfig-linux` - `chmod +x SuperHeroBoostConfig-linux` after downloading. |
| macOS (Apple Silicon) | `SuperHeroBoostConfig-macos.dmg` - open it and drag the app to Applications. It is not signed, so the first time use right-click > Open. |
| Emulator / manual | `SuperHeroBoost-0.5.0-presets.zip` (+ `.sha256`) - all 12 named app profiles as ready-to-install mod folders, no executables. |

The Windows build is the only one with an `.exe` extension; the Linux build is a plain executable named `-linux` and
macOS ships as a `.dmg` with the `.app` bundle inside.

## What's new

**Longshot 0.4.0 crashes fixed**
- 0.4.0 was built with `-Oz`, which enables LLVM's machine outliner. It moved the pointer guards into shared
  `OUTLINED_FUNCTION_n` helpers that end in `cmp` + `ret`, and the callers branched on those flags.
- Longshot's recompiler does not keep the condition flags of a `cmp` that ends a function, so after the call the
  `b.lo` used stale flags, the guard was skipped and a null pointer reached the HUD. Two observed crashes were
  `read 0x100000000038, guest 0x38` and `read 0x100000000080, guest 0x80` in `hud_on_code`.
- The module is now built with `-mllvm -enable-machine-outliner=never`, so every guard comparison stays inline.
  This is a module change: rebuild the game once.

**DLSS and FSR are kept on rebuild**
- The app reads the launcher's own settings (`LongshotLauncher`/`HookshotLauncher` `settings.json` + `builds.json`,
  `ReLink` `launcher.ini`), points `LONGSHOT_NGX_SDK`/`RELINK_NGX_SDK` at the SDK the launcher keeps and passes
  `--fsr` when the game had FSR.
- If the game had DLSS and the SDK is missing, the build stops with a message instead of silently compiling without
  DLSS and deleting the `ngx` runtime. If the launcher is not installed, the game's own `longshot_options.ini` /
  `relink_options.ini` is used as a fallback.

**ReLink support**
- A third static recompilation: `.relink_exefs`, `bin/relink-game`, `ReLink.exe`, the `RELINK_*` environment and the
  builder under `%LOCALAPPDATA%\ReLink\versions\<version>\ReLink` (or the Linux/macOS data folder). The install, backup and builder detection are tested; the full build has not been verified on a real ReLink install yet.
- Its renderer, `amd_fidelityfx_vk` library, VC runtime and item-wheel assets are backed up and restored like the
  rest.

**The right builder, on every OS**
- Longshot, Hookshot and ReLink use their own builder: the game's flavor decides which launcher folder is searched,
  so a ReLink or Hookshot builder is never picked for a Longshot game.
- Linux uses `$XDG_DATA_HOME` or `~/.local/share` and `~/.config`; macOS uses `~/Library/Application Support`.
  The builders' programs are `bin/longshot` and `bin/relink-game` without `.exe`, and `make_game.py` runs with the
  builder's own `tools/python/bin/python3` (or a system `python3` when the app is packaged).
- The builder path is optional in the app: it shows whether the builder was detected and allows choosing another
  folder.

**No more stop at about 90%**
- On Windows a running executable cannot be replaced. The app now closes any copy of the game running from the game
  folder (the root launcher, `bin/longshot.exe`, an older `longshot-game.exe`, a visible or hidden window) before the
  install and keeps checking while the build runs, so the builder reaches the final swap.
- It still asks you to close a copy it cannot close (another user's or an elevated process).

**Manual shield**
- ZL follows the game's **System > Options > Targeting Type**: hold to target in **Hold Target**, press to toggle in
  **Toggle Target**.
- Hold L to raise the shield while the target camera is active; **R3** cancels targeting.
- While it is enabled, L is removed from buttonMapping (its item slot is off), because L is the shield button.

**Button mapping**
- Follows the game's **Swap Jump Controls** option: the B item slot moves to X and the Jump label moves to B.
- B/L/R/ZR item buttons, the simple/extended layouts, the L item/selector modes and the three button styles are
  unchanged.

**Quick select**
- Removed the debug text that replaced the clock with `HOVER` / `HIERRO` / `MASCARA` / `LENTES` after a switch. The
  clock always shows the time; the D-pad switches behave as before.

**Install and uninstall**
- The backup records every file the install and the rebuild touch and restores exactly that, including the ReLink
  files. The generated shader, program and pipeline caches (some are hundreds of MB) are not copied and are deleted
  on uninstall, so a cache of the modded build cannot meet the restored game.
- The module id check refuses a game whose `main` is not the supported build `e0f3ccfa`.

## Everything from 0.4.0

- Three HUD layouts: Wide, Simple and Minimal.
- Exact bottle icons on the B/L/R/ZR buttons.
- Enemy speed (movement, animation and attack cadence) and duplicated-enemy placements.
- Optional compact segmented stamina bar.
- Longshot Vulkan fallback when the builder cannot find Vulkan/VMA headers.

## Install

1. Requires the game on update **v131072**.
   - **Emulator**: it must load mods from `user/load/0400486024DEC000`.
   - **Longshot / Hookshot / ReLink**: use the app's target and let it detect the builder; rebuild once with 0.5.0.
2. Back up your saves. The app closes the game on Windows if it is running, but save first.
3. Run `SuperHeroBoostConfig.exe`, pick a profile or tune the sections, select your emulator/game folder and press
   **Install** (or **Rebuild game** for a static recompilation).
4. Emulator presets can also be installed by hand: copy the `00-Super-Hero-Boost` folder of the chosen profile from
   the presets zip into `user/load/0400486024DEC000`.

## Notes

- Translations: Spanish, English, Portuguese, French, German and Italian.
- The app checks GitHub Releases on startup and offers the new version.
- Source, issues and documentation: https://github.com/kuribox/OOT-SuperHeroBoostMod
