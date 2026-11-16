# Companion app (SuperHeroBoostConfig)

The app does **not** compile anything. The mod ships precompiled as the standalone variant (`app/payload/standalone`)
and reads a small config block (`core/config.h`, magic `SHBCFG01`) when the game loads.
The app only:

1. finds the emulator's mod folder (`user/load/0400486024DEC000`, also accepting the load folder, the title folder or
   a custom `load_directory` from `qt-config.ini`),
2. patches the config bytes inside the prebuilt `subsdk9`: stamina on/off, stamina style, per-action costs,
   combat only, enemy health, damage taken, rupee counter / clock / 24 h, sprint speed, button mapping style,
   layout and L mode
   (field table in [GUIA-DESARROLLO.md](GUIA-DESARROLLO.md#33-runtime-configuration-coreconfigh)),
3. copies the button textures for the chosen style (Switch / PlayStation / Xbox) into the mod's romfs,
4. with "no heart drops", copies the generated romfs option (if that optional file was not built from the user's game
   dump, the app installs everything else and shows a note instead of failing),
5. writes everything as the mod folder `00-Super-Hero-Boost` and warns about other exefs mods that may conflict.

## Files

| File | Purpose |
|---|---|
| `app/main.py` | window, navigation and `--cli` mode |
| `app/presets.py` | complete game profiles |
| `app/installer.py` | install logic and config patching |
| `app/updater.py` | GitHub Releases update check, download and self-replace |
| `app/version.py` | project version (shown in the window and used by the release tools) |
| `app/paths.py` | portable/per-user settings paths (Windows, macOS, Linux) |
| `app/i18n.py` | texts in en / es / pt / fr / de / it |

Settings are remembered in `SuperHeroBoostConfig.json` next to the program; if that folder is read-only, in the
per-user configuration folder (see the README). The app never needs administrator rights.

## Game profiles

A profile sets **every** gameplay option. Every fixed profile includes the HUD, the button mapping and the Songbook.
Changing any option afterwards switches the profile to **Custom** and keeps your value. The button style (Switch /
PlayStation / Xbox), layout, L mode, the language and the emulator folder are not part of a profile. **Recommended**
is the default and enables everything.

Sprint is always **×1.25** in the profiles. It is only a starting point and can be changed by hand in the Stamina
section; the profiles never use ×1.75, ×2 or ×3.

| Profile | Stamina | Stamina style | Enemy HP | Damage | No hearts | Sprint | HUD | Buttons |
|---|---|---|---|---|---|---|---|---|
| **Recommended** | on | Hardcore | ×1.5 | ×2 | on | ×1.25 | on | on |
| Base | off | — | ×1 | ×1 | off | ×1.25 | on | on |
| Hero Mode | off | — | ×1.5 | ×2 | on | ×1.25 | on | on |
| Hero + Stamina | on | Hardcore | ×1.5 | ×2 | on | ×1.25 | on | on |
| Hero Explorer | on | Sprint only | ×1.5 | ×2 | on | ×1.25 | on | on |
| Super Hero | on | Hardcore | ×2 | ×3 | on | ×1.25 | on | on |
| Ultra Hero | on | Hardcore | ×3 | ×3 | on | ×1.25 | on | on |
| Survival | on | Hardcore | ×2 | ×2 | on | ×1.25 | on | on |
| Custom | your values | your values | your values | your values | your values | your values | your values | your values |

"Sprint only" means only sprinting drains stamina. "Hardcore" means every enabled action drains it. "No hearts" means
dropped hearts become green rupees (the optional romfs file; see the note below). Named profiles keep the stamina
display on the ring, and the enemy speed components off.

## Window

- **Home**: profile list (the only profile selector), explanation of the active profile, emulator folder and install
  status.
- **Stamina**: on/off, stamina style, what costs stamina (the checkboxes update automatically for each style), sprint
  speed and the stamina display (ring around the hero, or a segmented bar under the magic gauge; yellow, red while
  recharging).
- **Difficulty**: enemy health, damage taken, heart drops.
- **Enemies**: two beta tools, generated from the user's dump at build time and installed as extra romfs files:
  - **Duplicate enemies (Option A)**: clones generic enemy placements in `Banc` and doubles field auto-spawn counts.
    Bosses, minibosses and scripted enemies are excluded.
  - **Enemy speed**: movement, animation playback and attack cadence, each with eleven multipliers from ×0.5 to ×6
    (plus off). Some enemies or attacks may not change, or may desync.
  They can break puzzles, quests or performance. Back up the save and test one at a time.
- **HUD & buttons**: rupee counter, clock (**off / 12 h / 24 h**, one selector), button mapping (on/off), button
  style (Switch / PlayStation / Xbox), layout (extended / simple), L mode (item / selector) and **Quick select**.
- **Area collectibles counter**: adds a third native-style plate below the rupee/clock row with the
  Gold Skulltulas and heart pieces of the current Banc, for example `SKULL 3/8  COR 1/2`. It reads the live
  `HeartPieceAnchor_GameDataPath` flags, `Sequence_CurrentBanc` and, for the Skulltulas, the save's persistent
  64-bit key set (`Game` / `Bool64bitKey`), so the count no longer resets when you leave and re-enter an area.
  The heart count only includes pieces that the game associates with a map anchor; some chest/minigame pieces
  without one are not counted yet.
- **Miscellaneous**: Songbook autoplay (select a learned song in the game's native songbook with ZL and it plays
  automatically, effect included; not the Scarecrow's Song).
- **World changes**, inside *Miscellaneous*:
  - **Great Fairy rewards**: the three magic rewards are reordered. Hyrule Castle (child) gives **Nayru's Love**,
    Death Mountain Crater gives the **magic spin attack**, and Desert Colossus gives **double magic**. Each fountain
    keeps its own Great Fairy and its own dialogue; the reward line is switched to the new power. The Din fairy's
    overview dialogue still describes the original order, so trust the fountain itself.
  - **Farore's Wind outdoors**: allows placing Farore's Wind warp points outside dungeons. The real forbidden areas
    inside dungeons (for example the FireTemple areas) stay blocked. It is a patched event flow, installed as a romfs
    file. **Known bug**: press up and down a couple of times before the teleport menu responds.
- **About**: credits, the material/third-party notice and **Check for updates**.

The bottom bar always shows the install state and the **Install / Uninstall** buttons. Changes are saved
automatically (250 ms debounce).

## Quick select

The **HUD & buttons** section has a **Quick select** card. It enables the module's D-pad switches:

- **Boots**: hold D-pad Down to alternate between the Iron Boots and Hover Boots (from the default boots it picks
  the first one you own).
- **Mask**: hold D-pad Up to alternate between the Lens of Truth and the mask you were wearing.
- Only items in your inventory are used. The module calls the game's own equip request, so the change is applied
  immediately; writing the String64 alone only affects the next load.
- A short tap keeps the game's normal D-pad behaviour.
- The named profiles turn both on; uncheck them here to use a profile without quick select. It writes the live
  equipment, so keep a save backup.

## Updates

On startup the app asks GitHub for the latest release of
[OOT-SuperHeroBoostMod](https://github.com/kuribox/OOT-SuperHeroBoostMod/releases/latest) in a background thread. If
the tag is newer than `app/version.py`, a bar appears under the header with **Download / Later**; it is also
available as **Check for updates** in *About*.

- The download is the release asset for the platform (`SuperHeroBoostConfig.exe` on Windows). It is written to a
  `.part` file, its SHA-256 is checked against the asset digest from the GitHub API (when present), and only then
  renamed.
- A frozen Windows build in a writable folder replaces itself: a small detached PowerShell script waits for the app
  to exit, copies the new executable over the old one and starts it again. If the folder is read-only (for example
  `Program Files`), or the app runs from source, the file is saved to
  `%LOCALAPPDATA%\SuperHeroBoostConfig\updates` and the app shows its path.
- A network error or a rate limit never blocks the window: the automatic check is silent, and only the manual
  **Check for updates** shows a message.

The updater is only active in the GUI (`--cli` does not check), and it needs no GitHub account or token.

## Command line

The same install code is available without a window:

```
python app/main.py --cli --emu "EMULATOR_PATH" --profile recommended
python app/main.py --cli --emu "EMULATOR_PATH" --preset 3 --off jump,shoot --combat-only
python app/main.py --cli --emu "EMULATOR_PATH" --profile hero-explorer --rupees --clock --clock24
python app/main.py --cli --emu "EMULATOR_PATH" --profile recommended --no-songbook
python app/main.py --cli --emu "EMULATOR_PATH" --profile base --enemy-move 1 --enemy-anim 2 --enemy-attack 2 --stamina-bar
python app/main.py --list-profiles
```

`--profile` applies a complete profile first; the individual flags override it. `--preset` keeps the numeric stamina
style used by older scripts (0 hardcore, 1 combat only, 2 sprint only, 3 advanced).

## Build

Run this on each target OS:

```
python tools/make_release.py     # module + button textures + optional romfs options
python tools/build_app.py        # release/SuperHeroBoostConfig[.exe|.app]
```

`build_app.py` uses the platform's separator for `--add-data` and writes the platform's native output. macOS needs
PyInstaller from the same Python installation used to build; Linux produces a plain executable.

The whole payload is bundled with the app: the module, the repository romfs and the button textures for the three
styles. The `romfs` options generated from the game are only installed when their option is enabled, and a missing one
stops nothing else.

## Linux

The app itself is plain Python + Tkinter and builds on Linux:

```
sudo apt install python3 python3-tk
python3 -m pip install --user pyinstaller
python3 tools/build_app.py          # release/SuperHeroBoostConfig
```

`make_release.py` (the mod payload) is a separate step: it needs the LLVM toolchain and the game dump, so the usual
flow is to build the payload once (on any machine that has them) and then build the app on each target OS. PyInstaller
does not cross-compile.

To build the payload on Linux too, install `clang`, `lld` and the LLVM binutils, then set `SHB_LLVM` (folder with
`clang`, `ld.lld`, `llvm-objcopy`, `llvm-size`, `llvm-nm`), `SHB_STOCK_MAIN` (the game's `main`), `SHB_ROMFS` (the
`romfs` dump) and `SHB_DEVTOOL` (the BYML reader used by `make_romfs_opts.py`).

## No-heart-drop file

The "no hearts" option changes a game data table (`DropGlobalParam`) through romfs; it is not code. The repository does
not redistribute that table. `tools/make_romfs_opts.py` generates it from the user's own game dump (this project uses
the dump folder, or `SHB_ROMFS`), and `make_release.py` keeps an existing `app/payload/romfs_opts` when
rebuilding. That file is only needed at build time: the release payload already includes the generated copy, so users
do not need a dump. If the file is missing, the app installs everything else and shows a note.

## Longshot and Hookshot

The app can install into a static recompilation too. Pick **Hookshot / Longshot** in the **Install** section of the
sidebar and choose the game folder (the one with `bin/longshot.exe` and `.longshot_exefs`).

- The first install (or **Rebuild game**) runs the builder's update with a progress bar: 25–45 minutes, the game must
  be closed. The builder is detected from the launcher; pick its folder (the one with `tools/nx2/make_game.py`) if it
  is not.
- Once the game is built, **Install** only applies the profile, the configuration block and the selected romfs files
  (seconds, no rebuild). Use **Rebuild game** after an app/mod update.
- If the builder cannot find the Vulkan/VMA headers, the app points `RX_CPM` at its packaged `tools/cpm`; if they are
  still missing, it reuses the game's existing `bin/longshot_vk.dll` / `.so` through `LONGSHOT_VK_PREBUILT`.
- The actions are in the bottom bar: **Install / Apply settings**, **Rebuild game** and **Uninstall**. The Install
  section shows the game folder, the detected builder (a **Builder…** button appears only if it is not found) and the
  progress/log of a rebuild.
- **Uninstall** restores the original executable, image and `main` from `<game>/.shb-backup` and removes the mod.
- The builder's `exefs` patches are not applied at run time (the game is compiled ahead of time), so the module must
  be built in; this is what the app does. See [LONGSHOT.md](LONGSHOT.md).

`tools/install_longshot.py` is the same procedure for scripts and CI.
