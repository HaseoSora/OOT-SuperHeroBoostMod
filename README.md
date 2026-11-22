# Super Hero Boost

Gameplay module for the console remake (update **v131072**) and its cross-platform configuration app
**SuperHeroBoostConfig**.

Current release: **0.9.0**, with a **Rekarina** target: the app installs the mod into Rekarina's game folder and
rebuilds it with Rekarina's own tools, without editing Rekarina. The 0.8.0 item quantities, the game's own ZR item,
A to put the sword away, no magic jar drops, boss speed and the L3 sprint toggle remain.

### What's new in 0.9.0

- **Rekarina supported.** Rekarina is the Switch 2 static recompilation that loads ExeFS modules and takes romfs mods.
  Its launcher rejects code modules (`exefs/subsdk*`) and its lift only knows `main,subsdk0,sdk`. The app now:
  adds the mod's module as `subsdk9` to the lift, compiles it with **Rekarina's own** `gen.py` and `build_game.py`,
  converts the mod's IPS with its `tools/exefs_patches.py`, installs the romfs as
  `mods/zz-Super-Hero-Boost/romfs`, puts the mod first in `mods_order`, and replaces `Rekarina.exe` with the new
  build (backed up). Nothing in the Rekarina folder is edited.
- **Settings without a rebuild.** The module's configuration lives in its own data block; applying a profile
  patches `exefs/subsdk9` and the expected SHA-256 stored in `Rekarina.exe`, so changing options takes seconds. A
  full rebuild (10-20 minutes) is only needed the first time or when the module itself changes.
- **Old merged code disabled safely.** If a merged mod folder (for example the Mod Merger's `0-M`) still carries the
  old `subsdk9`/IPS, the app moves it aside (backed up); Rekarina then stops marking the whole mod as PLUGIN and its
  romfs loads.
- **Uninstall** restores the exe, the module, the old mod code, the status files and the mod order.

### What was new in 0.8.0

- **Item quantities.** The B / L / R / ZR buttons show the quantity of the consumables (sticks, nuts, bombs, seeds,
  bombchus, beans and arrows); unique items show no number.
- **The game's ZR item.** ZR is always the item the game's own box has (R selector, pause menu A, the save). A slot item
  is used through the box and it goes back to the ZR item once Link stands or walks again, not while aiming (a bow on R
  shoots its own arrow). Assigning ZR to a button, or a button's item to ZR, swaps them for real.
- **Put the sword / item away.** With an item on B, A while standing still puts the sword or the item in hand away
  (B's own function); A still talks, opens and rolls as usual.
- **Menus fixed.** The mod's HUD buttons kept the game's item-box "focusable" flag, so the cursor went onto them: in
  shops, dialogues, the game-over screen, Farore's Wind and past the Megaton Hammer on the Items page you had to press
  up / down a few times first. They are no longer focusable. The songbook no longer reads the ocarina while it is closed.
- **Hide the corner minimap.** New HUD option: the corner map (compass included) is not drawn while you play; the map
  screen (Minus) still works.
- **No magic jar drops.** New Difficulty option: dropped magic jars become green rupees, like the heart option. Both
  can be on at the same time.
- **Boss speed (beta).** Bosses and minibosses, left out of the enemy speed, have their own movement and animation
  multipliers in the Beta tab. Some bosses move by script, so animation is what speeds them up.
- **L3 sprint as a toggle.** One press of L3 starts the sprint and the next stops it; it also stops when stamina runs
  out, when you press A, and in dialogues.
- Install 0.8.0 and **rebuild the game once** on Longshot, Hookshot or ReLink: the module changed.

### What's new in 0.7.0

- **Switch target.** While Link is locked on, a **tap of the target button** (ZL, or R3 with the ZL/R3 swap) moves the
  lock to the enemy the game marks in **red** (the nearest one that is not locked); **holding it** (~0.3 s) drops the
  target. With no target the button locks on as usual. It uses the game's own attention list (the player's candidate
  array: the game locks element 0 and marks element 1), so the camera, the lock triangles and the marker follow by
  themselves. Its own option in **Controls**; needs System > Options > Targeting Type on **Toggle**.
- **Next target when the locked enemy dies.** Its own option in **Controls**, independent of the manual shield. It now
  follows the game's real lock (the AttentionSystem's lock link) and acts only when the locked enemy dies: walking up
  to enemies, the battle stance and a target you drop yourself no longer lock on by themselves.
