# Super Hero Boost 0.7.0

0.7.0 brings **souls-like targeting**: switch to the red-marked enemy with the target button, hold it to drop the
target, and the next enemy is locked on when the current one dies. Two new **Souls controls** profiles put it together
with the stamina bar, the lock-on with R3 and the manual shield, and the mod's own HUD labels now follow the game's
language. The 0.6.0 ReLink fix, manual shield and button positions remain.

## Switch target

- While Link is locked on, **tap the target button** (ZL, or R3 with the ZL/R3 swap) to move the lock to the enemy the
  game marks in **red**: the nearest one that is not locked.
- **Hold it** (about 0.3 s) to drop the target.
- With no target the button locks on as usual.
- It works through the game's own attention list: the game locks the first candidate and marks the second, so the
  camera, the lock triangles and the red marker follow by themselves.
- Its own option in **Controls**. Needs System > Options > Targeting Type on **Toggle**.

## Next target when the locked enemy dies

- Its own option in **Controls**, independent of the manual shield.
- It follows the game's real lock and acts only when the locked enemy dies. Walking up to enemies, the battle stance
  and a target you drop yourself no longer lock on by themselves.
- Needs Targeting Type on **Toggle**.

## Manual shield

- The target button always reaches the game. It used to be re-created from the player's action names, which also
  show up near enemies without a target, so with ZL targeting the game locked on by itself.
- "Targeting" is the game's own lock: L is never taken while you only stand near enemies.
- R3 still cancels the target when the ZL/R3 swap is off.

## Profiles

- **Souls controls** (vanilla difficulty) and **Souls controls + Hero Mode** (x1.5 enemy health, x2 damage, no heart
  drops): hardcore stamina shown as a bar, lock-on with R3, switch and next target, manual shield on L.
- Every combat profile with the manual shield (Recommended, Hero, Hero + Stamina, Hero Explorer, Super Hero, Ultra Hero,
  Survival, Beta: everything) now also turns the switch and next target on.
- Target with R3 and L3 sprint stay personal preferences in the other profiles.

## HUD labels in the game's language

- The labels the mod draws itself (Jump / Attack / Roll and the menu's Assign:) were always in Spanish.
- The installer reads the language the game is played in (`language.txt` next to a recompiled game, the emulators'
  settings) and the HUD uses it; the app's language is the fallback. `--lang` forces one.

## Enemy duplicator (beta)

- Stalchildren now double as well. Each spawn zone in the maps carries its own group size (2 small, 1 big, larger
  groups by the road); the duplicator only cloned hand-placed enemies and never touched those zones. It now doubles
  every count of the spawn zones and the scene's cap on them.
- It no longer turns on spawns the game keeps off: adult Link got Stalchildren from the doubled "0" of the adult
  spawn.

## Updating

- **Emulator:** install 0.7.0 from the app.
- **Longshot, Hookshot and ReLink:** install 0.7.0 and **rebuild the game once**: the module changed.
- Set System > Options > Targeting Type to **Toggle** for the switch and next target.
