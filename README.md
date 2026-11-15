# Super Hero Boost

Gameplay module for the console remake (update **v131072**) and its cross-platform configuration app
**SuperHeroBoostConfig**.

Current release: **0.2.1**, with support for the **Longshot** static recompilation and an automatic update check.

The mod adds stamina, difficulty scaling, an expanded HUD, extra item buttons and beta boots/mask quick select, all
configurable without recompiling anything. The app patches the prebuilt module and copies the files the game needs.
The module, the HUD, the textures and the app are original work: no third-party mod is bundled or downloaded.

## Features

### Gameplay

- **Complete profiles**: Recommended (everything on), Base, Hero Mode, Hero + Stamina, Hero Explorer, Super Hero,
  Ultra Hero, Survival, World changes and the two beta combinations (duplicated + fast enemies, everything). They set
  difficulty, stamina, the HUD, the world changes and the beta mods in one step; changing any option afterwards
  switches the profile to **Custom**.
- **Stamina** with four styles: hardcore (everything costs), combat only, sprint only and advanced (choose which
  actions cost). Includes exhaustion and regeneration, and costs for rolling, jumping, attacking, shooting,
  sprinting and blocking with the shield.
- **Stamina ring** next to the player, drawn with the game's own textures.
- **Sprint speed** configurable (default +25%).
- **Enemy health** and **damage taken** multipliers (×1 to ×3).
- **No heart drops**: hearts dropped by enemies become green rupees instead.
- **Always-visible clock and rupee counter**, with the game's native look and 12/24-hour format.
- **Songbook autoplay**: selecting a learned song in the native songbook (ZL) makes the hero play it and trigger
  its effect. Learned songs only; not the Scarecrow's Song.
- **Area collectibles counter**: a native-style plate below the clock with the Gold Skulltulas and heart pieces of
  the current area (for example `SKULL 3/8  COR 0/2`). The Skulltulas are read from the save's persistent key set, so
  the count no longer resets when you leave and re-enter an area; heart pieces without a map anchor (some
  chests/minigames) are not counted yet.
- **World changes**: reorders the three Great Fairy magic rewards (Hyrule Castle child gives **Nayru's Love**, Death
  Mountain Crater the **magic spin attack** and Desert Colossus **double magic**) and allows placing **Farore's Wind**
  warp points outside dungeons. Each fountain keeps her own model and dialogue; the Din fairy's overview still
  describes the original order. Known bug: press up and down a couple of times before the teleport menu responds.
- **Own button mapping** (`buttonMapping`):
  - **B, L, R and ZR** item buttons on the HUD, assignable from the **Items** tab of the pause menu.
  - **Switch / PlayStation / Xbox** button styles.
  - **Extended** layout (B, L, R, ZR, X, Y, A and the sword) or **simple** layout (only the assignable buttons, with
    B centred and L / R / ZR repositioned so there are no gaps).
  - **L button modes**: item or the game's item selector.

### Quick select (beta)

- **D-pad Down**: switch between the **Iron Boots** and **Hover Boots** without opening the pause menu. From the
  default boots it picks the first of the two you own.
- **D-pad Up**: switch between the **Lens of Truth** and the **mask** you were wearing.
- Only items in your inventory are used. The change is applied immediately through the game's own equip request,
  not just written to the save.
- A short tap keeps the game's normal D-pad behaviour.
- Off by default: enable each selector in the app's **Quick select (beta)** section. Experimental; back up your
  save before using it.

### Configuration app

- GUI for Windows, macOS and Linux (Python 3.10+ with Tkinter).
- Profiles, per-section settings, install and uninstall into the emulator's mod folder.
- **Quick select (beta)**: boots and mask switching from the D-pad.
- Checks GitHub Releases on startup and offers to download a newer version; on Windows it replaces itself and
  restarts.
- Translations in Spanish, English, Portuguese, French, German and Italian.
- Command-line mode to install the same configuration without opening the window.

### Beta

These options are **experimental**: they install extra romfs files. They can break puzzles, quests or performance.
Back up your save and test one at a time. The two beta profiles (*Beta: duplicated + fast enemies* and *Beta:
everything*) turn them on together with the rest of the configuration.

- **Enemy duplication (Option A)**: clones generic enemy placements in the map data and doubles field auto-spawn
  counts. Bosses, minibosses and scripted enemies are excluded.
- **Enemy speed ×2**: speeds up movement, animation and attack cadence. Some enemies or attacks may not change or
  may desync.

## Usage

1. **Requirements**: the game on update **v131072** and an emulator that loads mods from its
   `user/load/0400486024DEC000` folder (or the path you have configured). Back up your save before installing.
2. Open **SuperHeroBoostConfig** (or run `python app/main.py` from source).
3. Pick a profile or adjust the sections one by one.
4. Select the emulator folder. The app finds the mods folder, including a custom `load_directory` from
   `qt-config.ini`.
5. Press **Install**. The app creates the `00-Super-Hero-Boost` folder with the module, the button textures and the
   optional romfs files, and patches the selected configuration.
6. Close the game before installing or uninstalling.