- **Manual shield.** The target button always reaches the game (it used to be re-created from the player's action
  names, which also show up near enemies without a target: with ZL targeting the game then locked on by itself).
  "Targeting" is the game's own lock; L is never taken while you only stand near enemies. R3 still cancels the
  target when the ZL/R3 swap is off.
- **Profiles.** New **Souls controls** (vanilla difficulty) and **Souls controls + Hero Mode**: hardcore stamina as a
  bar, lock-on with R3, switch / next target and the manual shield. Every combat profile with the manual shield
  (Recommended, Hero, Super/Ultra Hero, Survival, Beta: everything) now also turns the switch and next target on.
- **HUD labels follow the game's language.** The labels the mod draws itself (Jump / Attack / Roll and the menu's
  Assign:) were always in Spanish; the installer reads the game's language (ReLink/Longshot `language.txt`, the
  emulators' settings) and the HUD uses it. `--lang` forces one.
- Install 0.7.0 and **rebuild the game once** on Longshot, Hookshot or ReLink: the module changed.

### What's new in 0.6.0

- **ReLink: every feature works.** ReLink's translator writes each function in address order and starts at its lowest
  address; a tail call to a function placed lower in the module made the caller's own start unreachable. Under
  ReLink the input dispatcher ran only the quick select, so stamina never drained (and flashed yellow on every
  action), the manual shield's L, the button mapping assignment and the R3/L3 controls did nothing. The module is
  now built without tail calls and the build fails if one appears. **Rebuild the game once** for the new module.
- **Manual shield.** With **Hold** targeting, only the held target button counts as a target (the game's lock-on
  state lingers after release and after attacks, which raised the shield without a target). With no target, **L
  keeps its default game function**; it is ours only while targeting or guarding, until it is released.
- **Button positions.** New button mapping option: **Nintendo** (default), **A and B swapped** or **Xbox** (A/B and
  X/Y swapped), to match the button layout chosen in Longshot or ReLink. The HUD and the pause menu draw each face
  button, its item and its label where it is on the controller; the game's **Swap Jump Controls** option still
  applies on top.
- **Game button prompts are a separate, optional choice** in the **HUD** section (None / PlayStation / Xbox, None by
  default). The button style now only picks the button mapping's own pictures; Longshot and ReLink already ship
  their own prompts.
- **App.** A **Play** button opens the emulator or the recompiled game's launcher; the scrollbars follow the app's
  theme; on a recompiled game, the main switch of each feature shows a red **Requires rebuild** tag (sub-options do
  not). New `--bm-layout` and `--game-layout` flags.

### What's new in 0.5.1

- **Enemy speed reworked.** Movement now scales every base and attack speed together (walk, run, dash, jog, strafe,
  attack motions and the per-enemy attack speeds), so enemies no longer slide or overshoot.
  **Animation playback**, **attack cadence** and **projectile speed** are independent, with eleven multipliers from
  x0.5 to x6 each (plus off). Attack cadence scales the interval tables and the action timeouts; the beta enemy
  profiles set all four components to x2.
- **Controls section.** **Target with R3** swaps ZL and R3 (R3 targets, ZL resets the camera; set System > Options >
  Targeting Type to **Hold**). **Hold L3** to sprint with the game's own sprint animation, without pressing A or
  rolling. Both are personal preferences and are off by default.
- **Manual shield.** L stays reserved while the shield is enabled, including during hit reactions and hit-stop; R3
  cancels targeting unless the target-on-R3 swap is on.
- **App.** New **Controls** section, an enemy **Projectiles** selector and `--enemy-proj`, `--target-r3` and
  `--sprint-l3` flags. The beta enemy profiles include the projectile speed.
- The 0.5.0 fixes remain: Longshot crashes, DLSS/FSR on rebuild, ReLink, builder detection on Windows, Linux and
  macOS and closing the running game before a build. Rebuild the game once with 0.5.1 for the new module.

### What's new in 0.5.0

- **Longshot 0.4.0 crashes fixed.** 0.4.0 was built with `-Oz`, and LLVM's machine outliner moved the pointer guards
  into helper functions that return with the condition flags. The Longshot recompiler does not keep those flags
  across a call, so a null pointer reached the HUD (Longshot crashed reading guest `0x38`/`0x80` while loading a save
  or an area). The module is now built without the outliner; **rebuild the game once** with 0.5.0 so the new module
  is baked into `image.bin`.
- **DLSS and FSR survive a rebuild.** The app reads the launcher's own settings (Longshot/Hookshot `settings.json`
  and `builds.json`, ReLink `launcher.ini`), points the builder at the DLSS SDK and passes `--fsr` when the game had
  it. If the game had DLSS and the SDK is missing, it stops with a message instead of silently removing DLSS.
