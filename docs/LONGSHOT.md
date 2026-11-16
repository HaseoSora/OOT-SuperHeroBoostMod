# Longshot and Hookshot

Hookshot and Longshot are **not emulators**: they are static recompilations of the game. The console's code is
translated to C and compiled into a native program (`bin/hookshot`, `bin/longshot.exe`); the prepared guest image
lives in `image.bin`, next to it.

That changes how a code mod is installed.

## Why an `exefs` mod does not work

The official mod layout is the emulator one:

```
<game>/mods/<name>/romfs/...      files that replace (or add to) the game's RomFS
<game>/mods/<name>/exefs/...      ignored
```

`host/mods.c` in the builder says it plainly:

> exefs patches (.pchtxt, .ips) are not applied: the code is compiled ahead of time from the original instructions,
> and the game folder has no module map (image.json) to place data patches with. A mod's exefs folder is logged as
> left out.

The log line is `mods: <name>: exefs patches are left out (the code is compiled ahead of time)`. Patching
`.longshot_exefs/main` by hand does nothing either: that folder is only the source of the build, and the translated
code is already inside the executable.

So:

- **RomFS only** (button textures, patched event flows, resource size tables, enemy packs): copy the romfs files to
  `<game>/mods/Super-Hero-Boost/romfs/`. That is all the recompiler reads at run time. The HUD, stamina, item
  buttons and collectible counter are code, so they will not appear (and the item buttons also need their textures
  here).
- **The whole mod**: rebuild the game with the mod's code included in the translation.

## Rebuilding the game with the mod

The builder translates every module it finds in `.longshot_exefs` (`rtld`, `main`, `subsdk0`…`subsdk9`, `sdk`), so
the module goes in as a normal extra module:

1. Patch the 26 hook sites in `.longshot_exefs/main` (the same IPS patches the emulator version uses; the only
   difference is that the text segment starts at file offset `0x104` instead of `0x100`).
2. Copy the prebuilt `subsdk9` to `.longshot_exefs/subsdk9`.
3. Run the builder's update:

```bat
python -I nx2/make_game.py --update "F:\Switch2\Longshot" --work "F:\Switch2\temp"
```

`tools/install_longshot.py` automates all of it (backups, patched exefs, configuration, romfs mod folder and the
builder with its own Python). The companion app has the same procedure in its **Hookshot / Longshot** target, with a
progress bar; its **Install** applies the profile and romfs once the game is built, and **Rebuild game** runs this
update again.

```bash
# reuse the profile and the romfs files of an existing emulator install
python tools/install_longshot.py --game "F:\Switch2\Longshot" ^
    --config "E:\...\00-Super-Hero-Boost\exefs\subsdk9" ^
    --romfs  "E:\...\00-Super-Hero-Boost\romfs"

# or the payload defaults (Switch buttons, no optional romfs files)
python tools/install_longshot.py --game "F:\Switch2\Longshot"
```

The update takes about as long as the first build (25–45 minutes on the reference PC: most of it is the GPU
shaders). It replaces `bin/longshot.exe` and `image.bin`; the romfs and saves are kept.

### If the builder cannot find the Vulkan headers

The update also compiles `longshot_vk.dll` (the Vulkan back end). A builder package ships the Vulkan, SPIR-V and VMA
headers in `tools/cpm`; the installer points `RX_CPM` there when that folder exists. If the builder still stops with
`no headers for longshot_vk.dll (missing Vulkan, VMA)`, the installer reuses the renderer already in the game
(`bin/longshot_vk.dll` or `bin/longshot_vk.so`) through `LONGSHOT_VK_PREBUILT`: it copies that file into the build's
work folder first, because the builder updates in place and cannot copy a file onto itself. Without an existing
renderer, install `vulkan-headers`, `spirv-headers` and `vulkan-memory-allocator` (or set the three
`LONGSHOT_*_HEADERS` variables / `RX_CPM` to a CPM cache) and run the update again.

### Why this works

The recompiler's module order is `rtld`, `main`, `subsdk0`…`subsdk9`, `sdk`, page-aligned. With `main` at
`0x80020000`, `subsdk9` lands at `0x84FA0000`, which is `main + 0x4F80000`: exactly the address the module is linked
at. The hook branches are PC-relative, so they reach it without any relocation.

The lift was checked with the patched exefs before building:

```
image: rtld@0x80000000, main@0x80020000, subsdk0@0x84EC0000, subsdk9@0x84FA0000, sdk@0x8547E000
subsdk9   72 functions, 100.00% complete, 12707 instructions, 0 untranslated
```

The module has no `DT_INIT` (init `0`), so the runtime does not need to call it; the hooks enter its code directly.

### Configuration

The configuration is a block inside `subsdk9`'s `.data` (magic `SHBCFG01`, 72 bytes, see
[GUIA-DESARROLLO.md](GUIA-DESARROLLO.md)). **The prebuilt module carries the factory block: stamina and songbook on,
HUD, button mapping and collectible counter off.** That is why a plain rebuild seems to show only the stamina bar.
Use `--config` with the module of an existing emulator install (that is what the app wrote) or patch the block by
hand before building.

The configuration also sits in `image.bin`, which is loaded into the guest at run time, so it can be changed **without
rebuilding** once the game has been built:

```bash
python tools/install_longshot.py --game "F:\Switch2\Longshot" --config "...\subsdk9" --config-only
```

The romfs side (button textures, Great Fairy, Farore, no heart drops, enemy options) is a separate copy in
`<game>/mods/Super-Hero-Boost/romfs`; it can be replaced at any time with the game closed.

## Verified on the reference build

- The recompiled `bin/longshot.exe` boots to the title screen at 60 fps with `subsdk9`'s code in it.
- Longshot's `HOS_WATCH` breakpoint on `g_wrap_entry[3]` (`0x84FB4C34`) counted **148 writes** during the first
  seconds, with the value `10000000` read from the module's `.data`: the module's input hook is running in the
  recompiled game.
- The mods log shows `mods: Super-Hero-Boost: 33 RomFS files` and the resource size table and `DropGlobalParam`
  overrides being used.

## Reverting

`--uninstall` restores `bin/longshot.exe`, `image.bin` and `.longshot_exefs/main` from `<game>/.shb-backup` (made on
the first install), removes `subsdk9` and deletes `<game>/mods/Super-Hero-Boost`. Nothing has to be recompiled when
that backup exists.

## Hookshot

Hookshot is the original project; Longshot is its continuation. Both ship the same builder (`HookshotBuilder` or
`LongshotBuilder`, with the `tools` folder beside it) and the same `nx2/make_game.py --update`. Pass its folder with
`--builder`; the rest of the procedure is identical.
