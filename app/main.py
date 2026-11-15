"""Super Hero Boost - configuration and installer window.

The mod is prebuilt and reads its options when the game loads; this app only
edits those options, remembers them and installs the mod into the emulator.
It does not compile anything.

Headless use (tests):
    SuperHeroBoostConfig --cli --emu <folder> [--profile hero] [--preset 2] ...
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import installer as I  # noqa: E402
import paths  # noqa: E402
from i18n import LANGS, tr, system_lang  # noqa: E402
from presets import (DEFAULT_PROFILE, KEYS, PROFILES, PROFILE_KEYS,  # noqa: E402
                     STAMINA_MODES, defaults, profile_values)


# ---------------------------------------------------------------- settings file
def load_cfg() -> dict:
    for p in paths.settings_paths():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}


def save_cfg(d: dict) -> str:
    for p in paths.settings_paths():
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(d, indent=1, ensure_ascii=False), encoding="utf-8")
            return str(p)
        except OSError:
            continue
    return ""


# ---------------------------------------------------------------- command line
def cli(argv) -> int:
    ap = argparse.ArgumentParser(description="Super Hero Boost installer (headless mode)")
    ap.add_argument("--cli", action="store_true")
    ap.add_argument("--emu", help="emulator folder (the one that contains 'user')")
    ap.add_argument("--profile", choices=PROFILE_KEYS, default="custom",
                    help="apply a complete game profile before the individual options")
    ap.add_argument("--list-profiles", action="store_true", help="print the profile keys and exit")
    ap.add_argument("--preset", type=int, choices=range(4), default=None,
                    help="stamina style: 0 hardcore, 1 combat only, 2 sprint only, 3 advanced")
    ap.add_argument("--no-button-mapping", action="store_true", help="no extra item buttons (button mapping)")
    ap.add_argument("--button-style", choices=I.BUTTON_STYLES, default=None, help="button mapping: button pictures")
    ap.add_argument("--bm-simple", action="store_true", help="button mapping: simple layout (assignable buttons only)")
    ap.add_argument("--bm-l", choices=I.L_MODES, default=None,
                    help="button mapping: L is an item button (assign) or the game's item selector")
    ap.add_argument("--no-stamina", action="store_true")
    ap.add_argument("--no-songbook", action="store_true", help="disable playing songs from the native songbook")
    ap.add_argument("--enemy-double", action="store_true", help="beta: duplicate generic enemies (romfs)")
    ap.add_argument("--enemy-speed", action="store_true", help="beta: accelerate enemy animation/movement/cadence (romfs)")
    ap.add_argument("--great-fairy", action="store_true", help="reorder the three Great Fairy magic rewards (romfs)")
    ap.add_argument("--farore-outdoor", action="store_true", help="allow Farore's Wind points outside dungeons (romfs)")
    ap.add_argument("--hud-collectibles", action="store_true", help="per-area Skulltula / heart-piece counter")
    ap.add_argument("--off", default=None, help="advanced: comma list of jump,attack,sprint,block,shoot,roll to disable")
    ap.add_argument("--combat-only", action="store_true", default=None)
    ap.add_argument("--name", default=I.MOD_NAME)
    ap.add_argument("--enemy-hp", type=int, default=None, help="enemy health, percent (150 = Hero Mode)")
    ap.add_argument("--damage", type=int, default=None, help="damage taken, percent (200 = Hero Mode)")
    ap.add_argument("--no-heart-drop", action="store_true")
    ap.add_argument("--sprint-speed", type=int, default=None, help="sprint speed, percent (125 = default)")
    ap.add_argument("--rupees", action="store_true", help="always-visible rupee counter")
    ap.add_argument("--clock", action="store_true", help="always-visible clock")
    ap.add_argument("--clock24", action="store_true")
    a = ap.parse_args(argv)

    if a.list_profiles:
        from i18n import T
        for key in PROFILE_KEYS:
            token = "profile_custom" if key == "custom" else "p_" + key.replace("-", "_")
            name = T["en"].get(token, "").replace("★", "*")
            print(f"{key:13s} {name}")
        return 0
    if not a.emu:
        ap.error("--emu is required")

    v = profile_values(a.profile) if a.profile != "custom" else defaults()
    costs = dict(zip(KEYS, v["costs"]))
    if a.off is not None:
        for k in a.off.split(","):
            if k in costs:
                costs[k] = False
    s = I.Settings(button_mapping=v["button_mapping"], stamina=v["stamina"], songbook=v["songbook"], preset=v["mode"],
                   combat_only=v["combat_only"], **costs,
                   enemy_hp=v["enemy_hp"], damage=v["damage"],
                   no_heart_drop=v["no_heart_drop"], sprint_speed=v["sprint_speed"],
                   hud_rupees=v["hud_rupees"], hud_clock=v["hud_clock"], clock_24h=v["clock_24h"])
    if a.preset is not None:
        s.preset = a.preset
    if a.no_button_mapping:
        s.button_mapping = False
    if a.button_style:
        s.button_style = a.button_style
    if a.bm_simple:
        s.bm_simple = True
    if a.bm_l:
        s.bm_l_mode = a.bm_l
    if a.no_stamina:
        s.stamina = False
    if a.no_songbook:
        s.songbook = False
    if a.enemy_double:
        s.enemy_double = True
    if a.enemy_speed:
        s.enemy_speed = True
    if a.great_fairy:
        s.great_fairy = True
    if a.farore_outdoor:
        s.farore_outdoor = True
    if a.hud_collectibles:
        s.hud_collectibles = True
    if a.combat_only:
        s.combat_only = True
    if a.enemy_hp is not None:
        s.enemy_hp = a.enemy_hp
    if a.damage is not None:
        s.damage = a.damage
    if a.sprint_speed is not None:
        s.sprint_speed = a.sprint_speed
    if a.no_heart_drop:
        s.no_heart_drop = True
    if a.rupees:
        s.hud_rupees = True
    if a.clock:
        s.hud_clock = True
    if a.clock24:
        s.clock_24h = True

    try:
        r = I.install(Path(a.emu), s, a.name)
    except I.InstallError as e:
        print("error:", e.key, e.arg)
        return 1
    print("installed in", r.target, "variant", r.variant)
    for k, arg in r.notes:
        print(" -", k, arg)
    return 0


# ---------------------------------------------------------------- window
BG = "#0c1712"
SIDEBAR = "#08110d"
PANEL = "#14251b"
PANEL2 = "#09130e"
BORDER = "#2f4a36"
ACCENT = "#d8b24a"
ACCENT_DARK = "#7a5c1f"
AMBER = "#e8b04a"
TEXT = "#f2e8c9"
DIM = "#a9a184"
RED = "#c9564a"


class ScrollArea:
    """A vertical scrolling frame that also works with wheel/trackpad on every OS."""

    def __init__(self, parent, bg):
        import tkinter as tk
        self.frame = tk.Frame(parent, bg=bg)
        self.canvas = tk.Canvas(self.frame, bg=bg, highlightthickness=0)
        self.bar = tk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar.pack(side="right", fill="y")
        self.inner = tk.Frame(self.canvas, bg=bg)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.refresh())
        self.canvas.bind("<Configure>", self._resize)
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>", self._wheel)
        self.canvas.bind_all("<Button-5>", self._wheel)

    def _resize(self, event):
        self.canvas.itemconfigure(self._win, width=event.width)
        self.refresh()

    def refresh(self):
        """Recalculate the scrollable region (call it after showing another section)."""
        try:
            self.inner.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def destroy(self):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            try:
                self.canvas.unbind_all(seq)
            except Exception:
                pass
        self.frame.destroy()

    def _wheel(self, event):
        # only scroll when the pointer is over this area (bind_all is global)
        try:
            x, y = event.x_root, event.y_root
            widget = self.frame.winfo_containing(x, y)
        except Exception:
            widget = None
        if widget is not None:
            w = widget
            inside = False
            while w is not None:
                if w is self.frame or w is self.canvas:
                    inside = True
                    break
                w = getattr(w, "master", None)
            if not inside:
                return
        bbox = self.canvas.bbox("all")
        if not bbox or bbox[3] - bbox[1] <= self.canvas.winfo_height():
            return
        if getattr(event, "num", None) == 4:
            step = -1
        elif getattr(event, "num", None) == 5:
            step = 1
        else:
            step = -1 if getattr(event, "delta", 0) > 0 else 1
        self.canvas.yview_scroll(step * 3, "units")


def gui() -> None:
    import tkinter as tk
    import tkinter.font as tkfont
    from tkinter import filedialog, messagebox, ttk

    if sys.platform == "win32":                    # crisp text on scaled displays
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    cfg = load_cfg()
    root = tk.Tk()
    root.title("Super Hero Boost")
    root.configure(bg=BG)
    root.geometry("1060x740")
    root.minsize(920, 620)

    fams = set(tkfont.families())
    FAM = next((f for f in ("Segoe UI", "SF Pro Text", "Helvetica Neue", "DejaVu Sans", "Arial") if f in fams), "TkDefaultFont")
    DISPLAY = next((f for f in ("Palatino Linotype", "Book Antiqua", "Georgia", "Cambria", "DejaVu Serif",
                                "Times New Roman") if f in fams), FAM)

    lang = tk.StringVar(value=cfg.get("lang") if cfg.get("lang") in LANGS else system_lang())
    emu = tk.StringVar(value=cfg.get("emu", ""))
    profile = tk.StringVar(value=cfg.get("profile") if cfg.get("profile") in PROFILE_KEYS else "custom")
    bmap = tk.BooleanVar(value=bool(cfg.get("button_mapping", True)))
    # button style, layout and L mode: personal choices, not part of a profile
    bstyle = tk.StringVar(value=cfg.get("button_style") if cfg.get("button_style") in I.BUTTON_STYLES else "switch")
    bsimple = tk.BooleanVar(value=bool(cfg.get("bm_simple", False)))
    blmode = tk.StringVar(value=cfg.get("bm_l_mode") if cfg.get("bm_l_mode") in I.L_MODES else "assign")
    stamina = tk.BooleanVar(value=bool(cfg.get("stamina", True)))
    songbook = tk.BooleanVar(value=bool(cfg.get("songbook", True)))
    hud_collectibles = tk.BooleanVar(value=bool(cfg.get("hud_collectibles", False)))
    enemy_double = tk.BooleanVar(value=bool(cfg.get("enemy_double", False)))
    enemy_speed = tk.BooleanVar(value=bool(cfg.get("enemy_speed", False)))
    great_fairy = tk.BooleanVar(value=bool(cfg.get("great_fairy", False)))
    farore_outdoor = tk.BooleanVar(value=bool(cfg.get("farore_outdoor", False)))
    mode = tk.StringVar(value=cfg.get("stamina_mode") if cfg.get("stamina_mode") in STAMINA_MODES
                        else STAMINA_MODES[cfg.get("preset", 0)] if cfg.get("preset", 0) in range(4) else "hardcore")

    saved_costs = cfg.get("costs")
    if not isinstance(saved_costs, dict):
        saved_costs = cfg.get("custom") if isinstance(cfg.get("custom"), dict) else {}
    costs = {k: tk.BooleanVar(value=bool(saved_costs.get(k, True))) for k in KEYS}
    combat = tk.BooleanVar(value=bool(saved_costs.get("combat_only", cfg.get("combat_only", False))))
    MULT = (100, 150, 200, 300)
    hp = tk.IntVar(value=cfg.get("enemy_hp", 100) if cfg.get("enemy_hp", 100) in MULT else 100)
    dmg = tk.IntVar(value=cfg.get("damage", 100) if cfg.get("damage", 100) in MULT else 100)
    SPEEDS = (100, 125, 150, 175, 200, 250, 300)
    speed = tk.IntVar(value=cfg.get("sprint_speed", 125) if cfg.get("sprint_speed", 125) in SPEEDS else 125)
    nodrop = tk.BooleanVar(value=bool(cfg.get("no_heart_drop", False)))
    rupees = tk.BooleanVar(value=bool(cfg.get("hud_rupees", False)))
    CLOCK_MODES = ("off", "12", "24")
    _clock = cfg.get("clock_mode")
    if _clock not in CLOCK_MODES:
        _clock = "24" if cfg.get("clock_24h") else "12" if cfg.get("hud_clock") else "off"
    clock_mode = tk.StringVar(value=_clock)

    status = tk.StringVar(value="")
    guard = {"on": False}
    ui = {"nav": {}, "sections": {}}
    state = {"section": "install"}

    L = lambda key, **kw: tr(lang.get(), key, **kw)  # noqa: E731

    # ---- style ----
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("SHB.TCombobox", fieldbackground=PANEL2, background=PANEL, foreground=TEXT,
                    arrowcolor=ACCENT, bordercolor=BORDER, lightcolor=PANEL, darkcolor=PANEL,
                    selectbackground=PANEL2, selectforeground=TEXT)
    style.map("SHB.TCombobox", fieldbackground=[("readonly", PANEL2)], foreground=[("readonly", TEXT)])
    root.option_add("*TCombobox*Listbox.background", PANEL2)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_DARK)
    root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

    # ---- small widget helpers ----
    def button(parent, text, cmd, primary=False, **kw):
        return tk.Button(parent, text=text, command=cmd, font=(FAM, 10, "bold"), relief="flat", bd=0,
                         cursor="hand2", bg=ACCENT if primary else PANEL2, fg="#1a1408" if primary else TEXT,
                         activebackground="#f1d27a" if primary else BORDER,
                         activeforeground="#1a1408" if primary else TEXT,
                         disabledforeground=DIM, highlightthickness=1,
                         highlightbackground=ACCENT if primary else BORDER,
                         padx=16, pady=7, **kw)

    def label(parent, text, size=10, color=TEXT, bold=False, italic=False, wrap=760, **kw):
        style_name = "italic" if italic else ("bold" if bold else "normal")
        return tk.Label(parent, text=text, bg=kw.pop("bg", PANEL), fg=color, font=(FAM, size, style_name),
                        justify="left", anchor="w", wraplength=wrap, **kw)

    def card(parent, title, desc=None):
        f = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        f.pack(fill="x", padx=4, pady=(0, 12))
        tk.Label(f, text=title, bg=PANEL, fg=ACCENT, font=(DISPLAY, 13, "bold"), anchor="w").pack(
            anchor="w", padx=14, pady=(10, 0))
        if desc:
            label(f, desc, size=9, color=DIM, bg=PANEL).pack(anchor="w", padx=14, pady=(2, 8))
        body = tk.Frame(f, bg=PANEL)
        body.pack(fill="x", padx=14, pady=(0, 12))
        return body

    def check(parent, text, var):
        return tk.Checkbutton(parent, text=text, variable=var, bg=PANEL, fg=TEXT, selectcolor=PANEL2,
                              activebackground=PANEL, activeforeground=ACCENT, disabledforeground=DIM,
                              font=(FAM, 10), anchor="w", highlightthickness=0, bd=0)

    def radio(parent, text, var, value, cmd=None):
        return tk.Radiobutton(parent, text=text, variable=var, value=value, command=cmd, bg=PANEL, fg=TEXT,
                              selectcolor=PANEL2, activebackground=PANEL, activeforeground=ACCENT,
                              disabledforeground=DIM, font=(FAM, 10), anchor="w", highlightthickness=0, bd=0)

    def combo(parent, values, var, width=16):
        cb = ttk.Combobox(parent, state="readonly", style="SHB.TCombobox", width=width, values=values)
        cb.current(values.index(var.get()) if var.get() in values else 0)
        return cb

    def emblem(canvas, cx, cy, size):
        """Three golden triangles: the pack's emblem (no game assets or text)."""
        h = size * 0.866
        for dx, dy in ((0, -h / 2), (-size / 2, h / 2), (size / 2, h / 2)):
            x, y = cx + dx, cy + dy
            canvas.create_polygon(x, y - h / 2, x - size / 2, y + h / 2, x + size / 2, y + h / 2,
                                  fill=ACCENT, outline="#f1d27a", width=1)

    # ---- profile handling ----
    def profile_name(key):
        return L("profile_custom") if key == "custom" else L("p_" + key.replace("-", "_"))

    def apply_profile(key, save=True):
        if key == "custom":
            refresh()
            return
        v = profile_values(key)
        guard["on"] = True
        profile.set(key)
        bmap.set(v["button_mapping"])
        stamina.set(v["stamina"])
        songbook.set(v["songbook"])
        hud_collectibles.set(v["hud_collectibles"])
        mode.set(STAMINA_MODES[v["mode"]])
        for k, val in zip(KEYS, v["costs"]):
            costs[k].set(val)
        combat.set(v["combat_only"])
        hp.set(v["enemy_hp"])
        dmg.set(v["damage"])
        nodrop.set(v["no_heart_drop"])
        speed.set(v["sprint_speed"])
        rupees.set(v["hud_rupees"])
        clock_mode.set("24" if v["clock_24h"] else "12" if v["hud_clock"] else "off")
        enemy_double.set(v["enemy_double"])
        enemy_speed.set(v["enemy_speed"])
        great_fairy.set(v["great_fairy"])
        farore_outdoor.set(v["farore_outdoor"])
        guard["on"] = False
        refresh()
        if save:
            autosave()

    def choose_profile(key):
        if key == "custom":
            profile.set("custom")
            refresh()
            autosave()
        else:
            apply_profile(key)

    def on_setting_change(*_):
        if guard["on"]:
            return
        if profile.get() != "custom":
            guard["on"] = True
            profile.set("custom")
            guard["on"] = False
        refresh()
        autosave()

    for var in (bmap, stamina, songbook, hud_collectibles,
                enemy_double, enemy_speed,
                great_fairy, farore_outdoor, mode,
                combat, hp, dmg, speed, nodrop,
                rupees, clock_mode, *costs.values()):
        var.trace_add("write", on_setting_change)

    def on_mode_change(*_):
        """When a named stamina style is chosen, show what it does in the checkbox list."""
        if guard["on"]:
            return
        view = I.PRESET_VIEW.get(STAMINA_MODES.index(mode.get()))
        if view is not None:
            guard["on"] = True
            for k in KEYS:
                costs[k].set(bool(view[k]))
            combat.set(bool(view["combat_only"]))
            guard["on"] = False
        refresh()
        autosave()

    mode.trace_add("write", on_mode_change)

    def on_pref_change(*_):   # button style / layout / L mode: no profile change
        refresh()
        autosave()

    for var in (bstyle, bsimple, blmode):
        var.trace_add("write", on_pref_change)

    pending = {"id": None}

    def autosave(*_):
        if pending["id"]:
            root.after_cancel(pending["id"])
        pending["id"] = root.after(250, remember)

    def settings():
        return I.Settings(button_mapping=bmap.get(), button_style=bstyle.get(), bm_simple=bsimple.get(),
                          bm_l_mode=blmode.get(), stamina=stamina.get(), songbook=songbook.get(),
                          hud_collectibles=hud_collectibles.get(),
                          enemy_double=enemy_double.get(), enemy_speed=enemy_speed.get(),
                          great_fairy=great_fairy.get(), farore_outdoor=farore_outdoor.get(),
                          preset=STAMINA_MODES.index(mode.get()),
                          combat_only=combat.get(),
                          **{k: costs[k].get() for k in KEYS},
                          enemy_hp=hp.get(), damage=dmg.get(), no_heart_drop=nodrop.get(),
                          sprint_speed=speed.get(), hud_rupees=rupees.get(),
                          hud_clock=clock_mode.get() != "off", clock_24h=clock_mode.get() == "24")

    def remember():
        return save_cfg({
            "lang": lang.get(), "emu": emu.get(), "profile": profile.get(),
            "button_mapping": bmap.get(), "button_style": bstyle.get(), "bm_simple": bsimple.get(),
            "bm_l_mode": blmode.get(),
            "stamina": stamina.get(), "songbook": songbook.get(),
            "hud_collectibles": hud_collectibles.get(),
            "enemy_double": enemy_double.get(), "enemy_speed": enemy_speed.get(),
            "great_fairy": great_fairy.get(), "farore_outdoor": farore_outdoor.get(),
            "stamina_mode": mode.get(),
            "costs": {**{k: costs[k].get() for k in KEYS}, "combat_only": combat.get()},
            "combat_only": combat.get(),
            "enemy_hp": hp.get(), "damage": dmg.get(), "no_heart_drop": nodrop.get(),
            "sprint_speed": speed.get(), "hud_rupees": rupees.get(),
            "clock_mode": clock_mode.get(),
            "hud_clock": clock_mode.get() != "off", "clock_24h": clock_mode.get() == "24",
        })

    def ok_emu():
        e = emu.get().strip()
        return I.find_mods_dir(Path(e).expanduser()) if e else None

    # ---- actions ----
    def browse():
        d = filedialog.askdirectory(title=L("emu_hint"))
        if d:
            emu.set(d)

    def do_install():
        try:
            status.set(L("working"))
            root.update_idletasks()
            r = I.install(Path(emu.get().strip()).expanduser(), settings())
            remember()
            msg = L("done_msg", n=r.target.name)
            for k, arg in r.notes:
                msg += "\n\n" + L("n_" + k, a=arg)
            status.set(L("ready"))
            messagebox.showinfo(L("done_title"), msg)
        except I.InstallError as ex:
            status.set("")
            messagebox.showerror(L("err_title"), L("e_" + ex.key, a=ex.arg))
        except Exception as ex:
            status.set("")
            messagebox.showerror(L("err_title"), str(ex))

    def do_remove():
        e = emu.get().strip()
        status.set(L("uninstalled") if e and I.uninstall(Path(e).expanduser()) else L("nothing"))

    def refresh(*_):
        if not ui["sections"]:
            return
        stam = stamina.get()
        adv = stam and mode.get() == "advanced"
        for w in ui.get("modes", []):
            w.config(state="normal" if stam else "disabled")
        for w in ui.get("costs", []):
            w.config(state="normal" if adv else "disabled")
        for key in ("combat", "sprint"):
            w = ui.get(key)
            if w is not None:
                w.config(state="normal" if stam else "disabled")
        on = bmap.get()
        if "variant" in ui:
            ui["variant"].config(state="readonly" if on else "disabled")
        for w in ui.get("bm", []):
            w.config(state="normal" if on else "disabled")
        ui["note"].config(text="" if stam else L("stamina_off_note"), fg=AMBER)
        mods = ok_emu()
        ui["install"].config(state="normal" if mods else "disabled")
        ui["mods"].config(text=L("mods_found", a=mods) if mods else L("mods_missing"),
                          fg=ACCENT if mods else DIM)
        if not mods and not status.get():
            status.set(L("pick_emu"))
        if mods and status.get() == L("pick_emu"):
            status.set("")
        token = profile.get().replace("-", "_")
        ui["profile_desc"].config(text=L("p_" + token + "_d") if profile.get() in PROFILES
                                  else L("p_custom_d"))
        ui["profile_badge"].config(text=L("profile_current", a=profile_name(profile.get())),
                                   fg=AMBER if profile.get() == "custom" else ACCENT)
        ui["reapply"].config(state="normal" if profile.get() != "custom" else "disabled")
        # Keep the comboboxes in sync with the model, so a profile changes every visible control.
        for cb, var, svar, names, choices in ui.get("mult", []):
            idx = choices.index(var.get()) if var.get() in choices else 0
            svar.set(names[idx])
            cb.current(idx)
        if "sprint" in ui:
            idx = SPEEDS.index(speed.get()) if speed.get() in SPEEDS else 0
            ui["sprint_var"].set(ui["sprint_values"][idx])
            ui["sprint"].current(idx)
        if "variant" in ui:
            idx = I.BUTTON_STYLES.index(bstyle.get()) if bstyle.get() in I.BUTTON_STYLES else 0
            ui["variant_var"].set(ui["variant_values"][idx])
            ui["variant"].current(idx)
        if "clock" in ui:
            idx = CLOCK_MODES.index(clock_mode.get()) if clock_mode.get() in CLOCK_MODES else 0
            ui["clock_var"].set(ui["clock_values"][idx])
            ui["clock"].current(idx)

    # ---- sections ----
    def build_install(parent):
        body = card(parent, L("home_title"), L("home_desc"))
        ui["profile_desc"] = label(body, "", size=10, color=AMBER, bold=True, bg=PANEL)
        ui["profile_desc"].pack(anchor="w", pady=(0, 5))
        prof = tk.Frame(body, bg=PANEL)
        prof.pack(fill="x")
        for i, key in enumerate(PROFILE_KEYS):
            r = radio(prof, profile_name(key), profile, key, cmd=lambda k=key: choose_profile(k))
            r.grid(row=i, column=0, sticky="w", pady=1)
            label(prof, L("p_" + key.replace("-", "_") + "_d"), size=9, color=DIM, bg=PANEL).grid(
                row=i, column=1, sticky="w", padx=(10, 0), pady=1)
        ui["reapply"] = button(body, L("reapply"), lambda: apply_profile(profile.get()))
        ui["reapply"].pack(anchor="w", pady=(8, 0))

        body = card(parent, L("install_title"), L("install_desc"))
        row = tk.Frame(body, bg=PANEL)
        row.pack(fill="x")
        entry = tk.Entry(row, textvariable=emu, bg=PANEL2, fg=TEXT, insertbackground=ACCENT, relief="flat",
                         font=(FAM, 10), highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=ACCENT)
        entry.pack(side="left", fill="x", expand=True, ipady=4)
        button(row, L("browse"), browse).pack(side="left", padx=(8, 0))
        label(body, L("emu_hint"), size=9, color=DIM, bg=PANEL).pack(anchor="w", pady=(5, 0))
        ui["mods"] = label(body, "", size=9, color=DIM, bg=PANEL)
        ui["mods"].pack(anchor="w", pady=(2, 0))
        label(body, L("install_hint"), size=9, color=AMBER, bg=PANEL).pack(anchor="w", pady=(6, 0))
        label(body, L("autosave"), size=9, color=DIM, bg=PANEL).pack(anchor="w", pady=(2, 0))

    def build_stamina(parent):
        body = card(parent, L("stamina_title"), L("stamina_desc"))
        check(body, L("stamina_on"), stamina).pack(anchor="w")
        label(body, L("stamina_on_desc"), size=9, color=DIM, bg=PANEL).pack(anchor="w", padx=(20, 0))
        ui["note"] = label(parent, "", size=9, color=AMBER, bg=BG, wrap=760)
        ui["note"].pack(anchor="w", padx=10, pady=(0, 6))

        body = card(parent, L("stamina_mode"))
        ui["modes"] = []
        for name in STAMINA_MODES:
            r = radio(body, L("m_" + name), mode, name)
            r.pack(anchor="w")
            ui["modes"].append(r)
            label(body, L("m_" + name + "_d"), size=9, color=DIM, bg=PANEL).pack(anchor="w", padx=(20, 0), pady=(0, 3))

        body = card(parent, L("costs_title"), L("costs_desc"))
        grid = tk.Frame(body, bg=PANEL)
        grid.pack(fill="x")
        ui["costs"] = []
        for i, k in enumerate(KEYS):
            c = check(grid, L("a_" + k), costs[k])
            c.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 28), pady=1)
            ui["costs"].append(c)
        ui["combat"] = check(body, L("combat_only"), combat)
        ui["combat"].pack(anchor="w", pady=(6, 0))

        body = card(parent, L("sprint_speed"))
        row = tk.Frame(body, bg=PANEL)
        row.pack(fill="x")
        label(row, L("sprint_speed") + ":", size=10, bg=PANEL).pack(side="left", padx=(0, 8))
        values = [L("speed_van")] + ["×%g" % (v / 100) for v in SPEEDS[1:]]
        svar = tk.StringVar(value=values[SPEEDS.index(speed.get())])
        ui["sprint_var"] = svar
        ui["sprint_values"] = values
        cb = combo(row, values, svar, width=14)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: speed.set(SPEEDS[cb.current()]))
        ui["sprint"] = cb

    def build_difficulty(parent):
        body = card(parent, L("difficulty_title"), L("difficulty_desc"))
        row = tk.Frame(body, bg=PANEL)
        row.pack(fill="x")
        names = [L("mult_van"), L("mult_15"), L("mult_2"), L("mult_3")]
        ui["mult"] = []
        for n, (lab, var) in enumerate(((L("enemy_hp"), hp), (L("damage"), dmg))):
            label(row, lab + ":", size=10, bg=PANEL).grid(row=0, column=n * 2, sticky="w", padx=(0, 6))
            svar = tk.StringVar(value=names[MULT.index(var.get())])
            cb = combo(row, names, svar, width=14)
            cb.grid(row=0, column=n * 2 + 1, padx=(0, 24))
            cb.bind("<<ComboboxSelected>>", lambda e, c=cb, v=var: v.set(MULT[c.current()]))
            ui["mult"].append((cb, var, svar, names, MULT))
        c = check(body, L("no_heart_drop"), nodrop)
        c.pack(anchor="w", pady=(10, 0))
        label(body, L("no_heart_drop_desc"), size=9, color=DIM, bg=PANEL).pack(anchor="w", padx=(20, 0))
        label(body, L("difficulty_note"), size=9, color=DIM, bg=PANEL).pack(anchor="w", pady=(8, 0))

    def build_hud(parent):
        body = card(parent, L("hud_title"), L("hud_desc"))
        row = tk.Frame(body, bg=PANEL)
        row.pack(fill="x")
        check(row, L("hud_rupees"), rupees).grid(row=0, column=0, sticky="w", padx=(0, 30))
        label(row, L("clock_mode") + ":", size=10, bg=PANEL).grid(row=0, column=1, sticky="w", padx=(0, 6))
        values = [L("clock_off"), L("clock_12"), L("clock_24")]
        cvar = tk.StringVar(value=values[CLOCK_MODES.index(clock_mode.get())])
        cb = combo(row, values, cvar, width=18)
        cb.grid(row=0, column=2, sticky="w")
        cb.bind("<<ComboboxSelected>>", lambda e: clock_mode.set(CLOCK_MODES[cb.current()]))
        ui["clock"] = cb
        ui["clock_var"] = cvar
        ui["clock_values"] = values
        check(body, L("hud_collectibles"), hud_collectibles).pack(anchor="w", pady=(8, 0))
        label(body, L("hud_collectibles_desc"), size=9, color=DIM, bg=PANEL).pack(anchor="w", padx=(20, 0))
        label(body, L("hud_note"), size=9, color=DIM, bg=PANEL).pack(anchor="w", pady=(8, 0))
        build_buttons(parent)

    def build_buttons(parent):
        body = card(parent, L("buttons_title"), L("buttons_desc"))
        check(body, L("bm_on"), bmap).pack(anchor="w")
        label(body, L("bm_on_desc"), size=9, color=DIM, bg=PANEL).pack(anchor="w", padx=(20, 0))
        ui["bm"] = []
        row = tk.Frame(body, bg=PANEL)
        row.pack(anchor="w", pady=(10, 0))
        label(row, L("variant") + ":", size=10, bg=PANEL).pack(side="left", padx=(0, 8))
        style_names = {"switch": "g_default", "playstation": "g_playstation", "xbox": "g_xbox"}
        names = [L(style_names[k]) for k in I.BUTTON_STYLES]
        vvar = tk.StringVar(value=names[I.BUTTON_STYLES.index(bstyle.get())])
        ui["variant_var"] = vvar
        ui["variant_values"] = names
        cb = combo(row, names, vvar, width=16)
        cb.pack(side="left")
        cb.bind("<<ComboboxSelected>>", lambda e: bstyle.set(I.BUTTON_STYLES[cb.current()]))
        ui["variant"] = cb

        label(body, L("bm_layout"), size=10, color=ACCENT, bold=True, bg=PANEL).pack(anchor="w", pady=(10, 0))
        for value, key in ((False, "bm_ext"), (True, "bm_simple")):
            r = radio(body, L(key), bsimple, value)
            r.pack(anchor="w")
            ui["bm"].append(r)
            label(body, L(key + "_d"), size=9, color=DIM, bg=PANEL).pack(anchor="w", padx=(20, 0))

        label(body, L("bm_l"), size=10, color=ACCENT, bold=True, bg=PANEL).pack(anchor="w", pady=(10, 0))
        for value in I.L_MODES:
            r = radio(body, L("bm_l_" + value), blmode, value)
            r.pack(anchor="w")
            ui["bm"].append(r)
            label(body, L("bm_l_" + value + "_d"), size=9, color=DIM, bg=PANEL).pack(anchor="w", padx=(20, 0))
        label(body, L("bm_note"), size=9, color=AMBER, bg=PANEL).pack(anchor="w", pady=(8, 0))

    def build_misc(parent):
        body = card(parent, L("misc_title"), L("misc_desc"))
        label(body, L("songbook_title"), size=11, color=ACCENT, bold=True, bg=PANEL).pack(anchor="w", pady=(2, 0))
        check(body, L("songbook_on"), songbook).pack(anchor="w", pady=(2, 0))
        label(body, L("songbook_desc"), size=9, color=DIM, bg=PANEL).pack(anchor="w", padx=(20, 0))
        label(body, L("songbook_note"), size=9, color=AMBER, bg=PANEL).pack(anchor="w", pady=(8, 0))

        body = card(parent, L("beta_title"), L("beta_desc"))
        label(body, L("beta_warning"), size=9, color=RED, bold=True, bg=PANEL).pack(anchor="w", pady=(0, 6))
        label(body, L("enemy_double"), size=10, color=ACCENT, bold=True, bg=PANEL).pack(anchor="w")
        check(body, L("enemy_double_on"), enemy_double).pack(anchor="w", padx=(0, 0))
        label(body, L("enemy_double_desc"), size=9, color=DIM, bg=PANEL).pack(anchor="w", padx=(20, 0), pady=(0, 8))
        label(body, L("enemy_speed"), size=10, color=ACCENT, bold=True, bg=PANEL).pack(anchor="w")
        check(body, L("enemy_speed_on"), enemy_speed).pack(anchor="w", padx=(0, 0))
        label(body, L("enemy_speed_desc"), size=9, color=DIM, bg=PANEL).pack(anchor="w", padx=(20, 0))
        label(body, L("enemy_beta_note"), size=9, color=AMBER, bg=PANEL).pack(anchor="w", pady=(8, 0))

        body = card(parent, L("world_beta_title"), L("world_beta_desc"))
        label(body, L("great_fairy"), size=10, color=ACCENT, bold=True, bg=PANEL).pack(anchor="w")
        check(body, L("great_fairy_on"), great_fairy).pack(anchor="w")
        label(body, L("great_fairy_desc"), size=9, color=DIM, bg=PANEL).pack(anchor="w", padx=(20, 0), pady=(0, 8))
        label(body, L("farore"), size=10, color=ACCENT, bold=True, bg=PANEL).pack(anchor="w")
        check(body, L("farore_on"), farore_outdoor).pack(anchor="w")
        label(body, L("farore_desc"), size=9, color=DIM, bg=PANEL).pack(anchor="w", padx=(20, 0))
        label(body, L("farore_note"), size=9, color=AMBER, bg=PANEL).pack(anchor="w", padx=(20, 0), pady=(4, 0))

    def open_github():
        import webbrowser
        webbrowser.open("https://github.com/kuribox/OOT-SuperHeroBoostMod")

    def build_about(parent):
        body = card(parent, L("about_title"))
        label(body, L("about_body"), size=10, bg=PANEL).pack(anchor="w")
        link = tk.Label(body, text=L("about_link"), bg=PANEL, fg=ACCENT, cursor="hand2",
                        font=(FAM, 9, "underline"), anchor="w", justify="left")
        link.pack(anchor="w", pady=(8, 0))
        link.bind("<Button-1>", lambda e: open_github())
        label(body, L("audit"), size=9, color=DIM, bg=PANEL).pack(anchor="w", pady=(6, 0))

    # ---- shell ----
    def build_header(shell):
        hd = tk.Frame(shell, bg=BG)
        hd.pack(fill="x", padx=18, pady=(14, 8))
        left = tk.Frame(hd, bg=BG)
        left.pack(side="left", fill="x", expand=True)
        brand = tk.Frame(left, bg=BG)
        brand.pack(anchor="w")
        logo = tk.Canvas(brand, width=58, height=48, bg=BG, highlightthickness=0)
        logo.pack(side="left", padx=(0, 12))
        emblem(logo, 29, 25, 30)
        names = tk.Frame(brand, bg=BG)
        names.pack(side="left")
        tk.Label(names, text="Super Hero Boost", bg=BG, fg=ACCENT, font=(DISPLAY, 24, "bold")).pack(anchor="w")
        tk.Label(names, text=L("subtitle"), bg=BG, fg=DIM, font=(FAM, 10)).pack(anchor="w")
        right = tk.Frame(hd, bg=BG)
        right.pack(side="right")
        ui["profile_badge"] = tk.Label(right, text="", bg=BG, fg=ACCENT, font=(FAM, 10, "bold"))
        ui["profile_badge"].grid(row=0, column=0, sticky="e", padx=(0, 18))
        tk.Label(right, text=L("language"), bg=BG, fg=DIM, font=(FAM, 9)).grid(row=0, column=1, sticky="e", padx=(0, 6))
        lcb = ttk.Combobox(right, state="readonly", style="SHB.TCombobox", width=12, values=list(LANGS.values()))
        lcb.current(list(LANGS).index(lang.get()) if lang.get() in LANGS else 0)
        lcb.grid(row=0, column=2)
        lcb.bind("<<ComboboxSelected>>", lambda e: change_lang(list(LANGS)[lcb.current()]))

    def change_lang(code):
        lang.set(code)
        remember()
        render()

    def build_sidebar(shell):
        side = tk.Frame(shell, bg=SIDEBAR, width=190)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        for key, text in (("install", "nav_install"), ("stamina", "nav_stamina"),
                          ("difficulty", "nav_difficulty"), ("hud", "nav_hud"),
                          ("misc", "nav_misc"), ("about", "nav_about")):
            b = tk.Button(side, text=L(text), command=lambda k=key: show_section(k), anchor="w",
                          bg=SIDEBAR, fg=TEXT, activebackground=PANEL, activeforeground=ACCENT,
                          relief="flat", bd=0, cursor="hand2", font=(FAM, 10, "bold"),
                          padx=18, pady=10, highlightthickness=0)
            b.pack(fill="x", pady=1)
            ui["nav"][key] = b
        return side

    def build_content(shell):
        wrap = tk.Frame(shell, bg=BG)
        wrap.pack(side="left", fill="both", expand=True, padx=(12, 12), pady=(0, 8))
        scroll = ScrollArea(wrap, BG)
        scroll.frame.pack(fill="both", expand=True)
        builders = {"install": build_install, "stamina": build_stamina, "difficulty": build_difficulty,
                    "hud": build_hud, "misc": build_misc, "about": build_about}
        for key, fn in builders.items():
            f = tk.Frame(scroll.inner, bg=BG)
            fn(f)
            ui["sections"][key] = f
        ui["_scroll"] = scroll
        return scroll

    def build_footer(shell):
        ft = tk.Frame(shell, bg=BG)
        ft.pack(side="bottom", fill="x", padx=18, pady=(0, 12))
        tk.Label(ft, textvariable=status, bg=BG, fg=ACCENT, font=(FAM, 9, "italic"), anchor="w").pack(side="left")
        ui["install"] = button(ft, L("install"), do_install, primary=True)
        ui["install"].pack(side="right")
        button(ft, L("uninstall"), do_remove).pack(side="right", padx=(0, 8))
        ui["install"].config(state="normal" if ok_emu() else "disabled")

    def show_section(key):
        state["section"] = key
        for k, f in ui["sections"].items():
            f.pack_forget()
        ui["sections"][key].pack(fill="x", padx=4, pady=(4, 0))
        ui["_scroll"].refresh()
        ui["_scroll"].canvas.yview_moveto(0)
        for k, b in ui["nav"].items():
            b.config(bg=PANEL if k == key else SIDEBAR, fg=ACCENT if k == key else TEXT)

    def render():
        old = ui.get("_scroll")
        if old is not None:
            old.destroy()
        for w in root.winfo_children():
            w.destroy()
        ui["nav"] = {}
        ui["sections"] = {}
        shell = tk.Frame(root, bg=BG)
        shell.pack(fill="both", expand=True)
        build_header(shell)
        build_footer(shell)
        body = tk.Frame(shell, bg=BG)
        body.pack(side="top", fill="both", expand=True)
        build_sidebar(body)
        build_content(body)
        show_section(state["section"])
        refresh()

    # New installations start from the flagship profile; saved/legacy settings keep their values.
    if not cfg:
        profile.set(DEFAULT_PROFILE)
        apply_profile(DEFAULT_PROFILE, save=False)
    elif "profile" not in cfg:
        profile.set("custom")
    elif profile.get() != "custom":
        apply_profile(profile.get(), save=False)

    for v in (emu, bmap, bstyle, bsimple, blmode, stamina, songbook, hud_collectibles,
              enemy_double,
              enemy_speed, great_fairy, farore_outdoor, mode, combat, hp, dmg, speed,
              nodrop, rupees, clock_mode, *costs.values()):
        v.trace_add("write", autosave)
    emu.trace_add("write", lambda *_: (status.set(""), refresh()))

    render()
    root.protocol("WM_DELETE_WINDOW", lambda: (remember(), root.destroy()))
    root.mainloop()


if __name__ == "__main__":
    if any(a in sys.argv for a in ("--cli", "--list-profiles", "-h", "--help")):
        raise SystemExit(cli(sys.argv[1:]))
    gui()
