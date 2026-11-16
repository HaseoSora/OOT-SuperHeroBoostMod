# Análisis de `hardercombat10.zip`

Origen: `F:\Downloads\hardercombat10.zip` (analizado el 16/11/2026 en la rama
`feat/harder-combat-enemy-speed`).

## Contenido

- 177 packs de romfs: 144 `Pack/Actor/Enemy_*.pack.zs` y 33 packs de proyectiles
  (`*_Bullet_*.pack.zs`, `ScrubDeku_DekuNut.pack.zs`, etc.).
- **Todas las diferencias son BYML** (parámetros); no toca animaciones ASB ni código.
- Se comparó cada pack contra el dump vanilla (`F:\Switch2\Longshot\rc\romfs`) miembro por miembro.

## Qué cambia (agregado sobre los 177 packs)

| Grupo | Campo(s) | Cambio |
|---|---|---|
| Movimiento base | `BSA/MovementParam`: WalkSpeed, RunSpeed, DashSpeed, EscapeSpeed, JogSpeed, SpecialMoveSpeed, StrafeSpeed, LiftWalkSpeed, WalkBackwardsSpeed | **x3.0** |
| Movimiento de ataque | `Game/BSA/ActionSeqContainer`: ChargeAttackMoveSpeed, AttackTransSpeed, SurpriseAttackMoveSpeed, AttackFlySpeed | **x3.0** |
| Movimiento por enemigo | `GameParameter/*Param`: AttackMoveSpeed, LandAttackMoveSpeed, Attack1st/2ndSpeed, AttackSpeed, AttackSpeedInWater, AttackJumpSpeed, AttackHitSpeed, etc. | **x3.0** |
| Proyectiles | BulletSpeed, ShootInitialSpeed, RangedAttackInitSpeed, SecondBulletFireSpeed, LightBallSpeed, BulletMax/MinSpeed | **x3.0** |
| Cadencia de ataque | `GameBalance/AttackInterval` (Long/Medium/Short, Min/Max) y campos `*AttackInterval*` por enemigo | **x0.02** (÷50) |
| Daño | `GameBalance/AttackParam/BaseAttackPower` | **x5.0** |
| Vida | `Life/LifeParameters/MaxLife` | **x2.0** |
| Percepción | `EnemyCommonParam/DiscoverSpreadDist(+Extend)` | **x1.25** |
| Vista | `PerceptionReceiverParam/SightParam`: Alert/Discover/TrackHorizontalRange | **x1.2** |
| Cerebro | `GeneralCounterRef`: LoseSightOfTarget, InaccessiblePassFinding, TemporaryReturnTimer | **x2.5** |
| Defensa | `StalfosParam`: QuickGuardProbability, RepelledSwiftAttackProb | **x1.4** |
| Lizalfos | `LizalfosParam`: SwitchActionTimeOnNotAtkPermit/Rnd | **x0.6** |

## Por qué la velocidad de este mod es más estable que la nuestra

Nuestro generador (`tools/make_enemy_opts.py`, versión anterior) sólo escalaba
`BSA/MovementParam` y la tabla `GameBalance/AttackInterval`, y además escalaba los
**timeouts de acción** del BSA (`AttackStartTimeoutFrames`, `BackWalkTime`,
`TimeoutTime`, ...). Eso deja desincronizados:

1. `JogSpeed` no se escalaba (el enemigo cambia entre jog y run con proporciones distintas).
2. Las velocidades de las **acometidas** (`ChargeAttackMoveSpeed`, `AttackTransSpeed`,
   `SurpriseAttackMoveSpeed`, `AttackFlySpeed`) y las velocidades por enemigo
   (`AttackMoveSpeed`, `Attack1stSpeed`, etc.) quedaban en vanilla mientras el resto
   iba x2/x3: el enemigo se pasa de largo o "patina" al atacar.
3. Acortar los timeouts de acción cambia la máquina de estados de la IA, no sólo el ritmo.

Harder Combat escala **todas** las velocidades juntas y **no** toca los timeouts de acción:
la cadencia la cambia con las tablas de intervalo. Nuestro `enemy_attack` sí sigue tocando los
timeouts de acción, como antes (por pedido); eso puede hacer la IA menos predecible que Harder
Combat, pero es lo que se quiere para esta opción.

## Qué se adoptó en Super Hero Boost

- `enemy_move` ahora escala:

  - todas las velocidades de `BSA/MovementParam` (incluido `JogSpeed`),
  - las velocidades de acción de `Game/BSA/ActionSeqContainer`,
  - las velocidades de ataque por enemigo de `GameParameter/*Param` y `Game/*Param`.

- `enemy_attack` escala las tablas/campos de intervalo de ataque **y también** los timeouts de
  acción (`AttackStartTimeoutFrames`, `BackWalkTime`, `TimeoutTime`, ...), como antes.

- **Nuevo `enemy_proj`**: velocidad de los proyectiles enemigos, independiente del movimiento.

- `enemy_anim` se mantiene como antes (ASB), separado; Harder Combat no cambia animaciones.

Los perfiles beta (`beta-enemies`, `beta-all`) activan los cuatro componentes en x2; el resto
de perfiles los dejan en off, como antes.

## Qué NO se adoptó (por ahora)

Daño x5, vida x2, percepción/vista, contadores del cerebro y probabilidades de defensa.
La app ya tiene **enemy health** (`enemy_hp`) y **damage taken** (`damage`) como opciones
separadas; si se quieren los valores exactos de Harder Combat se pueden agregar como opciones
nuevas, pero no son parte de la "velocidad" y cambiarían el balance por defecto.

## Regenerar el payload

```
set SHB_ROMFS=F:\Switch2\Longshot\rc\romfs
python tools\make_enemy_opts.py
```

El manifiesto pasa a `version: 2`; los campos tienen `k`:

- `m` = movimiento (base + acciones + por enemigo),
- `a` = cadencia de ataque (intervalos),
- `p` = proyectiles.

El instalador aplica el multiplicador elegido a cada grupo por separado en el momento de
instalar, así que el payload no crece: sigue habiendo un solo `enemy_speed_base` y un
manifiesto de offsets.
