# GameBanana Tools submission

Use this for the **Tools** section of the game (https://gamebanana.com/tools/games/7534), separately from the mod.
GameBanana classifies third-party programs as Tools; the Mods file must stay free of executables.

**Title:** Super Hero Boost Config

**Tagline:** Configure and install Super Hero Boost: profiles, stamina, difficulty, HUD, item buttons and optional
world changes from one window.

## Summary

SuperHeroBoostConfig is the companion app for **Super Hero Boost**, a gameplay and HUD module for the *Ocarina of
Time* remake (update **v131072**). It edits the module's configuration, chooses the button textures and copies the
files into the emulator's mod folder. It also builds the module into **Longshot** (static recompilation), and it can
apply a new configuration without rebuilding.

The app is open source (MIT). It is built with Python and PyInstaller; the executable is unsigned, so some antivirus
programs may show a generic false positive. The source, the build script and the release checksums are public.

## Features

- Profiles: Recommended, Base, Hero Mode, Hero + Stamina, Hero Explorer, Super Hero, Ultra Hero, Survival, World
  changes, two beta combinations and a fully custom setup.
- Stamina style and per-action costs, enemy HP/damage multipliers, sprint speed, no-heart-drop.
- HUD: rupees, clock (12/24 h) and per-area collectible counter.
- Button mapping: B / L / R / ZR, Switch / PlayStation / Xbox styles, extended or simple layout, L in item or
  selector mode, songbook autoplay.
- Optional world changes (Great Fairy rewards, Farore outdoors) and beta enemy options, generated from your own game
  files.
- Install and uninstall into the emulator's `user/load/0400486024DEC000` folder.
- Checks GitHub Releases on startup, shows a download bar when a newer version exists and, on Windows, replaces
  itself and restarts (the SHA-256 of the downloaded asset is verified when GitHub provides it).
- Longshot target: patches `main`, copies the module to `.longshot_exefs`, installs the romfs options and runs the
  builder's update with progress, log and cancel. **Hookshot** uses the same builder and procedure but is not tested
  yet.
- Command-line mode with the same options.
- Spanish, English, Portuguese, French, German and Italian.

## How to use

1. Requirements: the game on update **v131072**; an emulator that loads mods from `user/load`, or a Longshot /
   Hookshot installation with its builder's `tools` folder.
2. Close the game and back up your saves.
3. Run `SuperHeroBoostConfig.exe`.
4. Pick a profile or tune each section, choose the emulator/game folder and press **Install** (or **Rebuild game**
   for Longshot).
5. Start the game. To remove the mod, press **Uninstall** or delete `00-Super-Hero-Boost`.

## Files

- `SuperHeroBoostConfig.exe`
  SHA-256: `17cbcf09debeaf8660274fe2e5690ed44ad2687b1f34bbc58999886bff1091ca`

The module payload is inside the executable; the app does not download anything.

## Links

- Source, issues and releases: https://github.com/kuribox/OOT-SuperHeroBoostMod
- Mod submission: **Super Hero Boost** (link the mod page here once it is listed).

## Credits

Add these to the **Credits** module:

- **Kuribox** — creator: app, module, HUD, stamina system and item buttons — https://github.com/kuribox
- **Anthropic (Claude)** — AI software used as an assistant for coding, reverse engineering and testing —
  https://www.anthropic.com
- **DeepSeek** — AI software used as an assistant for coding, reverse engineering and testing —
  https://www.deepseek.com
- **Kabosune / oot-remake-modding** — modding documentation and help —
  https://github.com/Kabosune/oot-remake-modding
- **platinumagpie / oot-remake-devtool** — development tools used during research and testing —
  https://github.com/platinumagpie/oot-remake-devtool

## Moderation note

If a moderator asks about the executable: it is an open-source configuration tool, not the game mod, and it is
submitted in the Tools section on purpose. The Mods submission is a separate file with no executables. Include the
source link and the SHA-256 above, and offer a VirusTotal scan of the exact release binary.