- **ReLink supported** as a third static recompilation, with its `.relink_exefs`, `bin/relink-game`, builder and
  `RELINK_*` variables. Longshot, Hookshot and ReLink each use their own builder: the app no longer picks a ReLink or
  Hookshot builder for a Longshot game.
- **Builder detection on Linux and macOS** as well as Windows: `%LOCALAPPDATA%` on Windows, `$XDG_DATA_HOME` or
  `~/.local/share` on Linux, `~/Library/Application Support` on macOS; `bin/longshot` and `bin/relink-game` without
  `.exe`; the builder's own `tools/python/bin/python3` (or a system `python3`). The builder path is optional in the
  app and can be changed.
- **The app closes a running copy of the game** before installing and while the build runs (Windows), instead of
  failing at about 90% with "Longshot is still running from this folder". It still asks you to close a copy it cannot
  close (another user or an elevated process).
- **Manual shield**: ZL follows the game's **Targeting Type**; hold L to guard while the target camera is active;
  **R3** cancels targeting. While it is enabled, the L item slot is removed from buttonMapping.
- **Button mapping**: follows the game's **Swap Jump Controls** option; the B item slot moves to X and the Jump
  label moves to B.
- **Quick select**: removed the debug text that replaced the clock with HOVER/HIERRO/MASCARA/LENTES; the clock always
  shows the time.
- **Install and uninstall**: the backup records every file the install and the rebuild touch (including ReLink files)
  and restores exactly that; the generated shader and pipeline caches are deleted, not copied.

### What's new in 0.4.0

- **Three HUD layouts**: **Wide** (the four native-style plates), **Simple** (the four counters at the bottom,
  no background) and **Minimal** (rupees + time above the minimap; the area heart-piece counter next to the native
  Skulltula counter on the **Minus** map).
- **Bottle icons**: B/L/R and ZR now show the assigned bottle and its exact content: red/green/blue potion, blue
  fire, fish, bug, fairy, milk, half milk, letter, Poe, Big Poe or an empty bottle.
- **Enemy speed**: movement, animation playback and attack cadence are independent, with eleven multipliers from
  x0.5 to x6 (plus off); the duplicated-enemy placements also work now.
- **Stamina bar**: optional compact segmented bar instead of the ring around Link.
- **Longshot**: if the builder cannot find Vulkan/VMA headers, the installer reuses the installed
  `longshot_vk.dll`/`.so` instead of failing.
- **CI**: Windows, Linux and macOS apps and the presets pack build with GitHub Actions.

The mod adds stamina, difficulty scaling, an expanded HUD, extra item buttons and boots/mask quick select, all
configurable without recompiling anything. The app patches the prebuilt module and copies the files the game needs.
The module, the HUD, the textures and the app are original work: no third-party mod is bundled or downloaded.

## Features

### Gameplay

- **Complete profiles**: Recommended (everything on), Souls controls, Souls controls + Hero Mode, Base, Manual Shield,
  Hero Mode, Hero + Stamina, Hero Explorer, Super Hero, Ultra Hero, Survival, World changes and the two beta
  combinations (duplicated + fast enemies, everything). They set difficulty, stamina, the HUD, the world changes, the
  manual shield, the targeting and the beta mods in one step; changing any option afterwards switches the profile to
  **Custom**. The Souls profiles also turn on the stamina bar and the lock-on with R3.
- **Stamina** with four styles: hardcore (everything costs), combat only, sprint only and advanced (choose which
  actions cost). Includes exhaustion and regeneration, and costs for rolling, jumping, attacking, shooting,
  sprinting and blocking with the shield.
- **Stamina display**: a ring next to the player or a segmented bar under the magic gauge (yellow, red while
  recharging; grows with your hearts).
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
- **Three HUD layouts**: **Wide** (the four plates), **Simple** (the four counters at the bottom, no background) and **Minimal**
  (rupees and time above the minimap, with the area heart counter next to the native Skulltula counter on the Minus
  map).
- **World changes**: reorders the three Great Fairy magic rewards (Hyrule Castle child gives **Nayru's Love**, Death
  Mountain Crater the **magic spin attack** and Desert Colossus **double magic**) and allows placing **Farore's Wind**
  warp points outside dungeons. Each fountain keeps her own model and dialogue; the Din fairy's overview still
  describes the original order.
