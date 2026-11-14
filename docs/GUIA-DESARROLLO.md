# OoT Master Mod: guía de desarrollo

Cómo está hecho el mod, cómo se compila, se instala y se prueba, y cómo modificar cada parte. Juego: *The Legend of
Zelda: Ocarina of Time* (Switch 2), actualización v131072, `main` Build ID `E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348`.
Emulador de pruebas: Fritchii v4.1 (base Lichii), con carpeta de mods en
`E:\Switch2\Emu\lichii-windows-x86_64\user\load\0400486024DEC000` (la usa por `load_directory` en su `qt-config.ini`).

Documentos relacionados:
- [RE-NOTES.md](RE-NOTES.md): hallazgos de ingeniería inversa (direcciones, formatos, qué funcionó y qué no).
- [APP.md](APP.md): la app de configuración.
- [CLASSIC-HOOKS.md](CLASSIC-HOOKS.md): mapa de ganchos de Classic Item Slots.
- [CLASSIC-REPLICA.md](CLASSIC-REPLICA.md): análisis y plan de nuestra réplica de Classic.

---

## 1. Visión general

El mod son dos piezas que el emulador carga junto al juego:

| Pieza | Qué es | Dónde se genera |
|---|---|---|
| `exefs/subsdk9` | Nuestro módulo de código (NSO, ARM64, sin relocaciones) | `tools/build_core.py` |
| `exefs/<BuildID>.ips` | Parche IPS32 sobre `main`: cada punto de gancho salta a nuestro módulo | `tools/build_core.py` |
| `romfs/...` (opcional) | Datos del juego modificados (p. ej. "sin drop de corazones") | `tools/make_romfs_opts.py` |

La **app** (`release/OotMasterConfig.exe`) no compila nada: lleva el módulo ya compilado, escribe las opciones del
usuario en un bloque de configuración dentro de `subsdk9` y copia todo a la carpeta de mods (`00-OOT-Master`).

Flujo de una modificación:

```
editar core/ o features/  ->  build_core.py (prueba)  ->  probar en el emulador  ->  make_release.py  ->  build_app.py
```

## 2. Estructura del repositorio

```
core/                código común del módulo
  module.S           cabecera MOD0 y sección dinámica mínima
  link.ld            enlace: base del módulo y direcciones de funciones del juego (main-relative)
  hooks.S            envoltorios de ganchos (entrada de mando, ranuras, ganchos de código)
  dispatch.c/.h      reparto de eventos de entrada a las features (tabla generada, sin punteros)
  hid.c/.h           lectura/escritura de botones y sticks en las muestras HID
  config.c/.h        bloque de configuración OOTMCFG1 (lo parchea la app)
  player.c           seguimiento de Link y enemigos: estado de acción, vida, combate, escala de vida, escudo
  hud.c              todo el HUD propio: anillo de estamina, reloj, contador de rupias
  mem.c, slots.c ... utilidades
features/
  hero_core/         estamina (costes, agotamiento, recarga), multiplicador de sprint
  classic_slots/     réplica antigua de ranuras extra (no se publica; ver CLASSIC-REPLICA.md)
  probe/             feature de diagnóstico
tools/               compilación, publicación, pruebas en vivo y análisis (ver sección 9)
app/                 app de configuración (Tkinter) + payload precompilado
docs/                esta guía y las notas
build/               salidas y capturas (ignorado por git)
release/             OotMasterConfig.exe (ignorado por git)
```

Rutas externas que usan las herramientas (en este PC):
- Toolchain LLVM: `F:\project\oot\tools\llvm-mingw\llvm-mingw-20261104-ucrt-x86_64\bin`
- `main` original (solo lectura, para verificar ganchos y desensamblar): `F:\project\oot\data\stock-exefs\main`
- Volcado del romfs: `F:\switch2\hookshott\romfs`
- Devtool de platinumagpie (cliente del servidor de depuración): `F:\project\oot\vendor\devtool\oot-remake-devtool-main`
- Diccionario zstd del archivo de UI: `F:\project\oot\data\zsdic1.bin`

## 3. Cómo funciona el módulo

### 3.1 Restricciones
- **Sin relocaciones**: ninguna tabla en datos puede guardar direcciones (valdrían la dirección de enlace, no la real).
  Los nombres se guardan como `char[]` y se devuelven desde código; las listas de manejadores se generan como
  llamadas directas (`build/native/dispatch_gen.c`). Compilado con `-fno-jump-tables` porque clang convertía
  `switch` en tablas de punteros absolutos.
