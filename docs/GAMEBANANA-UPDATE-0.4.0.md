# GameBanana update 0.4.0

GameBanana has no public write API: the API (`api.gamebanana.com`, `apiv11/apiv12`) only reads data, and
uploading a file or editing a submission has to go through the website while logged in. This file is the
copy-paste material for that upload, so the page and the update match the 0.4.0 release.

## 1. Update: title and text

**Update name**

```
0.4.0 - HUD layouts, bottle icons and enemy options
```

**Update description**

```
Three HUD layouts, exact bottle icons on the item buttons, reworked enemy speed and duplication, and the
optional compact stamina bar.

HUD
- Wide: the four native-style plates at the bottom.
- Simple: just the four counters at the bottom, no background, with the sun/moon clock icon.
- Minimal: rupees and time above the minimap; the area heart-piece counter sits next to the native Skulltula
  counter on the Minus map.

Bottle icons
- B, L, R and ZR now show the assigned bottle and its exact content: red, green and blue potions, blue fire,
  fish, bug, fairy, milk, half milk, letter, Poe, Big Poe and empty bottles.

Enemy speed and duplication (beta)
- Movement, animation playback and attack cadence are independent, each with eleven multipliers from x0.5
  to x6 (plus off).
- The duplicated-enemy placements now clone every eligible enemy and share the original resources, so the
  extra enemies appear and behave.

Stamina
- Optional compact segmented bar instead of the ring around Link.

Longshot
- If the builder cannot find its Vulkan/VMA headers, the app reuses the installed longshot_vk library
  instead of failing.

Apps
- Prebuilt configuration app for Windows, Linux (x86_64) and macOS (Apple Silicon), plus the
  SuperHeroBoost-0.4.0-presets.zip here for emulators.
- The in-app update check now finds the platform build automatically.
```

## 2. File to attach to the update

`release/SuperHeroBoost-0.4.0-presets.zip` (43.3 MB, 11 profiles, no executables).

SHA-256: see `release/SuperHeroBoost-0.4.0-presets.zip.sha256` after `python tools/build_app.py`, or the
`.sha256` asset of the GitHub release. Upload the one published on GitHub so both pages carry the same file.

## 3. Submission description

Paste the contents of `docs/GAMEBANANA-DESCRIPTION.txt` (it already lists the 0.4.0 changes and the new
file names). Keep the "WHAT YOU ARE DOWNLOADING" and "NEW IN 0.4.0" blocks at the top.

## 4. Tools page (optional)

`docs/GAMEBANANA-TOOL.md` is the entry for the configuration app. Update its version line to 0.4.0 and
mention the Linux and macOS builds; the Files tab there can point at the GitHub release, since the app
itself is not attached to the mod page.

## 5. Checklist

- [ ] Update created with the title and text above.
- [ ] `SuperHeroBoost-0.4.0-presets.zip` attached and marked as the active file.
- [ ] Submission description replaced with `docs/GAMEBANANA-DESCRIPTION.txt`.
- [ ] Version field of the submission set to `0.4.0`.
- [ ] Tools page version bumped (if you maintain it).