- **Own button mapping** (`buttonMapping`):
  - **B, L, R and ZR** item buttons on the HUD, assignable from the **Items** tab of the pause menu.
  - **Switch / PlayStation / Xbox** button pictures for the mapping HUD.
  - **Button positions**: Nintendo, A and B swapped, or Xbox (A/B and X/Y swapped), to match the recompilers'
    button layout. Only where the buttons are drawn changes; the game's logical buttons stay the same.
- **Game button prompts** (HUD section, optional): replace the game's own prompts, font and controller picture with
  PlayStation or Xbox ones, downloaded once (~70 MB) from GameBanana and cached. None by default; Longshot and
  ReLink already include their own.
  - **Extended** layout (B, L, R, ZR, X, Y, A and the sword) or **simple** layout (only the assignable buttons, with
    B centred and L / R / ZR repositioned so there are no gaps).
  - **L button modes**: item or the game's item selector.
  - **Jump/B swap**: if the game's System > Options **Swap Jump Controls** is on, the B item slot moves to **X**
    automatically (input, icon position and menu legend); B keeps its native jump.

### Quick select

- **D-pad Down**: switch between the **Iron Boots** and **Hover Boots** without opening the pause menu. From the
  default boots it picks the first of the two you own.
- **D-pad Up**: switch between the **Lens of Truth** and the **mask** you were wearing.
- Only items in your inventory are used. The change is applied immediately through the game's own equip request,
  not just written to the save.
- A short tap keeps the game's normal D-pad behaviour.
- The named profiles (including **Recommended**) turn it on; each selector can still be disabled in the app's
  **Quick select** section. It writes the game's equipment live, so keep a save backup.

### Manual shield

- **ZL follows the game's Targeting Type option** (System > Options): in **Hold Target**, hold ZL to target; in
  **Toggle Target**, press ZL to toggle.
- **L raises the shield only while targeting.** With no target it keeps its default game function; while targeting
  or guarding (including shield-hit reactions and hit-stop) it is reserved until it is released, so the item
  selector never opens in the middle of a guard. "Targeting" is the game's own lock (and, in Hold Target, the held
  target button); standing near enemies is not.
- **R3** cancels targeting, unless the target-on-R3 swap is enabled.
- Optional: it is off by default and can be enabled in the app's **Controls** section.
- The target button always reaches the game as you press it; the game's Hold/Toggle option decides.
- Independent of the stamina system: the stamina config still applies its own held/hit costs when stamina is on.

### Controls

- **Target with R3**: swaps ZL and R3, so R3 holds or toggles the target camera and ZL resets it. Recommended with
  the game's **Hold** targeting type.
- **Hold L3** to sprint: uses the game's sprint flag and animation, without pressing A and without rolling.
- **Switch target with the target button**: while locked on, tap the target button (ZL, or R3 with the swap) to move
  the lock to the enemy with the red marker; hold it to drop the target. With no target it locks on as usual.
  Needs Targeting Type on **Toggle**.
- **Next target when it dies**: when the locked enemy dies, the next one is locked on automatically (nothing happens
  when there is none, or when you dropped the target yourself). Needs Targeting Type on **Toggle**.
- The manual shield and button mapping are described above and below. Target with R3 and L3 sprint are personal
  preferences (only the Souls profiles turn R3 on); the switch and next target come with the combat profiles.

### Configuration app

- GUI for Windows, macOS and Linux (Python 3.10+ with Tkinter).
- Profiles, per-section settings, install and uninstall into the emulator's mod folder, including a
  **Controls** section for the R3 target swap and the L3 sprint.