- Las funciones y datos del juego se referencian como símbolos en `core/link.ld` (offsets dentro de `main`). Con la
  base del módulo (`__base`) el enlazador produce saltos PC-relativos correctos.
- Base del módulo: `0x4F87000` (variante "classic", tras el `subsdk8` de Classic) o `0x4F80000` ("standalone").
  `make_release.py` compila las dos.

### 3.2 Tipos de gancho (todos en `core/hooks.S`, sitios en `tools/hook_sites.py`)
| Tipo | Cómo se parchea | Uso |
|---|---|---|
| `INPUT_HOOK` | el `bl` del juego a un lector de mando pasa a ser `bl` a nuestro envoltorio, que llama al lector original y luego a `mod_on_input` | build no-compat |
| `hook_stub3` (compat) | la primera instrucción del stub PLT del lector de mando pasa a `b` a nuestro envoltorio | build `--compat` (convive con Classic, que es dueño de los 5 `bl`) |
| `WRAP_HOOK` (ranuras) | `bl 0x1211C00` (equipar objeto) → nuestro envoltorio con pre-gancho que puede cambiar el objeto | réplica de Classic |
| `CODE_HOOK` | la instrucción `pacibsp` de la entrada de una función pasa a `b` a nuestro envoltorio; este guarda registros, llama `mod_on_code(id, x0, x1, x2, regs)`, los restaura (los cambios en `regs` se aplican), ejecuta `pacibsp` y vuelve a `sitio+4` | la mayoría de ganchos |

Ganchos de código actuales (`CODE_SITES`):

| id | sitio (main) | qué es | quién lo usa |
|---|---|---|---|
| 0 | 0x2B30DE0 | actualización por fotograma del planificador | `hud_frame()` (todo el HUD) |
| 1 | 0x33BDCE0 | init del controlador de la barra de magia | ancla del HUD (`g_mp`) |
| 2 | 0x43A6F8 | construcción de un recurso de UI | `hud_prepare()`: inyecta paneles en PlayerStatus_00 |
| 3 | 0x2D2D90 | `set_frame(anim, frame)` | observación de animaciones (diagnóstico) |
| 4 | 0x152F8F0 | creación de instancias de partes de layout | diagnóstico |
| 5 | 0x2C215E0 | actualización de movimiento de actores físicos (x0 = actor) | `player_track()`: Link y enemigos |
| 6-9 | 0x27F7D00, 0x27F7F90, 0x27FB0C0, 0x27FA200 | nodos de reacción de escudo de Link | coste de estamina al bloquear |
| 10 | 0x9352F0 | movimiento en suelo (x0 jugador, x1 dirección, s0 velocidad) | multiplicador de sprint |

En el callback, `regs` apunta a los registros guardados: `x0` en `+0x10`, `x30` (dirección de retorno) en `+0x08`,
`d0` en `+0xB0`. Ejemplo: el sprint comprueba `x30 == main+0x934994` (solo la llamada de Link) y multiplica `s0`.

**Añadir un gancho de código nuevo:**
1. Comprobar con `python tools/disasm.py <dir> 0x10` que la función empieza con `pacibsp` (0xD503237F).
2. `tools/hook_sites.py`: añadir `(sitio, "hook_x", id)` a `CODE_SITES`.
3. `core/link.ld`: `RES_X = sitio + 4;`
4. `core/hooks.S`: `CODE_HOOK hook_x, id, RES_X`
5. `core/hud.c`, `hud_on_code()`: manejar `id`. Si la lógica está en una feature, declararla `__attribute__((weak))`.
6. `build_core.py` verifica que el sitio tiene la instrucción esperada antes de generar el IPS.

### 3.3 Configuración en tiempo de ejecución (`core/config.h`)
Bloque `OotConfig` con magia `OOTMCFG1` en `.data`. La app busca la magia en `subsdk9` y escribe los campos; el mod
los lee en cada fotograma (`g_ootcfg`). **Solo se añaden campos al final** (usar `reserved`), sin reordenar.

