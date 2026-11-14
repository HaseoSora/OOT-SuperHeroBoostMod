# Super Hero Boost

Gameplay module for the console remake (update **v131072**) and its cross-platform configuration app
**SuperHeroBoostConfig**.

The mod adds stamina, difficulty scaling, an expanded HUD and extra item buttons, all configurable without
recompiling anything. The app patches the prebuilt module and copies the files the game needs. The module, the HUD,
the textures and the app are original work: no third-party mod is bundled or downloaded.

## Features

### Gameplay

- **Complete profiles**: Recommended (everything on), Base, Hero Mode, Hero + Stamina, Hero Explorer, Super Hero,
  Ultra Hero and Survival. They set difficulty, stamina and sprint in one step; changing any option afterwards
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
- **Own button mapping** (`buttonMapping`):
  - **B, L, R and ZR** item buttons on the HUD, assignable from the **Items** tab of the pause menu.
  - **Switch / PlayStation / Xbox** button styles.
  - **Extended** layout (B, L, R, ZR, X, Y, A and the sword) or **simple** layout (only the assignable buttons, with
    B centred and L / R / ZR repositioned so there are no gaps).
  - **L button modes**: item, shield or the game's item selector.

### Configuration app

- GUI for Windows, macOS and Linux (Python 3.10+ with Tkinter).
- Profiles, per-section settings, install and uninstall into the emulator's mod folder.
- Translations in Spanish, English, Portuguese, French, German and Italian.
- Command-line mode to install the same configuration without opening the window.

### Beta

These options are **experimental**. They are generated from the game dump and installed as extra romfs files; they
can break puzzles, quests or performance. Back up your save and test one at a time.

- **Enemy duplication (Option A)**: clones generic enemy placements in the map data and doubles field auto-spawn
  counts. Bosses, minibosses and scripted enemies are excluded.
- **Enemy speed ×2**: speeds up movement, animation and attack cadence. Some enemies or attacks may not change or
  may desync.

Other work in progress stays outside this branch and is not part of this release.

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

Prebuilt binaries are not published in this repository yet; build the app from source with the steps below.

### Button mapping controls

- In the pause menu's **Items** tab, with an item highlighted: **X** assigns it to **B**, **L** to **L**, **R** to
  **R** and **A** to the game's **ZR** box.
- Pressing the same button again unassigns it; if the item was already in another slot, they are swapped.
- If L is in **shield** or **selector** mode, L cannot be assigned and its button is hidden from the HUD and from the
  legend.
- In **selector** mode, L opens the game's item selector.

### Command line

```bash
python app/main.py --cli --emu "EMULATOR_PATH" --profile recommended
python app/main.py --cli --emu "EMULATOR_PATH" --profile hero-explorer --button-style switch --bm-simple
python app/main.py --cli --emu "EMULATOR_PATH" --profile recommended --bm-l selector
```

`--profile` applies a complete profile; individual flags override it. `--list-profiles` shows the list.

## Building

The app does not compile the mod: it uses the payload already staged in `app/payload`. Regenerating it requires the
game dump, LLVM (`clang`, `lld`, `llvm-objcopy`, `llvm-size`, `llvm-nm`) and the development dependencies listed in
[docs/GUIA-DESARROLLO.md](docs/GUIA-DESARROLLO.md).

```bash
python tools/build_core.py --features stamina,songbook,button_mapping --slots --compat --base 0x4F80000
python tools/make_release.py     # module + button textures + optional romfs files
python tools/build_app.py        # release/SuperHeroBoostConfig[.exe|.app]
```

`build_app.py` uses PyInstaller and does not cross-compile: run it on each target OS. The executable is written to
`release/`. See the development guide for details.

## Documentation

- [docs/GUIA-DESARROLLO.md](docs/GUIA-DESARROLLO.md): architecture, hooks, HUD, configuration and compilation.
- [docs/APP.md](docs/APP.md): app, profiles and options.
- [docs/BUTTON-MAPPING.md](docs/BUTTON-MAPPING.md): button mapping design.
- [docs/RE-NOTES.md](docs/RE-NOTES.md): reverse-engineering notes.
- [docs/AUDIT.md](docs/AUDIT.md): code and third-party material audit.

## Notice

No game code, text, textures or any other game material is redistributed. The mod reads the user's own dump at
runtime and only bundles its own module and its own art. You need your own legal copy of the game to use it.

## Credits

Module, HUD, stamina system, button mapping (with its textures) and app: original work by Kuribox.

Thanks to:

- [Kabosune / oot-remake-modding](https://github.com/Kabosune/oot-remake-modding) for the modding documentation
  and help.
- [platinumagpie / oot-remake-devtool](https://github.com/platinumagpie/oot-remake-devtool) for the development tools
  used during research and testing.

These projects are development references and tools; their code is not bundled with this mod.

## AI assistance

Parts of the development — code, documentation, reverse-engineering notes and tests — were carried out with help from
AI assistants: **Anthropic Claude** and **DeepSeek**. Every change was reviewed, built and tested by the author, who is
responsible for the final result. Game assets are not generated by AI: the button textures are drawn in code by
`tools/make_buttons.py`.

## License

Licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE).

You can use, modify, redistribute and build on this project, including commercially, as long as you keep the
copyright and license notices and state the changes you made. The license also includes an express grant of patent
rights and does not grant any trademark rights.
