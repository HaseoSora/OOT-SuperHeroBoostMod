# OoT Master Mod

Mod para *The Legend of Zelda: Ocarina of Time* (Switch 2, actualización v131072), con su app de configuración
`OotMasterConfig.exe`:

- **Estamina** con presets (hardcore, solo combate, solo sprint, avanzado), agotamiento y recarga; coste al rodar,
  saltar, atacar, disparar, esprintar y bloquear con el escudo.
- **Anillo de estamina** junto a Link, dibujado con texturas del juego.
- **Velocidad del sprint** configurable (por defecto +25 %).
- **Vida de los enemigos** y **daño recibido** multiplicables; opción **sin drop de corazones**.
- **Reloj y contador de rupias siempre visibles**, con el aspecto nativo del juego (12 / 24 h).
- Compatible con **Classic Item Slots** (se instala junto al mod desde la app).

## Uso
Abrir `OotMasterConfig.exe`, elegir la carpeta del emulador, marcar las opciones e **Instalar**. Instala la carpeta
`00-OOT-Master` en los mods del juego.

## Desarrollo
Todo el proceso (arquitectura, ganchos, HUD, configuración, compilación, pruebas en el emulador y cómo añadir
opciones) está en **[docs/GUIA-DESARROLLO.md](docs/GUIA-DESARROLLO.md)**.

Otras notas: [docs/RE-NOTES.md](docs/RE-NOTES.md) (ingeniería inversa), [docs/APP.md](docs/APP.md) (app),
[docs/CLASSIC-HOOKS.md](docs/CLASSIC-HOOKS.md) y [docs/CLASSIC-REPLICA.md](docs/CLASSIC-REPLICA.md) (Classic Item
Slots).

Pasos rápidos:
```
python tools/build_core.py --features hero_core --compat --base 0x4F87000
python tools/make_release.py
python tools/build_app.py
```