| offset | campo | app (`installer.patch_config`) |
|---|---|---|
| 16 | `stamina_enabled` | casilla Estamina |
| 17 | `preset` (0 hardcore, 1 solo combate, 2 solo sprint, 3 avanzado) | Preset |
| 18-23 | `cost_jump/attack/sprint/block/shoot/roll` | Qué gasta estamina |
| 24 | `combat_only` | Solo en combate |
| 25 | `classic_slots` (informativo) | Classic |
| 26 | `enemy_hp_pct` (u16) | Vida de los enemigos |
| 28 | `damage_taken_pct` (u16) | Daño que recibes |
| 30-32 | `hud_rupees`, `hud_clock`, `clock_24h` | HUD siempre visible |
| 33 | `no_heart_drop` (informativo; lo hace el romfs) | Sin drop de corazones |
| 34 | `sprint_speed_pct` (u16, defecto 125) | Velocidad del sprint |

**Añadir una opción nueva:** campo en `config.h` (quitando bytes de `reserved`), valor por defecto en `config.c`,
escritura en `installer.patch_config` (`f = magia + 16`), campo en `installer.Settings`, flag en `ootconfig.cli`,
control en `ootconfig.gui` (variable, guardado en `cfg`, `Settings(...)`) y textos en `app/i18n.py` para los 6
idiomas (`en es pt fr de it`).

## 4. Features

### 4.1 Estamina (`features/hero_core/hero_core.c`, `stamina.c`)
- Corre dentro de la lectura de mando de juego (sitio 3). Los costes salen de las **acciones** de Link
  (`player_track` lee su estado en `player+0x244`: `Rolling`, `Jump`, `Cut...`, `Guard...`), no de los botones.
- Capacidad: 75 + 75/17 por corazón a partir del 4.º (hasta 150).
- Sprint = A mantenido en estado `Move` durante 12 fotogramas: gasta 7/s.
- Agotado (amarillo): se bloquean las acciones según el preset (se quitan botones de la entrada) y se camina.
- Recarga tras 0,8 s sin acciones (1,8 s en combate, 2,5 s tras agotarse), a 24/s (48/s tras agotarse).
- Bloqueo con escudo: los ganchos 6-9 y los estados `Guard*Hit/Break/Reaction/Repel` (no `GuardFailHit`) suben un
  contador (`player_guard_seq`) que sobrevive a pausas cortas (el golpe llega durante la reacción de Link, cuando su
  actualización se detiene unos fotogramas).
- Combate: un enemigo vivo a menos de 10 m que se acerca o está encima (5 s de margen).
- Constantes: `#define` al principio de `hero_core.c` y `stamina_default_config()`.

### 4.2 Multiplicador de sprint (gancho 10, `hero_speed_hook`)
Multiplica la velocidad del movimiento en suelo de Link mientras A está pulsado y no lo ha quitado la estamina.
Rodar, nadar y trepar no pasan por esa llamada. Referencia: mod MIT "Movement Speed Increase" (Zerossa), que parchea
la misma llamada.

### 4.3 Vida de enemigos y daño recibido (`core/player.c`)
- Enemigo = actor cuyo recurso de vida se llama `Enemy_*`. Al verlo por primera vez se escalan su vida máxima y
  actual (`life+0x1C10` actual, `+0x1C18` máxima, valor s32 en `+8`). Diagnóstico: `g_hp_log`.
- Daño recibido: cuando baja la vida de Link se resta el extra (nunca mata solo el extra).
- Valores de vida de cada enemigo: `Pack/Actor/<Enemigo>.pack.zs` → `Life/LifeParameters/*.bgyml` (`MaxLife`).

### 4.4 Sin drop de corazones (romfs)
`tools/make_romfs_opts.py` genera, a partir del volcado del propio juego, `GameParameter/DropGlobalParam/...` con
`DropGlobalParam.HpActor` (el actor que cae como "corazón") apuntando a la rupia verde. La app copia ese romfs si la opción está marcada.

## 5. HUD propio (`core/hud.c`)

### 5.1 Cómo se añaden paneles al HUD del juego
1. El gancho 2 (`hud_prepare`) intercepta la construcción del layout `PlayerStatus_00` y entrega al motor una
   **copia privada de sus metadatos** (`build_root`) con paneles extra: imágenes `P_OotPic_000..` y textos
   `T_OotTxt_00..05`. Cada nombre lleva su CityHash64 (generado por `build_core.py` en `hud_names.h`).
