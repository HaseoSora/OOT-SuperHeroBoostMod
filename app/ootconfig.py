"""OOT Master Mod - configuration app (GUI). Does not compile anything: it edits the options of the prebuilt
mod and installs it into the emulator's mod folder.

Headless use (tests):  ootconfig.exe --cli --emu <folder> [--no-classic] [--no-stamina] [--preset N] ...
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import installer as I  # noqa: E402

CFG = Path(os.environ.get("APPDATA", str(Path.home()))) / "OotMasterConfig" / "settings.json"
PRESETS = ["Hardcore (todas las acciones gastan)", "Solo combate", "Solo sprint (como BotW)", "Avanzado"]


def load_cfg():
    try:
        return json.loads(CFG.read_text())
    except Exception:
        return {}


def save_cfg(d):
    CFG.parent.mkdir(parents=True, exist_ok=True)
    CFG.write_text(json.dumps(d, indent=1))


def cli(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", action="store_true")
    ap.add_argument("--emu", required=True)
    ap.add_argument("--classic-dir", default="")
    ap.add_argument("--no-classic", action="store_true")
    ap.add_argument("--classic-variant", default="", choices=["", "default", "playstation", "xbox"],
                    help="download this Classic variant from its release page")
    ap.add_argument("--classic-zip", default="", help="use a Classic zip downloaded by hand")
    ap.add_argument("--no-stamina", action="store_true")
    ap.add_argument("--preset", type=int, default=0)
    ap.add_argument("--off", default="", help="advanced: comma list of jump,attack,sprint,block,shoot,roll to disable")
    ap.add_argument("--combat-only", action="store_true")
    ap.add_argument("--name", default=I.MOD_NAME)
    a = ap.parse_args(argv)
    off = {x for x in a.off.split(",") if x}
    s = I.Settings(classic=not a.no_classic, stamina=not a.no_stamina, preset=a.preset, combat_only=a.combat_only,
                   **{k: k not in off for k in ("jump", "attack", "sprint", "block", "shoot", "roll")})
    cdir = Path(a.classic_dir) if a.classic_dir else None
    if a.classic_zip:
        cdir = I.classic_from_zip(Path(a.classic_zip))
    r = I.install(Path(a.emu), s, cdir, a.name, a.classic_variant, print)
    print("instalado en", r.target, "variante", r.variant)
    for n in r.notes:
        print(" -", n)
    return 0


def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    cfg = load_cfg()
    root = tk.Tk()
    root.title("OOT Master Mod - Configuración")
    root.geometry("640x640")
    pad = {"padx": 10, "pady": 4}

    emu = tk.StringVar(value=cfg.get("emu", ""))
    classic_path = tk.StringVar(value=cfg.get("classic_dir", ""))
    v_classic = tk.BooleanVar(value=cfg.get("classic", True))
    v_stam = tk.BooleanVar(value=cfg.get("stamina", True))
    v_preset = tk.IntVar(value=cfg.get("preset", 0))
    adv = {k: tk.BooleanVar(value=cfg.get(k, True)) for k in ("jump", "attack", "sprint", "block", "shoot", "roll")}
    v_combat = tk.BooleanVar(value=cfg.get("combat_only", False))
    status = tk.StringVar(value="")

    f = ttk.LabelFrame(root, text="Emulador")
    f.pack(fill="x", **pad)
    row = ttk.Frame(f); row.pack(fill="x", padx=6, pady=4)
    ttk.Entry(row, textvariable=emu).pack(side="left", fill="x", expand=True)
    mods_lbl = ttk.Label(f, text="", foreground="#555")
    mods_lbl.pack(anchor="w", padx=8)
    classic_lbl = ttk.Label(f, text="", foreground="#555")
    classic_lbl.pack(anchor="w", padx=8, pady=(0, 4))

    def detect(*_):
        e = Path(emu.get().strip()) if emu.get().strip() else None
        mods = I.find_mods_dir(e) if e and e.exists() else None
        mods_lbl.config(text=f"Carpeta de mods: {mods}" if mods else "Carpeta de mods: no encontrada")
        cl = I.find_classic(mods) if mods else None
        if cl and not classic_path.get():
            classic_path.set(str(cl))
        shown = classic_path.get() or (str(cl) if cl else "")
        classic_lbl.config(text=f"Classic Item Slots: {shown}" if shown else "Classic Item Slots: no detectado")
        return mods

    def browse():
        d = filedialog.askdirectory(title="Carpeta del emulador (la que contiene 'user')")
        if d:
            emu.set(d); classic_path.set(""); detect()

    ttk.Button(row, text="Examinar…", command=browse).pack(side="left", padx=6)
    emu.trace_add("write", lambda *_: None)

    g = ttk.LabelFrame(root, text="Módulos")
    g.pack(fill="x", **pad)
    ttk.Checkbutton(g, text="Classic Item Slots (botones B / L / R / ZR con objetos)", variable=v_classic,
                    command=lambda: refresh()).pack(anchor="w", padx=6, pady=2)
    crow = ttk.Frame(g); crow.pack(fill="x", padx=26, pady=(0, 4))
    ttk.Label(crow, text="Versión de Classic:").pack(side="left")
    SRC = ["Botones Switch (por defecto, se descarga)", "Botones PlayStation (se descarga)", "Botones Xbox (se descarga)",
           "Usar el Classic que ya tengo instalado", "Elegir un .zip de Classic…"]
    v_src = tk.IntVar(value=cfg.get("classic_src", 0))
    src_box = ttk.Combobox(crow, state="readonly", values=SRC, width=44)
    src_box.current(v_src.get()); src_box.pack(side="left", padx=6)
    src_box.bind("<<ComboboxSelected>>", lambda e: v_src.set(src_box.current()))
    ttk.Checkbutton(g, text="Estamina", variable=v_stam, command=lambda: refresh()).pack(anchor="w", padx=6, pady=2)

    p = ttk.LabelFrame(root, text="Preset de estamina")
    p.pack(fill="x", **pad)
    radios = []
    for i, t in enumerate(PRESETS):
        r = ttk.Radiobutton(p, text=t, variable=v_preset, value=i, command=lambda: refresh())
        r.pack(anchor="w", padx=6, pady=1); radios.append(r)

    a = ttk.LabelFrame(root, text="Avanzado: qué consume estamina")
    a.pack(fill="x", **pad)
    names = {"jump": "Saltos", "attack": "Ataques", "sprint": "Sprint", "block": "Bloqueo con escudo",
             "shoot": "Disparos (arco / tirachinas)", "roll": "Rodar y esquivar"}
    advw = []
    for k, t in names.items():
        c = ttk.Checkbutton(a, text=t, variable=adv[k]); c.pack(anchor="w", padx=6, pady=1); advw.append(c)
    c = ttk.Checkbutton(a, text="Solo en combate", variable=v_combat); c.pack(anchor="w", padx=6, pady=(6, 2)); advw.append(c)

    def refresh():
        src_box.state(["!disabled"] if v_classic.get() else ["disabled"])
        on = v_stam.get()
        for r in radios: r.state(["!disabled"] if on else ["disabled"])
        adv_on = on and v_preset.get() == 3
        for c in advw: c.state(["!disabled"] if adv_on else ["disabled"])

    def settings():
        return I.Settings(classic=v_classic.get(), stamina=v_stam.get(), preset=v_preset.get(),
                          combat_only=v_combat.get(), **{k: v.get() for k, v in adv.items()})

    def remember():
        d = {"emu": emu.get(), "classic_dir": classic_path.get(), "classic_src": v_src.get()}
        d.update(settings().to_dict())
        save_cfg(d)

    def do_install():
        try:
            e = Path(emu.get().strip())
            if not e.exists():
                raise FileNotFoundError("Elige la carpeta del emulador.")
            cl, variant = None, ""
            if v_classic.get():
                i = v_src.get()
                if i < 3:
                    variant = ["default", "playstation", "xbox"][i]
                    status.set("Descargando Classic Item Slots (solo la primera vez)…"); root.update_idletasks()
                elif i == 3:
                    mods = I.find_mods_dir(e)
                    cl = I.find_classic(mods) if mods else None
                    if not cl:
                        raise FileNotFoundError("No encuentro un Classic Item Slots original en tus mods.")
                else:
                    zp = filedialog.askopenfilename(title="Zip de Classic Item Slots", filetypes=[("Zip", "*.zip")])
                    if not zp:
                        return
                    cl = I.classic_from_zip(Path(zp))
            r = I.install(e, settings(), cl, I.MOD_NAME, variant, lambda m: (status.set(m), root.update_idletasks()))
            remember()
            msg = f"Instalado como mod '{r.target.name}' ({'con' if r.variant == 'classic' else 'sin'} Classic).\n\n" + "\n".join(r.notes)
            status.set("Listo. Reinicia el emulador / el juego para que cargue.")
            messagebox.showinfo("Listo", msg + "\n\nCierra el juego antes de volver a instalar.")
        except Exception as ex:
            status.set("")
            messagebox.showerror("No se pudo instalar", str(ex))

    def do_remove():
        e = Path(emu.get().strip())
        if I.uninstall(e):
            status.set("Mod desinstalado.")
        else:
            status.set("No hay un mod instalado por esta app.")

    b = ttk.Frame(root); b.pack(fill="x", **pad)
    ttk.Button(b, text="Enviar al emulador como mod", command=do_install).pack(side="left", padx=4)
    ttk.Button(b, text="Desinstalar", command=do_remove).pack(side="left", padx=4)
    ttk.Label(root, textvariable=status, foreground="#2a6").pack(anchor="w", padx=12)
    detect(); refresh()
    root.protocol("WM_DELETE_WINDOW", lambda: (remember(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    if "--cli" in sys.argv:
        raise SystemExit(cli(sys.argv[1:]))
    gui()