- **Play** opens the emulator (or the recompiled game's launcher) directly.
- On Longshot, Hookshot and ReLink, a red **Requires rebuild** tag marks the feature switches whose change needs the
  builder; their sub-options do not.
- **Quick select**: boots and mask switching from the D-pad.
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
- **Enemy speed**: four independent components (movement, animation playback, attack cadence and
  projectile speed), each with eleven multipliers from x0.5 to x6 (plus off). Movement scales
  every base and attack speed together, so enemies do not slide or overshoot.
  Attack cadence scales the interval tables and the action timeouts; projectiles are separate. Some
  enemies or attacks may not change or may desync.
## Usage

1. **Requirements**: the game on update **v131072** and an emulator that loads mods from its
   `user/load/0400486024DEC000` folder (or the path you have configured). Back up your save before installing.
2. Open **SuperHeroBoostConfig** (or run `python app/main.py` from source).
3. Pick a profile or adjust the sections one by one.
4. Select the emulator folder. The app finds the mods folder, including a custom `load_directory` from
   `qt-config.ini`.
5. Press **Install**. The app creates the `zz-Super-Hero-Boost` folder with the module, the button textures and the
   optional romfs files, and patches the selected configuration.
6. Close the game before uninstalling. On Windows the app closes a running game before installing and during
   a rebuild (it cannot replace a running executable); save your progress first.

To remove the mod, press **Uninstall** in the app or delete the `zz-Super-Hero-Boost` folder.

Prebuilt binaries are published on the [Releases](https://github.com/kuribox/OOT-SuperHeroBoostMod/releases) page;
you can also build the app from source with the steps below.

| Your system | Download |
|---|---|
| Windows | `SuperHeroBoostConfig.exe` |
| Linux (x86_64) | `SuperHeroBoostConfig-linux` — `chmod +x SuperHeroBoostConfig-linux` after downloading |
| macOS (Apple Silicon) | `SuperHeroBoostConfig-macos.dmg` — open it and drag the app to Applications (not signed: right-click > Open the first time) |
| Emulator, no app | `SuperHeroBoost-<version>-presets.zip` — ready-to-install mod folders |

The Windows build is the only one with a `.exe` extension; the Linux one is a plain executable named with
`-linux` and the macOS one is a `.dmg` disk image.

### Longshot, Hookshot and ReLink

Hookshot, Longshot and ReLink are static recompilations, not emulators: they translate the game to native code and
ignore `exefs` mods by design. The romfs files work from `<game>/mods/zz-Super-Hero-Boost/romfs`, but the module (HUD,
stamina, item buttons, collectible counter) has to be built into the game.

- **Longshot: supported and tested.** The app's **Longshot** target patches the game's `main`, copies the module to
  `.longshot_exefs`, installs the chosen romfs options and runs the builder's update with a progress bar. The first
  build takes 25-45 minutes; later code changes are incremental (~5 minutes) and profile/romfs-only changes need no
  rebuild. It is reversible with **Uninstall**. 0.5.1 includes the 0.5.0 crash fixes; rebuild once with 0.5.1 for
  the new controls/enemy module.
- **Hookshot: expected to work, not tested yet.** It ships the same builder and the same
  `nx2/make_game.py --update`; point the app's target (or `tools/install_longshot.py --builder`) at its
  `HookshotBuilder` folder. The procedure is otherwise identical.
- **ReLink: supported.** Its game is `bin/relink-game`, its exefs `.relink_exefs` and its builder
  `%LOCALAPPDATA%\ReLink\versions\<version>\ReLink` (or the Linux/macOS data folder). The same install, rebuild
  and uninstall steps apply. Tested with a full ReLink 0.7.9 build: stamina, manual shield, button mapping and
  controls work after rebuilding with the current module (see "Changes since 0.5.1").
- **Rekarina: supported (new in 0.9.0).** Point the target at Rekarina's game folder (the one with `Rekarina.exe`,
  `rekarina.ini` and `exefs/main`); the app finds `setup/<version>` beside it and drives Rekarina's tools. It never
  edits Rekarina: the lift runs `gen.py --modules main,subsdk0,sdk,subsdk9`, the compile runs `build_game.py`, and
  the ExeFS patches go through `tools/exefs_patches.py`. Two runners in the work folder add the compile flags and the
  hook resume points as extra `main` seeds (Rekarina dispatches only to function starts). The module is built for
  Rekarina's layout (`main+0x5200000`) with a synthetic `eh_frame_hdr` seed table and a minimal dynamic symbol table
  (its loader requires one). The mod's IPS stays in `mods/zz-Super-Hero-Boost/exefs` so its runtime switches the
  generated code set on. The first build takes 10-20 minutes and ~6 GB in `game/.shb-rekarina`; later settings
  changes take seconds. Uninstall restores the exe and every file the install touched.
- The app finds the builder of the game's own flavor on Windows, Linux and macOS, and shows whether it was detected
  or chosen by hand. `LONGSHOT_BUILDER`, `HOOKSHOT_BUILDER` and `RELINK_BUILDER` override it.

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
python app/main.py --cli --emu "EMULATOR_PATH" --profile base --enemy-move 1 --enemy-anim 2 --enemy-attack 2 --enemy-proj 2
python app/main.py --cli --emu "EMULATOR_PATH" --profile recommended --target-r3 --sprint-l3
python app/main.py --cli --emu "EMULATOR_PATH" --profile recommended --bm-layout xbox --game-layout none
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

- [HaseoSora](https://github.com/HaseoSora) for the **Switch GameCube** preset with its button artwork and
  controller diagram, and for grouping the HUD panes so the clusters keep their alignment under widescreen
  ("screen's edges") layouts.
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
