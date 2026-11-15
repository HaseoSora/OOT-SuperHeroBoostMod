# Super Hero Boost 0.3.0

Feature release: **boots/mask quick select**, included in every profile and in the preset pack, plus the HUD fix
for the Longshot crash after an equipment change.

## Download

- `SuperHeroBoostConfig.exe` — the configuration app for Windows (the module payload is bundled inside).
  SHA-256: `6d6d9fd74c04650830e24271c2ae81c42debb42a983d936f369e616be81b2c93`
- `SuperHeroBoost-0.3.0-presets.zip` — all 11 app profiles as ready-to-install mod folders for emulators, with no
  executables. Every profile includes quick select.
  SHA-256: `9cdfd1998da7101454aa53520672f91dc65ad5fd96e26a55050047bd5ed63d93`

## What's new

**Quick select (no longer beta)**
- **D-pad Down**: switches between the **Iron Boots** and **Hover Boots** without opening the pause menu. From the
  default boots it picks the first of the two you own.
- **D-pad Up**: switches between the **Lens of Truth** and the **mask** you were wearing.
- Only items in your inventory are used. The change is applied immediately through the game's own equip request,
  not just written to the String64 record.
- A short tap keeps the game's normal D-pad behaviour.
- The named profiles (including **Recommended**) and every preset in the zip turn it on; the app's **Quick select**
  card can disable each selector. It writes the live equipment, so keep a save backup.

**Longshot HUD crash fixed**
- After an equipment change, `hud_frame → zr_mirror` walked `[part+0x28] + 0x150 → +0x1F0 → +0x38` on a stale
  `PlayerStatus` part and read `0x326a`. Every step of that chain is now range-checked; `hud_ingame` and
  `g_frame_node` are validated too.

**Presets**
- `tools/build_app.py` still writes one zip with every profile; all profiles now carry `quick_boots` and
  `quick_mask` enabled, and the README inside the zip documents the D-pad controls.

## Everything from 0.2.1

- Automatic update check against GitHub Releases (download, SHA-256 check, Windows self-replace).
- Longshot support: the app patches `main`, copies the module to `.longshot_exefs`, installs the romfs options and
  runs the builder with progress. Hookshot uses the same procedure but is not tested yet.
- One presets zip with all 11 profiles.
- Everything from 0.2.0: Longshot save-start crash fix and the full gameplay/HUD feature set.

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
