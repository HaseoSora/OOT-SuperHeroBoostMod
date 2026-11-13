"""OoT Master Mod - configuration and installer window. It does not compile anything: the mod is prebuilt and reads
its options when the game loads; this app only edits those options and installs the mod into the emulator.

Headless use (tests):  OotMasterConfig.exe --cli --emu <folder> [--no-classic] [--no-stamina] [--preset N] ...
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import installer as I  # noqa: E402
from i18n import LANGS, tr, system_lang  # noqa: E402

KEYS = ("jump", "attack", "sprint", "block", "shoot", "roll")

def _cfg_paths():
    """Settings live next to the exe (OotMasterConfig.json, portable); if that folder is read-only, in %APPDATA%."""
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    return base / "OotMasterConfig.json", Path(os.environ.get("APPDATA", str(Path.home()))) / "OotMasterConfig" / "settings.json"


# Zelda-flavoured palette: deep forest green, gold, parchment
BG, PANEL, PANEL2 = "#10201a", "#1b3226", "#0c1712"
GOLD, GOLD_HI, GOLD_DIM = "#d8b24a", "#f1d27a", "#8f7a3a"
TEXT, DIM, RED = "#f2e8c9", "#a39a79", "#b8473a"


def load_cfg():
    for p in _cfg_paths():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
    return {}


def save_cfg(d):
    for p in _cfg_paths():
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
            return str(p)
        except OSError:
            continue
    return ""


def cli(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cli", action="store_true")
    ap.add_argument("--emu", required=True)
    ap.add_argument("--no-classic", action="store_true")
    ap.add_argument("--classic-variant", default="default", choices=list(I.CLASSIC_VARIANTS))
    ap.add_argument("--no-stamina", action="store_true")
    ap.add_argument("--preset", type=int, default=0)
    ap.add_argument("--off", default="", help="advanced: comma list of jump,attack,sprint,block,shoot,roll to disable")
    ap.add_argument("--combat-only", action="store_true")
    ap.add_argument("--name", default=I.MOD_NAME)
    ap.add_argument("--enemy-hp", type=int, default=100, help="enemy health, percent (150 = Hero Mode)")
    ap.add_argument("--damage", type=int, default=100, help="damage taken, percent (200 = Hero Mode)")
    ap.add_argument("--no-heart-drop", action="store_true")
    ap.add_argument("--rupees", action="store_true", help="always-visible rupee counter")
    ap.add_argument("--clock", action="store_true", help="always-visible clock")
    ap.add_argument("--clock24", action="store_true")
    a = ap.parse_args(argv)
    off = {x for x in a.off.split(",") if x}
    p = a.preset
    if p in I.PRESET_VIEW:
        v = I.PRESET_VIEW[p]
        s = I.Settings(classic=not a.no_classic, stamina=not a.no_stamina, preset=p, combat_only=bool(v["combat_only"]),
                       **{k: bool(v[k]) for k in KEYS})
    else:
        s = I.Settings(classic=not a.no_classic, stamina=not a.no_stamina, preset=p, combat_only=a.combat_only,
                       **{k: k not in off for k in KEYS})
    s.enemy_hp, s.damage, s.no_heart_drop = a.enemy_hp, a.damage, a.no_heart_drop
    s.hud_rupees, s.hud_clock, s.clock_24h = a.rupees, a.clock, a.clock24
    try:
        r = I.install(Path(a.emu), s, a.classic_variant, a.name)
    except I.InstallError as e:
        print("error:", e.key, e.arg)
        return 1
    print("installed in", r.target, "variant", r.variant)
    for k, arg in r.notes:
        print(" -", k, arg)
    return 0


def gui():
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import filedialog, messagebox, ttk

    try:                                  # crisp text and real sizes on scaled displays
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    cfg = load_cfg()
    root = tk.Tk()
    root.title("OoT Master Mod")
    root.configure(bg=BG)
    root.resizable(False, False)
    fams = set(tkfont.families())
    FAM = next((f for f in ("Palatino Linotype", "Book Antiqua", "Georgia", "Cambria", "Times New Roman") if f in fams), "serif")

    lang = tk.StringVar(value=cfg.get("lang") if cfg.get("lang") in LANGS else system_lang())
    emu = tk.StringVar(value=cfg.get("emu", ""))
    v_classic = tk.BooleanVar(value=cfg.get("classic", True))
    v_variant = tk.StringVar(value=cfg.get("variant", "default") if cfg.get("variant") in I.CLASSIC_VARIANTS else "default")
    v_stam = tk.BooleanVar(value=cfg.get("stamina", True))
    v_preset = tk.IntVar(value=cfg.get("preset", 0))
    custom = {k: bool(cfg.get("custom", {}).get(k, True)) for k in KEYS}
    custom["combat_only"] = bool(cfg.get("custom", {}).get("combat_only", False))
    adv = {k: tk.BooleanVar(value=custom[k]) for k in KEYS}
    v_combat = tk.BooleanVar(value=custom["combat_only"])
    status = tk.StringVar(value="")
    guard = {"on": False}
    ui = {}

    L = lambda key, **kw: tr(lang.get(), key, **kw)  # noqa: E731

    # ---- preset view: the "advanced" boxes show what the chosen preset switches on or off ----
    def apply_view():
        p = v_preset.get()
        guard["on"] = True
        if p == 3:
            for k in KEYS: adv[k].set(custom[k])
            v_combat.set(custom["combat_only"])
        else:
            for k in KEYS: adv[k].set(bool(I.PRESET_VIEW[p][k]))
            v_combat.set(bool(I.PRESET_VIEW[p]["combat_only"]))
        guard["on"] = False

    def remember_custom(*_):
        if guard["on"] or v_preset.get() != 3:
            return
        for k in KEYS: custom[k] = adv[k].get()
        custom["combat_only"] = v_combat.get()

    for v in list(adv.values()) + [v_combat]:
        v.trace_add("write", remember_custom)
    pending = {"id": None}

    def autosave(*_):                       # every change is stored right away (small delay to batch clicks)
        if pending["id"]:
            root.after_cancel(pending["id"])
        pending["id"] = root.after(250, lambda: remember())

    for v in (lang, emu, v_classic, v_variant, v_stam, v_preset, v_combat, *adv.values()):
        v.trace_add("write", autosave)

    def settings():
        p = v_preset.get()
        vals = {k: adv[k].get() for k in KEYS} if p == 3 else {k: bool(I.PRESET_VIEW[p][k]) for k in KEYS}
        co = v_combat.get() if p == 3 else bool(I.PRESET_VIEW[p]["combat_only"])
        return I.Settings(classic=v_classic.get(), stamina=v_stam.get(), preset=p, combat_only=co, **vals)

    def remember():
        return save_cfg({"lang": lang.get(), "emu": emu.get(), "classic": v_classic.get(), "variant": v_variant.get(),
                  "stamina": v_stam.get(), "preset": v_preset.get(), "custom": custom})

    # ---- small styled widgets ----
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Z.TCombobox", fieldbackground=PANEL2, background=PANEL, foreground=TEXT, arrowcolor=GOLD,
                    bordercolor=GOLD_DIM, lightcolor=PANEL, darkcolor=PANEL, selectbackground=PANEL2, selectforeground=TEXT)
    style.map("Z.TCombobox", fieldbackground=[("readonly", PANEL2)], foreground=[("readonly", TEXT)])
    root.option_add("*TCombobox*Listbox.background", PANEL2)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", GOLD_DIM)

    def button(parent, text, cmd, primary=False, **kw):
        b = tk.Button(parent, text=text, command=cmd, font=(FAM, 12, "bold"), relief="flat", bd=0, cursor="hand2",
                      bg=GOLD if primary else PANEL, fg="#1a1408" if primary else GOLD,
                      activebackground=GOLD_HI if primary else "#26443a", activeforeground="#1a1408" if primary else GOLD_HI,
                      disabledforeground="#6b6244", highlightthickness=1, highlightbackground=GOLD,
                      padx=18, pady=7, **kw)
        return b

    def section(parent, title):
        f = tk.Frame(parent, bg=PANEL, highlightbackground=GOLD_DIM, highlightcolor=GOLD, highlightthickness=1)
        f.pack(fill="x", padx=18, pady=(6, 0))
        tk.Label(f, text="✦  " + title, bg=PANEL, fg=GOLD, font=(FAM, 12, "bold")).pack(anchor="w", padx=10, pady=(4, 1))
        return f

    def check(parent, text, var, command=None):
        return tk.Checkbutton(parent, text=text, variable=var, command=command, bg=PANEL, fg=TEXT, selectcolor="#2d5040",
                              activebackground=PANEL, activeforeground=GOLD_HI, disabledforeground=DIM,
                              font=(FAM, 11), anchor="w", highlightthickness=0, bd=0)

    def radio(parent, text, val):
        return tk.Radiobutton(parent, text=text, variable=v_preset, value=val, command=refresh, bg=PANEL, fg=TEXT,
                              selectcolor="#2d5040", activebackground=PANEL, activeforeground=GOLD_HI,
                              disabledforeground=DIM, font=(FAM, 11, "bold"), anchor="w", highlightthickness=0, bd=0)

    def desc(parent, text):
        return tk.Label(parent, text=text, bg=PANEL, fg=DIM, font=(FAM, 9), justify="left", wraplength=640, anchor="w")

    main = tk.Frame(root, bg=BG)
    main.pack(fill="both", expand=True)

    def ok_emu():
        e = emu.get().strip()
        return I.find_mods_dir(Path(e)) if e else None

    def refresh(*_):
        if "install" not in ui:
            return
        stam = v_stam.get()
        for r in ui["radios"]: r.config(state="normal" if stam else "disabled")
        adv_on = stam and v_preset.get() == 3
        for c in ui["advw"]: c.config(state="normal" if adv_on else "disabled")
        ui["variant"].state(["!disabled"] if v_classic.get() else ["disabled"])
        mods = ok_emu()
        ui["install"].config(state="normal" if mods else "disabled")
        ui["mods"].config(text=L("mods_found", a=mods) if mods else L("mods_missing"), fg=GOLD_HI if mods else DIM)
        if not mods and not status.get():
            status.set(L("pick_emu"))
        if mods and status.get() == L("pick_emu"):
            status.set("")
        apply_view()

    def browse():
        d = filedialog.askdirectory(title=L("emu_hint"))
        if d:
            emu.set(d)

    def do_install():
        try:
            status.set(L("working")); root.update_idletasks()
            r = I.install(Path(emu.get().strip()), settings(), v_variant.get())
            remember()
            msg = L("done_msg", n=r.target.name, w=L("with_classic") if r.variant == "classic" else L("without_classic"))
            for k, arg in r.notes:
                msg += "\n\n" + L("n_" + k, a=arg)
            status.set(L("ready"))
            messagebox.showinfo(L("done_title"), msg)
        except I.InstallError as ex:
            status.set("")
            messagebox.showerror(L("err_title"), L("e_" + ex.key, a=ex.arg))
        except Exception as ex:   # unexpected
            status.set("")
            messagebox.showerror(L("err_title"), str(ex))

    def do_remove():
        e = emu.get().strip()
        status.set(L("uninstalled") if e and I.uninstall(Path(e)) else L("nothing"))

    def about():
        w = tk.Toplevel(root)
        w.title(L("about_title"))
        w.configure(bg=BG)
        w.resizable(False, False)
        w.transient(root)
        c = tk.Canvas(w, width=420, height=90, bg=BG, highlightthickness=0)
        c.pack()
        triforce(c, 210, 46, 34)
        tk.Label(w, text=L("about_body", a=I.CLASSIC_VERSION), bg=BG, fg=TEXT, font=(FAM, 11), justify="center",
                 wraplength=380).pack(padx=24, pady=(4, 14))
        button(w, "OK", w.destroy, primary=True).pack(pady=(0, 16))
        w.grab_set()

    def triforce(c, cx, cy, s):
        h = s * 0.87
        for dx, dy in ((0, -h / 2), (-s / 2, h / 2), (s / 2, h / 2)):
            x, y = cx + dx, cy + dy
            c.create_polygon(x, y - h / 2, x - s / 2, y + h / 2, x + s / 2, y + h / 2, fill=GOLD, outline=GOLD_HI)
            c.create_polygon(x, y - h / 2 + h * 0.22, x - s * 0.17, y + h * 0.16, x + s * 0.17, y + h * 0.16,
                             fill=BG, outline=GOLD_DIM)

    def render():
        for w in main.winfo_children():
            w.destroy()
        ui.clear()
        # header: triforce, title, language, about
        hd = tk.Canvas(main, width=780, height=96, bg=BG, highlightthickness=0)
        hd.pack()
        triforce(hd, 64, 48, 52)
        hd.create_text(126, 34, text="OoT Master Mod", anchor="w", fill=GOLD, font=(FAM, 27, "bold"))
        hd.create_text(128, 68, text=L("subtitle"), anchor="w", fill=TEXT, font=(FAM, 11, "italic"))
        lb = ttk.Combobox(hd, state="readonly", style="Z.TCombobox", width=11, values=list(LANGS.values()))
        lb.current(list(LANGS).index(lang.get()))
        lb.bind("<<ComboboxSelected>>", lambda e: (lang.set(list(LANGS)[lb.current()]), status.set(""), render()))
        hd.create_window(690, 30, window=lb)
        ab = button(hd, L("about"), about); ab.config(font=(FAM, 10, "bold"), padx=12, pady=3)
        hd.create_window(690, 62, window=ab)
        hd.create_line(18, 92, 762, 92, fill=GOLD_DIM)
        hd.create_polygon(390, 86, 396, 92, 390, 98, 384, 92, fill=GOLD)

        s = section(main, L("emulator"))
        row = tk.Frame(s, bg=PANEL); row.pack(fill="x", padx=10)
        e = tk.Entry(row, textvariable=emu, bg=PANEL2, fg=TEXT, insertbackground=GOLD, relief="flat", font=(FAM, 11),
                     highlightthickness=1, highlightbackground=GOLD_DIM, highlightcolor=GOLD)
        e.pack(side="left", fill="x", expand=True, ipady=4)
        button(row, L("browse"), browse).pack(side="left", padx=(8, 0))
        desc(s, L("emu_hint")).pack(anchor="w", padx=10, pady=(4, 0))
        ui["mods"] = tk.Label(s, text="", bg=PANEL, fg=DIM, font=(FAM, 9), anchor="w")
        ui["mods"].pack(anchor="w", padx=10, pady=(0, 5))

        s = section(main, L("modules"))
        check(s, L("classic"), v_classic, refresh).pack(anchor="w", padx=14)
        desc(s, L("classic_desc", a=I.CLASSIC_VERSION)).pack(anchor="w", padx=40)
        vr = tk.Frame(s, bg=PANEL); vr.pack(anchor="w", padx=40, pady=(3, 6))
        tk.Label(vr, text=L("glyphs") + ":", bg=PANEL, fg=TEXT, font=(FAM, 10)).pack(side="left")
        names = [L("g_" + k) for k in I.CLASSIC_VARIANTS]
        vb = ttk.Combobox(vr, state="readonly", style="Z.TCombobox", width=16, values=names)
        vb.current(list(I.CLASSIC_VARIANTS).index(v_variant.get()))
        vb.bind("<<ComboboxSelected>>", lambda ev: v_variant.set(list(I.CLASSIC_VARIANTS)[vb.current()]))
        vb.pack(side="left", padx=8)
        ui["variant"] = vb
        check(s, L("stamina"), v_stam, refresh).pack(anchor="w", padx=14, pady=(0, 6))

        s = section(main, L("preset"))
        ui["radios"] = []
        for i in range(4):
            r = radio(s, L(f"p{i}"), i); r.pack(anchor="w", padx=14)
            desc(s, L(f"p{i}d")).pack(anchor="w", padx=40, pady=(0, 1))
            ui["radios"].append(r)

        s = section(main, L("adv"))
        grid = tk.Frame(s, bg=PANEL); grid.pack(fill="x", padx=14)
        ui["advw"] = []
        for n, k in enumerate(KEYS):
            c = check(grid, L("a_" + k), adv[k]); c.grid(row=n // 2, column=n % 2, sticky="w", padx=(0, 30))
            ui["advw"].append(c)
        c = check(s, L("combat_only"), v_combat); c.pack(anchor="w", padx=14, pady=(2, 8))
        ui["advw"].append(c)

        bar = tk.Frame(main, bg=BG); bar.pack(fill="x", padx=18, pady=(12, 2))
        ui["install"] = button(bar, "⚔  " + L("install"), do_install, primary=True)
        ui["install"].pack(side="left")
        button(bar, L("uninstall"), do_remove).pack(side="left", padx=10)
        tk.Label(main, textvariable=status, bg=BG, fg=GOLD_HI, font=(FAM, 10, "italic"), anchor="w").pack(anchor="w", padx=20, pady=(2, 10))
        ui["install"].config(state="disabled")
        refresh()
        root.update_idletasks()
        root.geometry(f"780x{main.winfo_reqheight()}")

    emu.trace_add("write", lambda *_: (status.set(""), refresh()))
    render()
    root.protocol("WM_DELETE_WINDOW", lambda: (remember(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    if "--cli" in sys.argv:
        raise SystemExit(cli(sys.argv[1:]))
    gui()
