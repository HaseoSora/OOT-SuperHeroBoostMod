# Super Hero Boost 0.1.0

First public release: the gameplay/HUD module for the *Ocarina of Time* remake (update **v131072**) and the
**SuperHeroBoostConfig** companion app that configures and installs it.

## Download

- `SuperHeroBoostConfig.exe` — the configuration app for Windows (the module payload is bundled inside).
  SHA-256: `625748e8f54e3877c8d996d6e5d5343b1289af916ab18ff3b7143b8841620fc0`

## What it does

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

1. Requires the game on update **v131072** and an emulator that loads mods from `user/load/0400486024DEC000`.
2. Close the game.
3. Run `SuperHeroBoostConfig.exe`, pick a profile or tune the sections, select your emulator folder and press
   **Install**.
4. Back up your saves before playing.

## Notes

- The app does not compile anything: it patches the prebuilt module and copies the files the game needs.
- The beta options are generated from your own game files at build time; if a file is missing, the app says so and
  installs the rest.
- Translations: Spanish, English, Portuguese, French, German and Italian.
- Source, issues and documentation: https://github.com/kuribox/OOT-SuperHeroBoostMod
