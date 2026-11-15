# Super Hero Boost 0.2.1

Patch release: the configuration app now checks GitHub Releases for updates and can install them by itself.
Everything from 0.2.0 is included (Longshot support and the save-start crash fix).

## Download

- `SuperHeroBoostConfig.exe` — the configuration app for Windows (the module payload is bundled inside).
  SHA-256: `974c64fabdb9ebc897ccea95f23f46e9bba72c8a36f5e862cbf9d66e785463ff`
- `SuperHeroBoost-0.2.1-presets.zip` — all 11 app profiles as ready-to-install mod folders for emulators, with no
  executables. SHA-256: `d8a5089cf102bd61f6409792e2ab6ae1136c9c1094b0b79f188749dce9963b9e`

## What's new

**Automatic updates**
- On startup the app asks GitHub for the latest release in the background. If it is newer, a bar appears under the
  header with **Download** and **Later**; **Check for updates** is also available in *About*.
- The new executable is downloaded to a `.part` file, its SHA-256 is checked against the asset digest from the
  GitHub API when available, and only then installed.
- On Windows, a frozen build in a writable folder replaces itself and restarts (a small detached PowerShell helper
  waits for the app to close). In a read-only folder, or when running from source, the file is saved to
  `%LOCALAPPDATA%\SuperHeroBoostConfig\updates` and the app shows its path.
- Network errors and API rate limits never block the window: the automatic check is silent; only the manual check
  shows a message.

**Presets zip**
- `tools/build_app.py` now also writes `SuperHeroBoost-<version>-presets.zip`: every profile of the app as its own
  `00-Super-Hero-Boost` folder (module, IPS patch, Switch button textures and the optional romfs files that profile
  uses), ready for a GameBanana Mods upload. No executables inside.

**Note for 0.2.0 users**
- The 0.2.0 executable was published before this feature, so it cannot update itself. Download 0.2.1 once; from
  then on the app updates itself.

## Everything from 0.2.0

- **Longshot support (tested)**: the app patches `main`, copies the module to `.longshot_exefs`, installs the romfs
  options and runs the builder's update with progress, log and cancel. Longshot saves and the HUD, stamina, item
  buttons and collectibles work. **Hookshot** uses the same builder and procedure but is not tested yet.
- **Save-start crash fixed**: the HUD's collectibles reader dereferenced a stale GameData manager pointer in
  Longshot. Every GameData pointer read on the HUD path is now range-checked.
- Everything from 0.1.0: stamina (four styles, costs, ring), difficulty multipliers, no heart drops, sprint speed,
  rupee/clock/collectible HUD, B/L/R/ZR item buttons, songbook autoplay, Great Fairy rewards, Farore's Wind
  outdoors, 11 profiles and the two beta enemy mods.

## Install

1. Requires the game on update **v131072**.
   - **Emulator**: it must load mods from `user/load/0400486024DEC000`.
   - **Longshot**: use the app's **Longshot** target and the builder's `tools` folder.
2. Close the game and back up your saves.
3. Run `SuperHeroBoostConfig.exe`, pick a profile or tune the sections, select your emulator/game folder and press
   **Install** (or **Rebuild game** for Longshot).
4. The emulator presets can also be installed by hand: copy the `00-Super-Hero-Boost` folder of the chosen profile
   from the presets zip into `user/load/0400486024DEC000`.

## Notes

- Translations: Spanish, English, Portuguese, French, German and Italian.
- Source, issues and documentation: https://github.com/kuribox/OOT-SuperHeroBoostMod
