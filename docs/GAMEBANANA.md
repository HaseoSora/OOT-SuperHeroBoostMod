# GameBanana listing

**Title:** Super Hero Boost

**Tagline:** More than a HUD — stamina, Hero Mode difficulty, extra item buttons and world changes, all configurable from a desktop app.

**Alternative taglines**

- Stamina, Hero Mode scaling, an always-visible HUD and your own item buttons.
- A complete gameplay and HUD overhaul you can configure without touching a single file.

## Summary

Super Hero Boost is a gameplay and HUD module for the *Ocarina of Time* remake (update **v131072**). Stamina,
difficulty, the HUD and the extra buttons are switches in a companion app, and the installer patches the module with
the profile you pick: no recompiling, no manual file editing. The optional world changes and beta mods are generated
from your own game files.

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

## Download

- **`SuperHeroBoost-0.2.0-mod.zip`** — the mod itself, **no executable inside**.
  SHA-256: `c2817d883417264e85507f5ad666190aa53e36b7b78541e609791de45f6c3954`
- The companion app **SuperHeroBoostConfig** is not uploaded here. It is on the project's
  [Releases page](https://github.com/kuribox/OOT-SuperHeroBoostMod/releases) (Windows `.exe`; the source runs on
  Windows, macOS and Linux with Python 3.10+).

The zip contains the prebuilt module (recommended code profile: hardcore stamina, enemy HP 150%, damage 200%, HUD
with rupees / clock / collectibles, songbook and Switch-style item buttons) and its button textures. The optional
world changes, no-heart-drop and beta enemy mods need the companion app because they are generated from your own
game files.

## How to use

1. **Requirements**: the game on update **v131072** and an emulator that loads mods from `user/load`. Close the game
   before installing and back up your saves.
2. Download **`SuperHeroBoost-0.2.0-mod.zip`** and extract it.
3. Copy the **`00-Super-Hero-Boost`** folder into `user/load/0400486024DEC000` (the folder that contains your
   mods; merge it if it already exists).
4. Start the game.
5. In game:
   - **Item buttons**: open the pause menu, go to the **Items** tab, highlight an item and press **X** to put it
     on **B**, **L** on **L** and **R** on **R**. The game's own **ZR** box still works with **A**.
   - **Songbook**: pick a learned song in the native songbook (**ZL**) and Link plays it with its effect.
   - **HUD**: rupees and clock stay visible; under them you get the Gold Skulltula and heart-piece counter of the
     current area.
   - **Stamina**: the ring next to Link shows what is left; it refills when you stop.
6. To change options, use the app: pick a profile or tune each section and press **Install** over the same folder.
   To remove the mod, delete `00-Super-Hero-Boost`.

The app saves your settings automatically, but changes only reach the game after pressing **Install**.

## Requirements

- The game, update **v131072**.
- An emulator that loads mods from `user/load/0400486024DEC000` (or a custom load folder, which the app also
  detects).
- Close the game before installing or uninstalling. Back up your save.

## Compatibility

- **Emulators: tested** on **lichii** and **Fritchii**.
- **Longshot: supported and tested** since 0.2.0. Longshot is a static recompilation, so the module has to be built
  into the game: the app's **Longshot** target rebuilds it and installs the profile and romfs options (25-45 minutes
  the first time; later code changes are incremental and profile/romfs changes need no rebuild).
- **Hookshot: expected to work, not tested yet.** It uses the same builder and `nx2/make_game.py --update`; the app
  accepts its `HookshotBuilder/tools` folder.
- Real hardware: not tested.

## Credits

Add these to GameBanana's **Credits** module (the AI software providers are required by the AI content policy):

- **Kuribox** — creator: module, HUD, stamina system, item buttons and companion app —
  https://github.com/kuribox
- **Anthropic (Claude)** — AI software used as an assistant for coding, reverse engineering and testing —
  https://www.anthropic.com
- **DeepSeek** — AI software used as an assistant for coding, reverse engineering and testing —
  https://www.deepseek.com
- **Kabosune / oot-remake-modding** — modding documentation and help —
  https://github.com/Kabosune/oot-remake-modding
- **platinumagpie / oot-remake-devtool** — development tools used during research and testing —
  https://github.com/platinumagpie/oot-remake-devtool

The AI software was used as an assistant; the design, direction, integration and testing are the author's.

## Links

- Source and issues: https://github.com/kuribox/OOT-SuperHeroBoostMod
- App downloads: https://github.com/kuribox/OOT-SuperHeroBoostMod/releases
- Cover art: `docs/portada.png` (1920x1080) and `docs/portada-mini.jpg` (640x480, for the listing thumbnail).