2. Cada panel se describe en varias tablas del layout (lista común `+0x20`, imagen/texto `+0x40`, imágenes `+0x60`,
   textos `+0x80`). Detalles del formato en RE-NOTES ("Layout file format", "Rupee counter / clock HUD").
   **Importante:** en el descriptor común de una imagen, `+0x40 = 0xFFFF` y `+0x42 = índice en la lista de imágenes`.
   Al revés, el motor busca en listas basura en cada consulta (cientos de miles de lecturas inválidas y la carga
   en negro ~2 minutos).
3. **Texturas:** cada textura usa una copia de un material con textura (el de `P_SubItemBg_00`) cuyo sampler apunta
   al nombre de otra textura del archivo `Common` (`add_material`). Texturas usadas: `NumBaseSide_00/01` (placa),
   `Nt_RupeeIconNew_00` (rupia), `Circle64_00` (círculos), `White8_00_BC4L` (rayos).
4. Cada fotograma, `hud_frame()` coloca los paneles escribiendo su registro (`+0x60/+0x64` escala, `+0x68` rotación,
   `+0x6C/+0x70` posición, marcar `|= 0x6F`) y su color (objeto del panel `+0x20`, RGBA float).
5. Texto: `set_text` del juego (`main+0x439520`). Cada campo tiene dos paneles y se escribe en el oculto para
   evitar parpadeo.
6. Fuera del juego (menús, cargas) todo se oculta una vez y no se toca; al reconstruirse el layout se vacían las
   cachés (`plates_reset`).

### 5.2 Reloj y rupias
- Placa nativa del contador de rupias, dibujada dos veces (en espejo) para tener chevrones en ambos lados.
- Hora: `World_CurrentDateTime` (GameData) o el reloj del mundo; sol de 6:00 a 18:00, luna (media luna) el resto.
- Rupias: GameData Int `PlayerStatus.CurrentRupee` (registro 962) y capacidad de la cartera (976).
- Aspecto ajustable: `g_hudp[]` (índices documentados en `hud.c`).

### 5.3 Anillo de estamina
Unos 230 paneles `Circle64_00` solapados (48 en el anillo interior, 64 en el exterior) que forman un tubo
continuo, con una pista negra detrás; el último punto va en el ángulo exacto del relleno. Sigue a Link proyectando su
posición con la matriz de la cámara (`anchor_update`). Aspecto: `g_ringp[]`.

### 5.4 Ajustar el aspecto en vivo
Con el juego abierto mediante `live_check.py --keep` (o `run`), sin recompilar:
```
python tools/hud_tune.py get
python tools/hud_tune.py set 0=-1518 3=0.46 --shot build/tune.png --crop 0,600,400,720
python tools/hud_tune.py set 6=0.0 --sym g_ringp
python tools/hud_tune.py cfg rupees=1 clock=1 clock24=0
```
Cuando el aspecto convence, se copian los valores a los inicializadores de `g_hudp` / `g_ringp`.

## 6. Compilar, publicar y la app

```
python tools/build_core.py --features hero_core --compat --base 0x4F87000   # módulo de prueba en build/native
python tools/make_release.py     # compila las 2 variantes en app/payload + romfs opcional + Classic empaquetado
python tools/build_app.py        # release/OotMasterConfig.exe (PyInstaller). Cerrar el .exe antes.
```

La app (`app/ootconfig.py` interfaz, `app/installer.py` lógica, `app/i18n.py` textos):
1. encuentra la carpeta de mods del emulador (respeta `load_directory`);
2. copia la variante adecuada y parchea el bloque de configuración;
3. con Classic Item Slots: copia su módulo como `subsdk8` y su romfs, y fusiona los dos IPS comprobando que no
   se solapan;
4. avisa de otros mods con exefs que pueden chocar.

También tiene modo línea de comandos (el mismo código de instalación):
```
python app/ootconfig.py --cli --emu "E:/Switch2/Emu/Fritchii-v4.1-Windows-x64/Fritchii-v4.1" --preset 0 --rupees --clock --sprint-speed 125
```

## 7. Probar en el emulador

`tools/live_check.py` arranca Fritchii con el servidor de depuración (`EDEN_NX2_DEBUG_SERVER=127.0.0.1:6545`), espera
la pantalla de título, pulsa A 4 veces, espera a que cargue la partida (≈30 s), saca capturas en `build/` e imprime
los diagnósticos del módulo (símbolos leídos de `build/native/module.elf`).

