# Super Hero Boost

Módulo de gameplay para el remake de consola (actualización v131072) y su app de configuración multiplataforma
`SuperHeroBoostConfig`:

- **Perfiles completos**: **Recomendado** (todo activado), Base, Modo héroe, Héroe + estamina, Héroe explorador,
  Superhéroe, Ultra héroe y Supervivencia. Todos incluyen el HUD y Classic Item Slots, y ajustan de una vez la
  dificultad, la estamina y el sprint; cualquier cambio manual pasa a **Personalizado**.
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
- Compatible con **Classic Item Slots** (la app lo descarga de su release oficial en GitHub y lo instala con su crédito
  original; no va incluido en el código).

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
[docs/CLASSIC-HOOKS.md](docs/CLASSIC-HOOKS.md), [docs/CLASSIC-REPLICA.md](docs/CLASSIC-REPLICA.md) (Classic Item
Slots) y [docs/AUDIT.md](docs/AUDIT.md) (auditoría de código y materiales de terceros).

Pasos rápidos:

```
python tools/build_core.py --features stamina,songbook --compat --base 0x4F87000
python tools/make_release.py
python tools/build_app.py
```

El ejecutable se genera en `release/` para el sistema donde se compila (PyInstaller no hace compilación cruzada).

## Créditos

Classic Item Slots v1.4.3, de sonofsilvanus, se descarga de su release oficial de GitHub cuando se activa y se instala
tal cual. No se distribuye con la app. El módulo, el HUD, el sistema de estamina y la app son trabajo original.
