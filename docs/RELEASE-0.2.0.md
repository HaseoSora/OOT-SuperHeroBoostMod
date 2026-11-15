# Super Hero Boost 0.2.0

Second public release: the gameplay/HUD module for the *Ocarina of Time* remake (update **v131072**), the
**SuperHeroBoostConfig** app, and support for the **Longshot** static recompilation.

## Download

- `SuperHeroBoostConfig.exe` — the configuration app for Windows (the module payload is bundled inside).
  SHA-256: `17cbcf09debeaf8660274fe2e5690ed44ad2687b1f34bbc58999886bff1091ca`

## What's new

**Longshot support (tested)**
- The app has a **Longshot** target: it patches the game's `main`, copies the module into `.longshot_exefs`,
  installs the chosen romfs options and runs the builder's update with progress, log and cancel.
- Verified with builder `v3.0.0-rc.3`: the recompiled game boots, starts a save, and the HUD, stamina, item
  buttons and collectible counter work.
- Later code changes rebuild incrementally (~5 minutes instead of 25-45); profile, HUD and romfs changes use
  **Apply settings** and need no rebuild.
- **Uninstall** restores the original `bin/longshot.exe`, `image.bin` and `.longshot_exefs/main`.

**Hookshot (expected, not tested)**
- Hookshot ships the same builder and `nx2/make_game.py --update`; the target accepts its
  `HookshotBuilder/tools` folder and the procedure is identical. It has not been verified on a real Hookshot
  build yet.

**Fixes**
- The Longshot save-start crash is fixed: the HUD's collectibles reader dereferenced a stale pointer from the
  GameData manager's save-slot array. Every GameData pointer read on the HUD path is now range-checked.
- The HUD also validates layout names before the game's `find_part`/`ui_find_sub` calls, which keeps the module
  safe in both the emulator and the recompiled game.

## Everything from 0.1.0

**Stamina**
- Four styles: hardcore (every action costs), combat only, sprint only or advanced (choose which actions cost).
- Exhaustion and regeneration, with costs for rolling, jumping, attacking, shooting, sprinting and shield blocking.
- Stamina ring next to Link, drawn with the game's own textures.

**Difficulty**
- Enemy health and damage taken multipliers (x1 to x3).
- No heart drops: hearts become green rupees.

**HUD**
- Always-visible rupee counter and clock (off / 12 h / 24 h) with the game's native plates.
- Per-area Gold Skulltula and heart-piece counter that reads the save's persistent key set, so it survives leaving
  and re-entering an area.

**Buttons**
- B, L, R and ZR item buttons on the HUD, assignable from the pause menu's Items tab (X / L / R).
- Switch, PlayStation and Xbox button styles; extended or simple layout; L as an item button or the game's selector.
- Songbook autoplay from the native songbook.

**World changes**
- Great Fairy magic rewards reordered: Hyrule Castle (child) gives **Nayru's Love**, Death Mountain Crater the
  **magic spin attack** and Desert Colossus **double magic**.
- **Farore's Wind** warp points can be placed outdoors.
  *Known issue: press up and down a couple of times before the teleport menu responds.*

**Profiles**: Recommended, Base, Hero Mode, Hero + Stamina, Hero Explorer, Super Hero, Ultra Hero, Survival,
World changes and two beta combinations (enemy duplication, x2 enemy speed), plus a fully custom setup.

## Install

1. Requires the game on update **v131072**.
   - **Emulator**: it must load mods from `user/load/0400486024DEC000`.
   - **Longshot / Hookshot**: the app needs the builder's `tools` folder and rebuilds the game.
2. Close the game.
3. Run `SuperHeroBoostConfig.exe`, pick a profile or tune the sections, select your emulator or game folder and
   press **Install** (or **Rebuild game** for a recompilation).
4. Back up your saves before playing.

## Notes

- The app does not compile anything for the emulator: it patches the prebuilt module and copies the files the game
  needs. For Longshot/Hookshot it runs the builder that ships with the recompilation.
- The beta options are generated from your own game files at build time; if a file is missing, the app says so and
  installs the rest.
- Translations: Spanish, English, Portuguese, French, German and Italian.
- Source, issues and documentation: https://github.com/kuribox/OOT-SuperHeroBoostMod