```
python tools/live_check.py --load-a 4 --keep --linger 3     # deja el juego abierto
```

Puntos clave:
- Instalar primero (app o `--cli`) y **después** volver a ejecutar `build_core.py` con la misma variante, para que
  `module.elf` (los símbolos) coincida con lo instalado.
- El servidor de depuración atiende en serie: mientras se ejecuta una entrada (`input_sequence`), las lecturas
  esperan. Para medir durante una entrada, leer la memoria del proceso con `HostMemory` del devtool (como hacen
  `hud_tune.py` y los scripts de velocidad).
- Escribir memoria en vivo: `HostMemory(pid).calibrate(cliente, [base_main])` y luego `write(dir, bytes)`.
- El log del emulador (`user/log/eden_log.txt`) debe quedar limpio: muchas líneas `Unmapped Read/Write` indican
  un fallo de descriptores o punteros y ralentizan muchísimo el juego.
- Mods de terceros que chocan (Always-On Rupee Counter, HUD of Time, Hero Core, Classic suelto...) deben estar
  desactivados en el emulador.

## 8. Investigar el juego (receta)

| Necesito | Cómo |
|---|---|
| Ver código de una dirección | `python tools/disasm.py 0x9352f0 0x40` |
| Quién llama a una función | buscar `bl` a esa dirección en el texto de `main` (ver scripts en RE-NOTES) |
| Parámetros de un actor | `Pack/Actor/<Actor>.pack.zs` (zstd con `pack.zsdic` de `Pack/ZsDic.pack.zs`, SARC, BYML) |
| Tablas RSDB (objetos, armas) | `RSDB/*.rstbl.byml.zs` (zstd con `zs.zsdic`) |
| Layouts de UI | `UI/Layout2Archive/Common...blarc.zs` (SARC de `.buil`, formato BFFH en RE-NOTES) |
| Texturas de UI | `Common...bntx.zs`: `tools/bntx_probe.py` lista, `tools/bntx_decode.py` decodifica BC4 (altura de bloque 4 para 128x128) |
| Un valor en memoria | `DebugClient.search(...)` + leer vecinos; bisección escribiendo valores con `HostMemory` |
| Estado de Link | `player+0x244` (nombre de acción), `actor+0x31C` posición (solo lectura efectiva), `actor+0x388` velocidad (salida) |

Los nombres de funciones no están en `main` en texto claro (el motor usa hashes); las pistas salen de los datos
(AINB, BYML) y de las direcciones que ya usan otros mods.

## 9. Herramientas (`tools/`)

| Herramienta | Para qué |
|---|---|
| `build_core.py` | compila el módulo y su IPS; genera `hud_names.h` y `dispatch_gen.c` |
| `make_release.py` / `build_app.py` | payload de la app / ejecutable |
| `make_romfs_opts.py` | romfs opcionales (sin drop de corazones) |
| `hook_sites.py` | lista de sitios de gancho |
| `live_check.py` | arrancar, cargar partida, capturar y leer diagnósticos |
| `hud_tune.py` | ajustar HUD y opciones en vivo, capturas |
| `disasm.py` | desensamblar `main` |
| `bntx_probe.py`, `bntx_decode.py` | texturas de UI |
| `pane_dump.py`, `gauge_dump.py`, `text_probe.py`, `clock_probe.py` | volcados del HUD en vivo |
| `enemy_probe.py`, `find_player.py`, `player_strings.py`, `action_names.py` | actores y estados de Link |
| `e2e_matrix.py` | prueba completa: instala cada configuración con el `.exe` (sin ventana), arranca, hace acciones y comprueba que la estamina se comporta como promete esa configuración (`build/e2e/results.txt`) |
| `compat_pack.py`, `make_restbl.py` | paquete de prueba Classic + nuestro módulo; tabla de tamaños de recursos (presupuesto de memoria de la UI) |
| `lib/` | `nso.py` (NSO/IPS), `sarc.py`, `cityhash.py`, `winmove.py` |

## 10. Licencias y referencias
- Classic Item Slots (sonofsilvanus): se descarga de su release oficial y se instala tal cual.
- "Movement Speed Increase" (Zerossa, MIT): referencia para la llamada de movimiento del sprint.
- OoT Remake DevTool (platinumagpie): servidor de depuración, `HostMemory`, lectores de BYML/GameData.
