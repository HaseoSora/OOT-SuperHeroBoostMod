# Companion app (OotMasterConfig.exe)

The app does **not** compile anything. The mod ships precompiled in two variants (`app/payload/classic`,
`app/payload/standalone`) and reads a small config block (`core/config.h`, magic `OOTMCFG1`) when the game loads.
The app only:

1. finds the emulator's mod folder (`user/load/0400486024DEC000`, honouring a custom load directory),
2. patches the config bytes inside the prebuilt `subsdk9` (preset, per-action costs, combat only, stamina on/off),
3. with Classic Item Slots enabled, downloads the chosen variant (Switch / PlayStation / Xbox) from Classic's official
   release page (cached under `%APPDATA%\OotMasterConfig`), copies its module as `subsdk8` and its romfs, and merges the
   two IPS patch files (they are checked for overlaps),
4. writes everything as the mod folder `00-OOT-Master`.

Developer steps (only when the mod code changes): `python tools/make_release.py` then `python tools/build_app.py`.