To remove the mod, press **Uninstall** in the app or delete the `00-Super-Hero-Boost` folder.

Prebuilt binaries are published on the [Releases](https://github.com/kuribox/OOT-SuperHeroBoostMod/releases) page;
you can also build the app from source with the steps below.

### Longshot and Hookshot

Hookshot and Longshot are static recompilations, not emulators: they translate the game to native code and ignore
`exefs` mods by design. The romfs files work from `<game>/mods/Super-Hero-Boost/romfs`, but the module (HUD,
stamina, item buttons, collectible counter) has to be built into the game.

- **Longshot: supported and tested.** The app's **Longshot** target patches the game's `main`, copies the module to
  `.longshot_exefs`, installs the chosen romfs options and runs the builder's update with a progress bar. Verified
  with builder `v3.0.0-rc.3`: the game boots, starts a save, and the HUD, stamina, item buttons and collectible
  counter work. The first build takes 25-45 minutes; later code changes are incremental (~5 minutes) and
  profile/romfs-only changes need no rebuild. It is reversible with **Uninstall**.
- **Hookshot: expected to work, not tested yet.** It ships the same builder and the same
  `nx2/make_game.py --update`; point the app's target (or `tools/install_longshot.py --builder`) at its
  `HookshotBuilder/tools` folder. The procedure is otherwise identical, but it has not been verified on a real
  Hookshot build.

See [docs/LONGSHOT.md](docs/LONGSHOT.md) for the details.

### Button mapping controls

- In the pause menu's **Items** tab, with an item highlighted: **X** assigns it to **B**, **L** to **L**, **R** to
  **R** and **A** to the game's **ZR** box.
- Pressing the same button again unassigns it; if the item was already in another slot, they are swapped.
- If L is in **selector** mode, L cannot be assigned and its button is hidden from the HUD and from the legend.
- In **selector** mode, L opens the game's item selector.

### Command line

```bash
python app/main.py --cli --emu "EMULATOR_PATH" --profile recommended
python app/main.py --cli --emu "EMULATOR_PATH" --profile hero-explorer --button-style switch --bm-simple
python app/main.py --cli --emu "EMULATOR_PATH" --profile recommended --bm-l selector
python app/main.py --cli --emu "EMULATOR_PATH" --profile recommended --quick-boots --quick-mask
```

`--profile` applies a complete profile; individual flags override it. `--list-profiles` shows the list. The
`--quick-boots` / `--quick-mask` flags turn on the beta D-pad selectors.

The Great Fairy mod rewrites event flows with the `evfl` library (`pip install evfl`); if it is not installed,
`make_release.py` warns and keeps the previously generated files.

## Building

The app does not compile the mod: it uses the payload already staged in `app/payload`. Regenerating it requires the
game dump, LLVM (`clang`, `lld`, `llvm-objcopy`, `llvm-size`, `llvm-nm`) and the development dependencies listed in
[docs/GUIA-DESARROLLO.md](docs/GUIA-DESARROLLO.md).

```bash
python tools/build_core.py --features stamina,songbook,button_mapping --slots --compat --base 0x4F80000
python tools/make_release.py     # module + button textures + optional romfs files
python tools/build_app.py        # release/SuperHeroBoostConfig[.exe|.app] + SuperHeroBoost-<version>-presets.zip
```

`build_app.py` uses PyInstaller and does not cross-compile: run it on each target OS. It also writes
`release/SuperHeroBoost-<version>-presets.zip`, one zip with every app profile as a ready-to-install mod folder (no
executables), for the GameBanana Mods upload. The executable is written to `release/`. See the development guide
for details.

## Documentation

- [docs/GUIA-DESARROLLO.md](docs/GUIA-DESARROLLO.md): architecture, hooks, HUD, configuration and compilation.
- [docs/APP.md](docs/APP.md): app, profiles and options.
- [docs/BUTTON-MAPPING.md](docs/BUTTON-MAPPING.md): button mapping design.
- [docs/RE-NOTES.md](docs/RE-NOTES.md): reverse-engineering notes.
- [docs/LONGSHOT.md](docs/LONGSHOT.md): installing the mod in Hookshot and Longshot (static recompilations).
- [docs/AUDIT.md](docs/AUDIT.md): code and third-party material audit.

## Credits

Module, HUD, stamina system, button mapping (with its textures) and app: original work by Kuribox.

Thanks to:

- [Kabosune / oot-remake-modding](https://github.com/Kabosune/oot-remake-modding) for the modding documentation
  and help.
- [platinumagpie / oot-remake-devtool](https://github.com/platinumagpie/oot-remake-devtool) for the development tools
  used during research and testing.

These projects are development references and tools; their code is not bundled with this mod.

## AI assistance

AI assistants were used for parts of the coding, reverse engineering and testing: **Anthropic Claude**
(https://www.anthropic.com) and **DeepSeek** (https://www.deepseek.com). I orchestrated the work, tested the results
and adjusted them until they worked.

## License

Licensed under the **MIT License**. See [LICENSE](LICENSE).

You can use, modify, redistribute and build on this project, including commercially, as long as you keep the
copyright and license notices.
