# Super Hero Boost

Módulo de gameplay para el remake de consola (actualización v131072) y su app de configuración multiplataforma
`SuperHeroBoostConfig`:

- **Perfiles completos**: **Recomendado** (todo activado), Base, Modo héroe, Héroe + estamina, Héroe explorador,
  Superhéroe, Ultra héroe y Supervivencia. Todos incluyen el HUD y el mapeo de botones (nuestros botones de objeto),
  y ajustan de una vez la dificultad, la estamina y el sprint; cualquier cambio manual pasa a **Personalizado**.
- **Estamina** con estilos (hardcore, solo combate, solo sprint, avanzado), agotamiento y recarga; coste al rodar,
  saltar, atacar, disparar, esprintar y bloquear con el escudo.
- **Anillo de estamina** junto al jugador, dibujado con texturas del juego.
- **Velocidad del sprint** configurable (por defecto +25 %).
- **Vida de los enemigos** y **daño recibido** multiplicables; opción **sin drop de corazones**.
- **Reloj y contador de rupias siempre visibles**, con el aspecto nativo del juego (12 / 24 h).
- **Autoreproducción del songbook**: al elegir una canción aprendida en el songbook nativo (ZL) se reproduce sola,
  con el héroe tocándola y activando su efecto. Solo funciona con canciones aprendidas y no con la canción del
  espantapájaros.
- **Opciones beta**: duplicar enemigos genéricos (Opción A) y acelerar su movimiento, animación y cadencia ×2. Son experimentales
  y pueden romper puzles, misiones o el rendimiento; se activan en la app y se instalan como romfs extra.
- **Mapeo de botones propio**: botones de objeto B, L, R y ZR en el HUD, asignables desde el menú de pausa. Incluye
  estilo de botones **Switch / PlayStation / Xbox**, diseño **extendido o simple** y modos del botón L (objeto,
  escudo o selector). No usa ningún mod de terceros.

## Uso

Abre `SuperHeroBoostConfig`, elige un perfil (o ajusta las secciones una a una), selecciona la carpeta del emulador e
**Instala**. La app crea la carpeta `00-Super-Hero-Boost` en los mods del juego y guarda tus ajustes automáticamente.

La app funciona en **Windows, macOS y Linux** (Python 3.10+ con Tkinter). Los ajustes se guardan junto al programa o,
si esa carpeta no es escribible, en la carpeta de configuración del usuario:

- Windows: `%APPDATA%\SuperHeroBoostConfig\settings.json`
- macOS: `~/Library/Application Support/SuperHeroBoostConfig/settings.json`
- Linux: `~/.config/SuperHeroBoostConfig/settings.json`

## Desarrollo

Todo el proceso (arquitectura, ganchos, HUD, configuración, compilación, pruebas y cómo añadir opciones) está en
**[docs/GUIA-DESARROLLO.md](docs/GUIA-DESARROLLO.md)**.

Otras notas: [docs/APP.md](docs/APP.md) (app y perfiles), [docs/RE-NOTES.md](docs/RE-NOTES.md) (ingeniería inversa),
[docs/BUTTON-MAPPING.md](docs/BUTTON-MAPPING.md) (buttonMapping, nuestros botones de objetos) y [docs/AUDIT.md](docs/AUDIT.md) (auditoría de código y materiales de terceros).

Pasos rápidos:

```
python tools/build_core.py --features stamina,songbook,button_mapping --slots --compat --base 0x4F80000
python tools/make_release.py
python tools/build_app.py
```

El ejecutable se genera en `release/` para el sistema donde se compila (PyInstaller no hace compilación cruzada).

## Créditos

El módulo, el HUD, el sistema de estamina, el mapeo de botones (con sus texturas de botones) y la app son trabajo
original. No se incluye ni se descarga ningún mod de terceros.
