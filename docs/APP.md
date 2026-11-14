# Companion app (OotMasterConfig.exe)

The app does **not** compile anything. The mod ships precompiled in two variants (`app/payload/classic`,
`app/payload/standalone`) and reads a small config block (`core/config.h`, magic `OOTMCFG1`) when the game loads.
The app only:

1. finds the emulator's mod folder (`user/load/0400486024DEC000`, honouring a custom load directory),
2. patches the config bytes inside the prebuilt `subsdk9`: stamina on/off, preset, per-action costs, combat only,
   enemy health, damage taken, rupee counter / clock / 24 h, sprint speed (field table in
   [GUIA-DESARROLLO.md](GUIA-DESARROLLO.md#33-configuración-en-tiempo-de-ejecución-coreconfigh)),
3. with Classic Item Slots enabled, takes the chosen variant (Switch / PlayStation / Xbox) bundled in the payload
   (v1.4.3, staged by `make_release.py` from Classic's official release page), copies its module as `subsdk8` and its
   romfs, and merges the two IPS patch files (they are checked for overlaps),
4. with "no heart drops", copies the generated romfs option,
5. writes everything as the mod folder `00-OOT-Master` and warns about other exefs mods that may conflict.

Files: `app/ootconfig.py` (window + `--cli` mode), `app/installer.py` (install logic, config patching),
`app/i18n.py` (texts in en / es / pt / fr / de / it). Settings are remembered in `OotMasterConfig.json` next to
the exe.

Developer steps (only when the mod code changes): `python tools/make_release.py` then `python tools/build_app.py`
(close the running exe first). See [GUIA-DESARROLLO.md](GUIA-DESARROLLO.md).
