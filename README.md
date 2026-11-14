# Super Hero Boost

Módulo de gameplay para el remake de consola (actualización **v131072**) y su aplicación de configuración
multiplataforma **SuperHeroBoostConfig**.

El mod añade estamina, escalado de dificultad, un HUD ampliado y botones de objeto extra, todo configurable sin
recompilar nada. La app parchea el módulo precompilado y copia los archivos que necesita el juego. El módulo, el HUD,
las texturas y la app son trabajo original: no se incluye ni se descarga ningún mod de terceros.

## Características

### Jugabilidad

- **Perfiles completos**: Recomendado (todo activado), Base, Modo héroe, Héroe + estamina, Héroe explorador,
  Superhéroe, Ultra héroe y Supervivencia. Ajustan de una vez dificultad, estamina y sprint; cualquier cambio manual
  pasa a **Personalizado**.
- **Estamina** con cuatro estilos: hardcore (todo cuesta), solo combate, solo sprint y avanzado (elige qué acciones
  cuestan). Incluye agotamiento y recarga, y coste al rodar, saltar, atacar, disparar, esprintar y bloquear.
- **Anillo de estamina** junto al jugador, dibujado con texturas del juego.
- **Velocidad del sprint** configurable (por defecto +25 %).
- **Vida de los enemigos** y **daño recibido** multiplicables (×1 a ×3).
- **Sin drop de corazones**: los corazones que sueltan los enemigos pasan a ser rupias verdes.
- **Reloj y contador de rupias siempre visibles**, con el aspecto nativo del juego y formato de 12 / 24 h.
- **Autoreproducción del songbook**: al elegir una canción aprendida en el songbook nativo (ZL), el héroe la toca y
  activa su efecto. Solo con canciones aprendidas; no con la canción del espantapájaros.
- **Mapeo de botones propio** (`buttonMapping`):
  - Botones de objeto **B, L, R y ZR** en el HUD, asignables desde la pestaña **Objetos** del menú de pausa.
  - Estilos de botón **Switch / PlayStation / Xbox**.
  - Diseño **extendido** (B, L, R, ZR, X, Y, A y espada) o **simple** (solo los botones asignables, con B centrado y
    L / R / ZR recolocados para que no queden huecos).
  - Modos del botón **L**: objeto, escudo o selector de objetos del juego.

### App de configuración

- Interfaz para Windows, macOS y Linux (Python 3.10+ con Tkinter).
- Perfiles, ajustes por sección, instalación y desinstalación en la carpeta de mods del emulador.
- Traducciones en español, inglés, portugués, francés, alemán e italiano.
- Modo línea de comandos para instalar la misma configuración sin abrir la ventana.

### Beta

Estas opciones son **experimentales**. Se generan a partir del volcado del juego y se instalan como romfs extra; pueden
romper puzles, misiones o el rendimiento. Haz una copia de tu partida y prueba una cada vez.

- **Duplicado de enemigos (Opción A)**: clona enemigos genéricos del mapa y duplica los apariciones automáticas del
  campo. Jefes, minijefes y enemigos de script quedan fuera.
- **Velocidad de enemigos ×2**: acelera movimiento, animación y cadencia de ataque. Algunos enemigos o ataques pueden
  no cambiar o desincronizarse.

El resto de ideas en desarrollo se mantienen fuera de esta rama y no forman parte de esta versión.

## Uso

1. **Requisitos**: el juego en la actualización **v131072** y un emulador que cargue mods desde su carpeta
   `user/load/0400486024DEC000` (o la que tengas configurada). Guarda una copia de tu partida antes de instalar.
2. Abre **SuperHeroBoostConfig** (o ejecuta `python app/main.py` desde el código).
3. Elige un perfil o ajusta las secciones una a una.
4. Selecciona la carpeta del emulador. La app detecta la carpeta de mods, incluida una ruta `load_directory`
   personalizada de `qt-config.ini`.
5. Pulsa **Instalar**. La app crea la carpeta `00-Super-Hero-Boost` con el módulo, las texturas de botones y los
   romfs opcionales, y parchea la configuración elegida.
6. Cierra el juego antes de instalar o desinstalar.

Para quitar el mod, pulsa **Desinstalar** en la app o borra la carpeta `00-Super-Hero-Boost`.

### Controles del mapeo de botones

- En la pestaña **Objetos** del menú de pausa, con un objeto resaltado:
  **X** lo asigna a **B**, **L** a **L**, **R** a **R** y **A** al **ZR** del juego.
- Pulsar el mismo botón otra vez desasigna; si el objeto ya estaba en otra ranura, se intercambian.
- Si L está en modo **escudo** o **selector**, L no se puede asignar y su botón se oculta del HUD y de la leyenda.
- En modo **selector**, L abre el selector de objetos del juego.

### Línea de comandos

```bash
python app/main.py --cli --emu "RUTA_DEL_EMULADOR" --profile recommended
python app/main.py --cli --emu "RUTA_DEL_EMULADOR" --profile hero-explorer --button-style switch --bm-simple
python app/main.py --cli --emu "RUTA_DEL_EMULADOR" --profile recommended --bm-l selector
```

`--profile` aplica un perfil completo; las opciones individuales lo sobrescriben. `--list-profiles` muestra la lista.

## Compilar

La app no compila el mod: usa el payload ya generado en `app/payload`. Para regenerarlo hace falta el volcado del
juego, LLVM (`clang`, `lld`, `llvm-objcopy`, `llvm-size`, `llvm-nm`) y las dependencias de desarrollo que se indican en
[docs/GUIA-DESARROLLO.md](docs/GUIA-DESARROLLO.md).

```bash
python tools/build_core.py --features stamina,songbook,button_mapping --slots --compat --base 0x4F80000
python tools/make_release.py     # módulo + texturas de botones + romfs opcionales
python tools/build_app.py        # release/SuperHeroBoostConfig[.exe|.app]
```

`build_app.py` usa PyInstaller y no compila de forma cruzada: hay que ejecutarlo en cada sistema destino. El
ejecutable se genera en `release/`. Para más detalle, consulta la guía de desarrollo.

## Documentación

- [docs/GUIA-DESARROLLO.md](docs/GUIA-DESARROLLO.md): arquitectura, ganchos, HUD, configuración y compilación.
- [docs/APP.md](docs/APP.md): app, perfiles y opciones.
- [docs/BUTTON-MAPPING.md](docs/BUTTON-MAPPING.md): diseño del mapeo de botones.
- [docs/RE-NOTES.md](docs/RE-NOTES.md): notas de ingeniería inversa.
- [docs/AUDIT.md](docs/AUDIT.md): auditoría de código y materiales de terceros.

## Aviso

No se redistribuye código, texto, texturas ni ningún otro material del juego. El mod lee los archivos del volcado del
usuario en tiempo de ejecución y solo incluye su propio módulo y su propio arte. Necesitas tu propia copia legal del
juego para usarlo.

## Créditos

Módulo, HUD, sistema de estamina, mapeo de botones (con sus texturas) y app: trabajo original de Kuribox.
