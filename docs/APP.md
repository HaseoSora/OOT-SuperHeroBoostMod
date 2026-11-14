# Companion app (SuperHeroBoostConfig)

The app does **not** compile anything. The mod ships precompiled in two variants (`app/payload/classic`,
`app/payload/standalone`) and reads a small config block (`core/config.h`, magic `SHBCFG01`) when the game loads.
The app only:

1. finds the emulator's mod folder (`user/load/0400486024DEC000`, also accepting the load folder, the title folder or
   a custom `load_directory` from `qt-config.ini`),
2. patches the config bytes inside the prebuilt `subsdk9`: stamina on/off, stamina style, per-action costs,
   combat only, enemy health, damage taken, rupee counter / clock / 24 h, sprint speed
   (field table in [GUIA-DESARROLLO.md](GUIA-DESARROLLO.md#33-configuración-en-tiempo-de-ejecución-coreconfigh)),
3. with Classic Item Slots enabled, downloads the chosen variant (Switch / PlayStation / Xbox) from its official GitHub
   release (v1.4.3), caches it per user, copies its module as `subsdk8` and its romfs, and merges the two IPS patch
   files (they are checked for overlaps). Classic is **not** bundled with the app,
4. with "no heart drops", copies the generated romfs option (if that optional file was not built from the user's game
   dump, the app installs everything else and shows a note instead of failing),
5. writes everything as the mod folder `00-Super-Hero-Boost` and warns about other exefs mods that may conflict.

## Files

| File | Purpose |
|---|---|
| `app/main.py` | window, navigation and `--cli` mode |
| `app/presets.py` | complete game profiles |
| `app/installer.py` | install logic and config patching |
| `app/paths.py` | portable/per-user settings paths (Windows, macOS, Linux) |
| `app/i18n.py` | texts in en / es / pt / fr / de / it |

Settings are remembered in `SuperHeroBoostConfig.json` next to the program; if that folder is read-only, in the
per-user configuration folder (see the README). The app never needs administrator rights.

## Game profiles

A profile sets **every** gameplay option. Every fixed profile includes the HUD and Classic Item Slots. Changing any
option afterwards switches the profile to **Custom** and keeps your value. The button style (Switch / PlayStation /
Xbox), the language and the emulator folder are not part of a profile. **Recommended** is the default and enables
everything.

Sprint is always **×1.25** in the profiles. It is only a starting point and can be changed by hand in the Stamina
section; the profiles never use ×1.75, ×2 or ×3.

| Profile | Stamina | Stamina style | Enemy HP | Damage | No hearts | Sprint | HUD | Classic |
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
dropped hearts become green rupees (the optional romfs file; see the note below).

## Window

- **Inicio**: profile list (the only profile selector), explanation of the active profile, emulator folder and install
  status.
- **Estamina**: on/off, stamina style, what costs stamina (the checkboxes update automatically for each style), sprint
  speed.
- **Dificultad**: enemy health, damage taken, heart drops.
- **HUD y botones**: rupee counter, clock, 24-hour clock, Classic Item Slots and button style.
- **Acerca de**: credits and the material/third-party notice.

The bottom bar always shows the install state and the **Instalar / Desinstalar** buttons. Changes are saved
automatically (250 ms debounce).

## Command line

The same install code is available without a window:

```
python app/main.py --cli --emu "RUTA_DEL_EMULADOR" --profile recommended
python app/main.py --cli --emu "RUTA_DEL_EMULADOR" --preset 3 --off jump,shoot --combat-only
python app/main.py --cli --emu "RUTA_DEL_EMULADOR" --profile hero-explorer --rupees --clock --clock24
python app/main.py --list-profiles
```

`--profile` applies a complete profile first; the individual flags override it. `--preset` keeps the numeric stamina
style used by older scripts (0 hardcore, 1 combat only, 2 sprint only, 3 advanced).

## Build

Run this on each target OS:

```
python tools/make_release.py     # module variants + optional romfs options (no Classic)
python tools/build_app.py        # release/SuperHeroBoostConfig[.exe|.app]
```

`build_app.py` uses the platform's separator for `--add-data` and writes the platform's native output. macOS needs
PyInstaller from the same Python installation used to build; Linux produces a plain executable.

Classic Item Slots is downloaded by the app at install time and cached in the per-user folder. If the machine is
offline the install stops with a clear error before touching the mod folder.

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
`F:\switch2\Longshot\romfs`, or `SHB_ROMFS`), and `make_release.py` keeps an existing `app/payload/romfs_opts` when
rebuilding. That file is only needed at build time: the release payload already includes the generated copy, so users
do not need a dump. If the file is missing, the app installs everything else and shows a note.
