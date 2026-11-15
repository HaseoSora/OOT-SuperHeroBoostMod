# GameBanana listing

**Title:** Super Hero Boost

**Tagline:** More than a HUD — stamina, Hero Mode difficulty, extra item buttons and world changes, all configurable from a desktop app.

**Alternative taglines**

- Stamina, Hero Mode scaling, an always-visible HUD and your own item buttons.
- A complete gameplay and HUD overhaul you can configure without touching a single file.

## Summary

Super Hero Boost is a gameplay and HUD module for the *Ocarina of Time* remake (update **v131072**) plus a
companion app, **SuperHeroBoostConfig**, that writes the configuration for you: no recompiling, no manual file
editing, and a one-click install into your emulator's mod folder. Stamina, difficulty, the HUD, the extra buttons
and the optional world changes are all switches in the app, and the installer patches the prebuilt module with the
profile you pick.

## Features

**Stamina**
- Four styles: hardcore (every action costs), combat only, sprint only, or advanced (choose which actions cost).
- Exhaustion and regeneration, with individual costs for rolling, jumping, attacking, shooting, sprinting and
  blocking with the shield.
- Stamina ring next to Link, drawn with the game's own textures.

**Difficulty**
- Enemy health and damage taken multipliers (x1 to x3).
- No heart drops: hearts become green rupees.

**Movement**
- Configurable sprint speed (+25% by default).

**HUD**
- Always-visible rupee counter and clock (off / 12 h / 24 h) with the game's native plate look.
- Per-area counter for Gold Skulltulas and heart pieces. It reads the save's persistent key set, so the count
  survives leaving and re-entering an area.

**Buttons**
- B, L, R and ZR item buttons on the HUD, assignable from the pause menu's Items tab by pressing X / L / R.
- Switch, PlayStation and Xbox button styles.
- Extended layout (B, L, R, ZR, X, Y, A and the sword) or simple layout (only the assignable buttons, with B
  centred).
- L as an item button or as the game's own item selector.
- Songbook autoplay: pick a learned song in the native songbook (ZL) and Link plays it with its effect.

**World changes**
- The three Great Fairy magic rewards are reordered: Hyrule Castle (child) gives **Nayru's Love**, Death Mountain
  Crater gives the **magic spin attack** and Desert Colossus gives **double magic**.
- **Farore's Wind** warp points can be placed outdoors.
- Known bug: press up and down a couple of times before the teleport menu responds.

**Profiles**
- Recommended, Base, Hero Mode, Hero + Stamina, Hero Explorer, Super Hero, Ultra Hero, Survival, World changes and
  two beta combinations, plus a fully custom setup.

**Beta (optional, generated from your own game files)**
- Enemy duplication (Option A).
- Enemy speed x2.

**Companion app**
- GUI for Windows, macOS and Linux (Python 3.10+ with Tkinter) and a command-line mode.
- Translations: Spanish, English, Portuguese, French, German and Italian.

## How to use

1. **Requirements**: the game on update **v131072** and an emulator that loads mods from its `user/load` folder.
   Close the game before installing and back up your saves.
2. Download **`SuperHeroBoostConfig.exe`** from the
   [Releases page](https://github.com/kuribox/OOT-SuperHeroBoostMod/releases) and run it (Windows). The module is
   bundled inside the app: you do not need Python.
3. On **Game profile** pick a preset (Recommended turns everything on) or tune each section by hand: Stamina,
   Difficulty, HUD, Modifications.
4. Choose your emulator folder: the one that contains `user` (the app also finds a custom `load_directory`).
5. Press **Install**. It creates `00-Super-Hero-Boost` inside `user/load/0400486024DEC000` and patches the
   configuration you selected.
6. Start the game.
7. In game:
   - **Item buttons**: open the pause menu, go to the **Items** tab, highlight an item and press **X** to put it
     on **B**, **L** on **L** and **R** on **R**. The game's own **ZR** box still works with **A**.
   - **Songbook**: pick a learned song in the native songbook (**ZL**) and Link plays it with its effect.
   - **HUD**: rupees and clock stay visible; under them you get the Gold Skulltula and heart-piece counter of the
     current area.
   - **Stamina**: the ring next to Link shows what is left; it refills when you stop.
8. To remove it, press **Uninstall** in the app (or delete the `00-Super-Hero-Boost` folder).

The app saves your settings automatically, but changes only reach the game after pressing **Install** again.

## Requirements

- The game, update **v131072**.
- An emulator that loads mods from `user/load/0400486024DEC000` (or a custom load folder, which the app also
  detects).
- Close the game before installing or uninstalling. Back up your save.

## Compatibility

- **Emulators only for now.** The mod has not been tested on real hardware, so please use an emulator that loads
  mods from its `user/load` folder.
- Tested and working on **lichii** and **Fritchii**.
- **Hookshot**: not working yet. I have not managed to get the mod running there so far, so it is not supported
  for now.

## Links

- Source and issues: https://github.com/kuribox/OOT-SuperHeroBoostMod
- Cover art: `docs/portada.png` (1920x1080) and `docs/portada-mini.jpg` (640x480, for the listing thumbnail).
