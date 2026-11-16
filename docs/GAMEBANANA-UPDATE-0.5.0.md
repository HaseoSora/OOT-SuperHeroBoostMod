# GameBanana update 0.5.0

GameBanana has no public write API: the API (`api.gamebanana.com`, `apiv11/apiv12`) only reads data, and uploading a
file or editing a submission has to go through the website while logged in. This file is the copy-paste material for
that upload, so the page and the update match the 0.5.0 release.

## 1. Update: title and text

**Update name**

```
0.5.0 - Longshot crash fixes, DLSS/FSR kept, ReLink and cross-platform builders
```

**Update description**

```
0.5.0 fixes the Longshot crashes introduced in 0.4.0, keeps DLSS/FSR when the game is rebuilt, adds ReLink, finds
the right builder on Windows, Linux and macOS, and closes a running game instead of stopping the build at the end.

LONGSHOT / HOOKSHOT NOTICE
There has been a lot of feedback about Longshot problems since 0.4.0: crashes while loading a save or an area
(read 0x100000000038 / 0x80), a rebuild that stopped near 90% with "Longshot is still running from this folder",
DLSS disappearing after a rebuild, and the app choosing a ReLink or Hookshot builder for a Longshot game. This
update is meant to fix all of them. The module changed, so rebuild the game once with 0.5.0 (Install / Rebuild
game). If a crash remains, attach logs/longshot_log.txt and the new file in bug-reports/.

LONGSHOT CRASHES
- 0.4.0 was built with -Oz, which enabled LLVM's machine outliner: it moved the pointer guards into helpers that
  end in cmp+ret and the callers branched on those flags.
- Longshot's recompiler does not keep the flags of a cmp that ends a function, so the guard was skipped and a null
  pointer reached the HUD. Observed as read 0x100000000038 (guest 0x38) and read 0x100000000080 (guest 0x80) in
  hud_on_code.
- The module is now built with -mllvm -enable-machine-outliner=never; every guard comparison stays inline.

DLSS AND FSR
- The app reads the launcher's own settings and points the rebuild at the DLSS SDK (LONGSHOT_NGX_SDK /
  RELINK_NGX_SDK) and passes --fsr when the game had it.
- If the game had DLSS and the SDK is missing, the rebuild stops with a message instead of silently removing DLSS.
- If the launcher is not installed, the game's own longshot_options.ini / relink_options.ini is used.

RELINK
- Third supported static recompilation: .relink_exefs, bin/relink-game, ReLink.exe, RELINK_* variables and the
  builder under %LOCALAPPDATA%\ReLink\versions\<version>\ReLink.
- Its renderer, amd_fidelityfx_vk, VC runtime and item-wheel assets are backed up and restored with the rest.

BUILDER DETECTION
- Longshot, Hookshot and ReLink use their own builder; a ReLink or Hookshot builder is never picked for a Longshot
  game.
- Windows: %LOCALAPPDATA%. Linux: $XDG_DATA_HOME / ~/.local/share and ~/.config. macOS: ~/Library/Application
  Support. The builders' programs are bin/longshot and bin/relink-game without .exe, and the builder's own
  tools/python/bin/python3 is used.
- The builder path is optional in the app and can be changed.

NO MORE 90% STOP
- On Windows a running executable cannot be replaced. The app now closes any copy of the game running from the game
  folder before the install and keeps checking while the build runs, so the builder reaches the final swap.
- It still asks you to close a copy it cannot close (another user or an elevated process).

MANUAL SHIELD
- ZL follows the game's Targeting Type: hold to target in Hold Target, press to toggle in Toggle Target.
- Hold L to guard while the target camera is active; R3 cancels targeting. While enabled, the L item slot is
  removed from buttonMapping.

BUTTON MAPPING
- Follows the Swap Jump Controls option: the B item slot moves to X and the Jump label moves to B.

QUICK SELECT
- Removed the debug clock text (HOVER / HIERRO / MASCARA / LENTES); the clock always shows the time.

INSTALL / UNINSTALL
- The backup records every file the install and the rebuild touch and restores exactly that (including ReLink).
  The generated shader, program and pipeline caches are not copied and are deleted on uninstall.
- The module id check refuses a game whose main is not the supported build e0f3ccfa.

APPS
- Windows, Linux (x86_64) and macOS (Apple Silicon) builds, plus the SuperHeroBoost-0.5.0-presets.zip for
  emulators (12 profiles, no executables).
```

## 2. File to attach to the update

`release/SuperHeroBoost-0.5.0-presets.zip` (12 named profiles, no executables).

SHA-256: `9f8512fe1c92502847fa3fe070f0751b2a3c32aeed79a24398285af287b88fd0` (also in `release/SuperHeroBoost-0.5.0-presets.zip.sha256`).

## 3. Submission description

Paste the contents of `docs/GAMEBANANA-DESCRIPTION.txt` (updated for 0.5.0, with the Longshot notice at the top and
the new file names). Keep the "WHAT YOU ARE DOWNLOADING" and "NEW IN 0.5.0" blocks at the top.

## 4. Version fields

- The Mods submission **Version**: `0.5.0`.
- The Tools submission (`docs/GAMEBANANA-TOOL.md`): version `0.5.0`, with the Windows exe SHA-256 and the new
  features (ReLink, builder detection, closing the running game).

## 5. Checklist

- [ ] Update created with the title and text above.
- [ ] `SuperHeroBoost-0.5.0-presets.zip` attached and marked as the active file.
- [ ] Submission description replaced with `docs/GAMEBANANA-DESCRIPTION.txt`.
- [ ] Version field of the submission set to `0.5.0`.
- [ ] Longshot notice present at the top of the description and in the update text.
- [ ] Tools page version bumped and the exe SHA-256 updated (if you maintain it).
