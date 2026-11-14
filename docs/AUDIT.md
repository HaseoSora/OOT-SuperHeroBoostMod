# Auditoría de código y materiales de terceros

Revisión hecha sobre los archivos versionados del proyecto. Objetivo: que el módulo, el HUD, la estamina, la app y el
instalador sean trabajo propio, y que no se redistribuya material del juego ni se usen marcas de terceros en el
producto.

## Resumen

| Elemento | Origen | ¿Se distribuye? | Estado |
|---|---|---|---|
| `core/`, `features/stamina/`, `features/classic_slots/`, `features/probe/` | Propio | Sí (módulo compilado) | OK |
| `app/` (ventana, perfiles, instalador, textos) | Propio | Sí | OK |
| `tools/` (compilación, pruebas, análisis) | Propio, salvo dependencias indicadas | No | OK |
| Classic Item Slots v1.4.3 | sonofsilvanus (terceros) | No: la app lo descarga de su release oficial | Se conserva el crédito; no se empaqueta con el proyecto |
| Algoritmo CityHash64 | Algoritmo público de Google | Solo el código que lo implementa | Implementación propia; sin código de Google copiado |
| Código y materiales del juego | Juego original | No | Solo se leen del volcado del usuario en tiempo de ejecución |
| Herramientas de desarrollo (LLVM, PyInstaller, lz4, zbic, devtool, emulador) | Terceros | No | Dependencias de desarrollo, no forman parte del producto |

## Código propio

- `core/`: cabecera MOD0, ganchos, reparto, HID, configuración, seguimiento de jugador/enemigos y HUD.
- `features/stamina/`: máquina de estados de estamina y ganchos de entrada/velocidad. Los valores de
  `stamina_default_config()` son ajustes propios, no una copia de otro mod.
- `features/songbook/`: reproducción desde el songbook nativo. Implementación propia basada en los campos del
  contexto de ocarina y en inyectar los cinco botones de nota; no usa código de terceros.
- `app/`: ventana Tkinter, perfiles completos, instalador, rutas multiplataforma y textos en seis idiomas.
- `tools/`: scripts de compilación, pruebas en vivo, volcados y análisis. Algunos leen el juego o usan el servidor de
  depuración, pero no se empaquetan con la app.

No se ha encontrado código fuente de otro mod copiado dentro de `core/`, `features/` ni `app/`.

## Classic Item Slots

No se empaqueta con el producto. La app lo descarga de su release oficial de GitHub en el momento de instalar la
variante elegida (tres variantes de botones) y lo instala tal cual. El crédito a sonofsilvanus se mantiene en la app,
el README y la documentación. No se presenta como trabajo propio.

## CityHash64

El motor del juego guarda un hash de 64 bits junto a cada nombre de panel. `tools/lib/cityhash.py` implementa el
algoritmo público CityHash64 para calcular esos hashes; no contiene código de Google, solo la implementación propia de
las constantes y operaciones publicadas. Se usa en tiempo de compilación para generar `hud_names.h`.

## Material del juego

- `build/`, `data/`, `release/` y `app/payload/` están ignorados por git.
- `tools/check_no_game_data.py` recorre el índice de git y falla si encuentra extensiones de dump (`.byml`,
  `.bgyml`, `.bntx`, `.sarc`, `.nso`, `.nro`, `.ips`, etc.), carpetas `romfs/`/`exefs/`/`app/payload/` o archivos con
  magia de formatos del juego. Se puede ejecutar antes de cada commit.
- El repositorio no contiene texturas, layouts, BYML, romfs, `main` ni ningún archivo extraído del juego.
- `tools/make_romfs_opts.py` genera el romfs opcional a partir del volcado del usuario; la app copia ese resultado
  solo si el usuario marca la opción.
- `tools/make_enemy_opts.py` genera los dos mods beta de enemigos (duplicado y velocidad) desde el volcado; tampoco
  se versionan ni se redistribuyen.
- El módulo usa nombres de recursos internos del juego (por ejemplo `Circle64_00`, `NumBaseSide_00`,
  `Nt_RupeeIconNew_00`) para dibujar el HUD con el aspecto nativo. Son referencias a archivos que ya están en el
  juego del usuario, no material redistribuido.
- Los nombres de paneles propios se renombraron de `*_Oot*` a `*_Shb*` para no usar la abreviatura del juego.

## Textos y marcas

Se revisaron los archivos versionados y los textos de la app:

- No quedan referencias textuales a la franquicia, a la consola ni a la región del juego en el producto. El emblema de tres
  triángulos de la cabecera se dibuja por código (tres polígonos) y no usa ningún asset ni logotipo oficial.
- El nombre del protagonista se sustituyó por "el jugador"/"the player" en comentarios y documentación; los identificadores internos
  pasaron de `g_link_*` a `g_player_*`.
- "Hero Mode" se mantiene como nombre genérico de dificultad (es el término que usa el propio producto).
- La abreviatura `OoT` se eliminó del código y de los nombres de paneles. La URL de descarga de Classic conserva su
  nombre original porque es la URL real del release de terceros y solo se usa para descargar el mod al instalar.

## Dependencias de desarrollo

No se distribuyen, pero conviene tenerlas documentadas:

- LLVM/clang/lld (llvm-mingw) para compilar el módulo.
- PyInstaller para empaquetar la app.
- `lz4` y `zbic` para descomprimir el `main` original durante la verificación.
- El cliente del servidor de depuración y los lectores de BYML/GameData usados por los scripts de pruebas.

## Pendiente de decisión

El proyecto no tiene un archivo `LICENSE`. Si se va a publicar, conviene elegir una licencia para el código propio
(por ejemplo MIT) y mantener el crédito y la licencia de Classic Item Slots por separado. Esta auditoría no decide la
licencia; solo deja constancia de qué es propio y qué es de terceros.
