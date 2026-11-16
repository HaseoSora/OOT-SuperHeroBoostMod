# Super Hero Boost 0.4.0

Feature release: three HUD layouts, exact bottle icons on the B/L/R/ZR buttons, expanded enemy speed and
duplication, the compact stamina bar and the Longshot Vulkan fallback. The apps for Windows, Linux and macOS
and the presets pack are built by the GitHub Actions workflow.

## Download

| Your system | File |
|---|---|
| Windows | `SuperHeroBoostConfig.exe` — the configuration app (the module payload is bundled inside). |
| Linux (x86_64) | `SuperHeroBoostConfig-linux` — `chmod +x SuperHeroBoostConfig-linux` after downloading. |
| macOS (Apple Silicon) | `SuperHeroBoostConfig-macos.dmg` — open it and drag the app to Applications. It is not signed, so the first time use right-click > Open (or `xattr -dr com.apple.quarantine /Applications/SuperHeroBoostConfig.app`). |
| Emulator / manual | `SuperHeroBoost-0.4.0-presets.zip` (+ `.sha256`) — all 11 app profiles as ready-to-install mod folders, no executables. |

The Windows build is the only one with an `.exe` extension: the Linux build is a plain ELF executable (that
is why it has no extension, it is named `-linux` to tell it apart) and macOS ships as a `.dmg` with the
`.app` bundle inside, the usual way to install an app on a Mac.

## What's new

**HUD layouts**
- **Wide**: the four native-style plates at the bottom (rupees, clock, Skulltulas, heart pieces).
- **Simple**: just the four counters at the bottom, without a background; the clock keeps its sun/moon icon.
- **Minimal**: rupees and time above the minimap, no plates; the area heart-piece counter appears next to the
  native Skulltula counter on the **Minus** map, with the native heart icon. The Skulltula HUD plate is left to
  the game's own map counter.

**Bottle icons**
- The B/L/R/ZR buttons now show the assigned bottle and its exact content: red, green and blue potions, blue fire,
  fish, bug, fairy, milk, half milk, letter, Poe, Big Poe and empty bottles.
- The five bottle cells are item indices 14–17 and 50; the HUD reads each bottle's GameData content record.
- ZR reads the game's own item-box value (`BottleA..E`) instead of its stale icon name.

**Enemy speed and duplication**
- Movement, animation playback and attack cadence are independent levels, with eleven multipliers from ×0.5 to
  ×6 (plus off).
- The duplicated-enemy placement option now clones every eligible placement and shares the original resource
  hashes, so the extra enemies appear and behave.

**Stamina bar**
- Optional compact segmented horizontal bar instead of the ring around Link; it follows the same stamina value
  and colours.

**Longshot**
- If the builder cannot find its Vulkan/VMA headers, the installer points `RX_CPM` at the packaged cache and,
  if the headers are still missing, reuses the game's installed `longshot_vk.dll`/`.so` through
  `LONGSHOT_VK_PREBUILT`.

**CI**
- GitHub Actions builds the Windows, Linux and macOS apps and the presets zip. The release job publishes the
  assets for tags `v*`.

## Everything from 0.3.0

- Boots/mask quick select, included in every profile and in the preset pack.
- Longshot HUD crash fix after an equipment change.
- Automatic update check against GitHub Releases (download, SHA-256 check, Windows self-replace).
- Full gameplay/HUD feature set and the 11 profiles.

## Install

1. Requires the game on update **v131072**.
   - **Emulator**: it must load mods from `user/load/0400486024DEC000`.
   - **Longshot**: use the app's **Longshot** target and the builder's `tools` folder.
2. Close the game and back up your saves.
3. Run `SuperHeroBoostConfig.exe`, pick a profile or tune the sections, select your emulator/game folder and
   press **Install** (or **Rebuild game** for Longshot).
4. The emulator presets can also be installed by hand: copy the `00-Super-Hero-Boost` folder of the chosen
   profile from the presets zip into `user/load/0400486024DEC000`.

## Notes

- Translations: Spanish, English, Portuguese, French, German and Italian.
- The configuration app is original work; the module, HUD, textures and installer are original too.
- Source, issues and documentation: https://github.com/kuribox/OOT-SuperHeroBoostMod
