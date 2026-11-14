# Mapeo de botones (buttonMapping): diseño y notas

Módulo propio de Super Hero Boost. Añade botones de objeto **B, L, R y ZR** al HUD y permite asignarles objetos
desde el menú de pausa. No usa ningún mod de terceros: el módulo, el arte de los botones y las texturas se generan
en este proyecto.

## Funciones

| Función | Cómo funciona |
|---|---|
| Botones de objeto extra B / L / R / ZR | se equipa el objeto de la ranura en la caja de objeto del juego (índice forzado en la llamada `main+0x1211C00`) y se mantiene ZR mientras se mantiene el botón |
| Estilos de botón | tres juegos de texturas: Switch (`OotBtnS_*`), Xbox (`OotBtnX_*`) y PlayStation (`OotBtnP_*`); byte de estilo 0 / 1 / 2 |
| Diseño extendido | botones B, L, R, ZR, X, Y, A y espada |
| Diseño simple | solo los botones asignables B, L, R y ZR; oculta X, Y, A y la espada, y reubica L / R / ZR en su sitio con B centrado y más cerca, en zigzag, tanto en el HUD como en la pestaña Objetos del menú |
| Modo de L: objeto | L es una ranura de objeto más |
| Modo de L: escudo | L hace de ZL (escudo) sin bloquear cámara; en diseño extendido muestra el escudo equipado y no se puede asignar; en simple se oculta |
| Modo de L: selector | L abre el selector de objetos del juego; misma lógica de diseño, sin icono de escudo |
| Asignación en pausa | pestaña Objetos: B / L / R sobre el objeto resaltado; un objeto que ya está en otra ranura se intercambia |
| Iconos | partes `PaItemBtn_00` con el icono del objeto y su sombra, igual que la caja de objeto nativa |

El módulo se activa con el byte `button_mapping` de la configuración (`core/config.h`): estilo en `+22`, diseño simple
en `+23` y modo de L en `+24`.

## Partes del HUD

- Cuatro clones de la caja de objeto nativa (`Pa_SelectItem_00`, asset `PaItemBtn_00`) se añaden a
  `PlayerStatus_00` con el descriptor común corregido (`+0x40 = 0xFFFF`, `+0x42` = índice de parte). Se crean, los
  encuentra `find_part`, tienen las 11 animaciones (ItemPattern, StockNum, NumMax, NumMin, IsInvalid, Type,
  ItemChange, Select, UnSelect, Decide, Assign) y dibujan. `PART_N = 4`, `slots_update()` en `core/hud.c`.
- Los iconos son texturas cargadas por nombre en tiempo de ejecución. `PaItemBtn_00` contiene la parte
  `Pa_ReplaceIcon_00`, cuyos dos paneles (icono + sombra) usan la textura de relleno `FBLayout_00_ASTC4x4`. El HUD la
  sustituye por `UI/Tex/Icon/<Item_Name>.bntx.zs` y `UI/Tex/IconSh/<name>_Sh`.
- **Cómo pone el juego un icono** (HUD nativo en `main+0x33B7E80`):
  1. reserva un controlador de icono de 0x40 bytes, fija su vtable (`[main+0x4C973B0] + 0x10`) y sus campos, lo enlaza
     en la lista de la parte y pone a cero `+0x30` / `+0x38`;
  2. `main+0xA37320(controller, part)` crea los reemplazadores de textura del icono y de la sombra en
     `controller+0x30` / `+0x38` (0x58 bytes cada uno, del heap del motor);
  3. `main+0xA73920(controller->+0x30, &"Item_X", 0)` y `main+0xA73920(controller->+0x38, &"Item_X_Sh", 0)`.
- Llamar a `main+0xA73920` sobre el objeto de `nested ReplaceIcon frame + 0x6A8` desbordaba la pila (juego
  congelado): ese objeto no es un reemplazador listo. La llamada directa queda tras `SLOT_ICON_DIRECT 0`.
- **Solución (commit f5ad284 y posteriores):** los controladores los construye la rutina del juego
  `main+0x33B7DA0(widget, heap)` (la del icono de la Agony Stone: busca `Pa_ReplaceIcon_00` en `widget+0x20`, crea el
  controlador y pone `Item_AgonyStone`). Se llama con un widget de relleno por botón **durante la inicialización del
  HUD PlayerStatus** (hook 12 en `main+0x33F5D20`, x0 HUD, x1 heap): ese heap solo acepta reservas durante la
  inicialización (más tarde devolvía un controlador nulo y el juego caía). El hook 11 en `main+0xA37320` captura el
  controlador creado. Después los iconos se cambian en cualquier momento con `main+0xA73920` sobre `controller+0x30`
  (nombre) y `+0x38` (`nombre_Sh`).

## Índice de objeto -> icono

- `main+0x592B20(manager, &name, item)` devuelve el nombre de actor del objeto, que también es el nombre de su textura
  de icono. `manager = **(main+0x4C7E0D0)`, nombre por defecto `*(main+0x4C7DAD0)` (el HUD hace lo mismo antes de
  poner su icono).
- Índice de objeto = índice de la llamada de equipar `main+0x1211C00`. Leído en vivo:
  0 Item_DekuStick, 1 Item_DekuNut, 2 Item_Bomb, 3 Item_Boomerang, 4 Weapon_Range_SlingShot, 5 Item_Hookshot,
  6 Item_Longshot, 7 Item_Hammer, 9 Item_Bombchu, 10 Item_DinFire, 11 Item_FaroreWind, 12 Item_NayruLove,
  13 Item_MagicBean, 14 Item_Bottle_<content>, 18 Item_FishingRod, 30 Weapon_Range_Bow, 31 Item_WeirdEgg ..
  44 Item_ClaimCheck (objetos de intercambio), 46 Item_Arrow_Fire, 47 Item_Arrow_Ice, 48 Item_Arrow_Light
  (8, 15-17, 19-29, 45: vacíos en esta partida).
- `ItemPattern` es el **encuadre** del icono dentro del botón (el frame 0 lo dibuja más grande), no la elección del
  objeto; la tabla medida objeto -> frame se aplica por objeto (`item_pattern()` en `core/hud.c`). `ItemChange` es la
  animación de aparición del icono (frame 0 = oculto). `Type` no cambia nada visible.

## Texturas

`tools/make_buttons.py` dibuja los tres juegos de botones con formas y texto, sin material del juego. Cada estilo
produce sus propias texturas `OotBtn*_*` y el instalador copia solo el juego del estilo elegido.

## Pendiente

- Puerto del botón L como escudo: hoy L se traduce a ZL y un hook en la entrada de `ExecutePlayerCameraLockOn`
  (`main+0x27E3A60`) evita que la cámara fije objetivo. Falta verificarlo en partida.
