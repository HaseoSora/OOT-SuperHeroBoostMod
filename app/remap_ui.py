"""Button remap editor (buttonMapping): what each of the eight buttons does, with a live preview.

The module side is core/remap.h: every physical button gets a role (jump, sword, action, target, item 1..3, the
game's own item, or nothing). This page edits that table and draws two previews from it:
  * the controller, with the chosen button style's glyphs where each button sits, and its role;
  * the in-game HUD cluster, the way core/hud.c draws it (same coordinates, same pad layout rule).

Its texts live here and are merged into the app's tables on import, so the page is self-contained.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import installer as I
from i18n import T

# ---------------------------------------------------------------- texts
_TXT = {
    "en": dict(
        rm_title="Button remap",
        rm_on="Choose what each button does",
        rm_on_desc="Pick an action for X, Y, A, B, L, R, ZL and ZR. The HUD buttons move with them. Off: the classic "
                   "layout (X jump, Y sword, A action, ZL target, B / L / R items, ZR the game's item).",
        rm_reset="Classic layout",
        rm_items="Item buttons: {n} / 4",
        rm_missing="No button for: {a}. The game cannot do that while you play.",
        rm_no_main="No button for the main item: the item you pick with A in the pause menu cannot be used.",
        rm_menu="Pause menu, Items tab: assign with {a}.",
        rm_pad="Your controller",
        rm_hud="In game",
        rm_target_note="Target has no HUD button (as before).",
        rm_swap_note="Only while you play: menus, the ocarina and dialogue choices keep the real buttons, as the "
                     "game's own prompts name them.",
        role_none="Nothing",
        role_jump="Jump",
        role_sword="Sword",
        role_action="Action (talk, open, roll)",
        role_target="Target",
        role_target_ms="Guard (manual shield)",
        role_item1="Item 1",
        role_item2="Item 2",
        role_item2_ms="Target on / off (manual shield)",
        role_item2_sel="Item selector",
        role_item3="Item 3",
        role_item_main="Main item (the game's)",
        short_none="—", short_jump="Jump", short_sword="Sword", short_action="Action", short_target="Target",
        short_target_ms="Guard", short_item1="Item 1", short_item2="Item 2", short_item2_ms="Target",
        short_item2_sel="Selector", short_item3="Item 3", short_item_main="Main item",
    ),
    "es": dict(
        rm_title="Reasignar botones",
        rm_on="Elegir qué hace cada botón",
        rm_on_desc="Elige una acción para X, Y, A, B, L, R, ZL y ZR. Los botones del HUD se mueven con ellos. "
                   "Desactivado: la distribución clásica (X saltar, Y espada, A acción, ZL fijar, B / L / R objetos, "
                   "ZR el objeto del juego).",
        rm_reset="Distribución clásica",
        rm_items="Botones de objeto: {n} / 4",
        rm_missing="Ningún botón para: {a}. El juego no podrá hacerlo mientras juegas.",
        rm_no_main="Ningún botón para el objeto principal: el objeto que eliges con A en el menú de pausa no se podrá "
                   "usar.",
        rm_menu="Menú de pausa, pestaña Objetos: se asigna con {a}.",
        rm_pad="Tu mando",
        rm_hud="En el juego",
        rm_target_note="Fijar objetivo no tiene botón en el HUD (como antes).",
        rm_swap_note="Solo mientras juegas: los menús, la ocarina y las elecciones de diálogo usan los botones reales, "
                     "como los nombra el propio juego.",
        role_none="Nada",
        role_jump="Saltar",
        role_sword="Espada",
        role_action="Acción (hablar, abrir, rodar)",
        role_target="Fijar objetivo",
        role_target_ms="Guardia (escudo manual)",
        role_item1="Objeto 1",
        role_item2="Objeto 2",
        role_item2_ms="Fijar sí / no (escudo manual)",
        role_item2_sel="Selector de objetos",
        role_item3="Objeto 3",
        role_item_main="Objeto principal (el del juego)",
        short_none="—", short_jump="Saltar", short_sword="Espada", short_action="Acción", short_target="Fijar",
        short_target_ms="Guardia", short_item1="Objeto 1", short_item2="Objeto 2", short_item2_ms="Fijar",
        short_item2_sel="Selector", short_item3="Objeto 3", short_item_main="Principal",
    ),
    "pt": dict(
        rm_title="Remapear botões",
        rm_on="Escolher o que cada botão faz",
        rm_on_desc="Escolha uma ação para X, Y, A, B, L, R, ZL e ZR. Os botões do HUD acompanham. Desligado: o layout "
                   "clássico (X pular, Y espada, A ação, ZL mirar, B / L / R itens, ZR o item do jogo).",
        rm_reset="Layout clássico",
        rm_items="Botões de item: {n} / 4",
        rm_missing="Nenhum botão para: {a}. O jogo não poderá fazer isso enquanto joga.",
        rm_no_main="Nenhum botão para o item principal: o item escolhido com A no menu de pausa não poderá ser usado.",
        rm_menu="Menu de pausa, aba Itens: atribua com {a}.",
        rm_pad="Seu controle",
        rm_hud="No jogo",
        rm_target_note="Mirar não tem botão no HUD (como antes).",
        rm_swap_note="Só enquanto joga: menus, a ocarina e escolhas de diálogo usam os botões reais, como o próprio "
                     "jogo os mostra.",
        role_none="Nada", role_jump="Pular", role_sword="Espada", role_action="Ação (falar, abrir, rolar)",
        role_target="Mirar", role_target_ms="Defesa (escudo manual)", role_item1="Item 1", role_item2="Item 2",
        role_item2_ms="Mirar liga / desliga (escudo manual)", role_item2_sel="Seletor de itens", role_item3="Item 3",
        role_item_main="Item principal (o do jogo)",
        short_none="—", short_jump="Pular", short_sword="Espada", short_action="Ação", short_target="Mirar",
        short_target_ms="Defesa", short_item1="Item 1", short_item2="Item 2", short_item2_ms="Mirar",
        short_item2_sel="Seletor", short_item3="Item 3", short_item_main="Principal",
    ),
    "fr": dict(
        rm_title="Réassigner les boutons",
        rm_on="Choisir l'action de chaque bouton",
        rm_on_desc="Choisissez une action pour X, Y, A, B, L, R, ZL et ZR. Les boutons du HUD suivent. Désactivé : la "
                   "disposition classique (X sauter, Y épée, A action, ZL cibler, B / L / R objets, ZR l'objet du jeu).",
        rm_reset="Disposition classique",
        rm_items="Boutons d'objet : {n} / 4",
        rm_missing="Aucun bouton pour : {a}. Le jeu ne pourra pas le faire pendant que vous jouez.",
        rm_no_main="Aucun bouton pour l'objet principal : l'objet choisi avec A dans le menu pause ne pourra pas "
                   "servir.",
        rm_menu="Menu pause, onglet Objets : assignez avec {a}.",
        rm_pad="Votre manette",
        rm_hud="En jeu",
        rm_target_note="Cibler n'a pas de bouton dans le HUD (comme avant).",
        rm_swap_note="Seulement en jeu : les menus, l'ocarina et les choix de dialogue gardent les vrais boutons, comme "
                     "le jeu les affiche.",
        role_none="Rien", role_jump="Sauter", role_sword="Épée", role_action="Action (parler, ouvrir, rouler)",
        role_target="Cibler", role_target_ms="Garde (bouclier manuel)", role_item1="Objet 1", role_item2="Objet 2",
        role_item2_ms="Cibler oui / non (bouclier manuel)", role_item2_sel="Sélecteur d'objets", role_item3="Objet 3",
        role_item_main="Objet principal (celui du jeu)",
        short_none="—", short_jump="Sauter", short_sword="Épée", short_action="Action", short_target="Cibler",
        short_target_ms="Garde", short_item1="Objet 1", short_item2="Objet 2", short_item2_ms="Cibler",
        short_item2_sel="Sélecteur", short_item3="Objet 3", short_item_main="Principal",
    ),
    "de": dict(
        rm_title="Tasten neu belegen",
        rm_on="Festlegen, was jede Taste tut",
        rm_on_desc="Wähle eine Aktion für X, Y, A, B, L, R, ZL und ZR. Die HUD-Tasten wandern mit. Aus: die klassische "
                   "Belegung (X springen, Y Schwert, A Aktion, ZL anvisieren, B / L / R Items, ZR das Item des Spiels).",
        rm_reset="Klassische Belegung",
        rm_items="Item-Tasten: {n} / 4",
        rm_missing="Keine Taste für: {a}. Das Spiel kann das beim Spielen nicht.",
        rm_no_main="Keine Taste für das Haupt-Item: das mit A im Pausemenü gewählte Item kann nicht benutzt werden.",
        rm_menu="Pausemenü, Reiter Items: zuweisen mit {a}.",
        rm_pad="Dein Controller",
        rm_hud="Im Spiel",
        rm_target_note="Anvisieren hat keine HUD-Taste (wie bisher).",
        rm_swap_note="Nur beim Spielen: Menüs, die Okarina und Dialogauswahl nutzen die echten Tasten, wie das Spiel "
                     "sie anzeigt.",
        role_none="Nichts", role_jump="Springen", role_sword="Schwert", role_action="Aktion (reden, öffnen, rollen)",
        role_target="Anvisieren", role_target_ms="Abwehr (manueller Schild)", role_item1="Item 1", role_item2="Item 2",
        role_item2_ms="Anvisieren an / aus (manueller Schild)", role_item2_sel="Item-Auswahl", role_item3="Item 3",
        role_item_main="Haupt-Item (das des Spiels)",
        short_none="—", short_jump="Springen", short_sword="Schwert", short_action="Aktion", short_target="Visier",
        short_target_ms="Abwehr", short_item1="Item 1", short_item2="Item 2", short_item2_ms="Visier",
        short_item2_sel="Auswahl", short_item3="Item 3", short_item_main="Haupt",
    ),
    "it": dict(
        rm_title="Riassegna i tasti",
        rm_on="Scegli cosa fa ogni tasto",
        rm_on_desc="Scegli un'azione per X, Y, A, B, L, R, ZL e ZR. I tasti dell'HUD li seguono. Disattivato: lo schema "
                   "classico (X salto, Y spada, A azione, ZL mira, B / L / R oggetti, ZR l'oggetto del gioco).",
        rm_reset="Schema classico",
        rm_items="Tasti oggetto: {n} / 4",
        rm_missing="Nessun tasto per: {a}. Il gioco non potrà farlo mentre giochi.",
        rm_no_main="Nessun tasto per l'oggetto principale: l'oggetto scelto con A nel menu di pausa non si potrà usare.",
        rm_menu="Menu di pausa, scheda Oggetti: assegna con {a}.",
        rm_pad="Il tuo controller",
        rm_hud="In gioco",
        rm_target_note="La mira non ha un tasto nell'HUD (come prima).",
        rm_swap_note="Solo mentre giochi: menu, ocarina e scelte di dialogo usano i tasti reali, come li mostra il "
                     "gioco.",
        role_none="Niente", role_jump="Salto", role_sword="Spada", role_action="Azione (parlare, aprire, rotolare)",
        role_target="Mira", role_target_ms="Guardia (scudo manuale)", role_item1="Oggetto 1", role_item2="Oggetto 2",
        role_item2_ms="Mira sì / no (scudo manuale)", role_item2_sel="Selettore oggetti", role_item3="Oggetto 3",
        role_item_main="Oggetto principale (quello del gioco)",
        short_none="—", short_jump="Salto", short_sword="Spada", short_action="Azione", short_target="Mira",
        short_target_ms="Guardia", short_item1="Ogg. 1", short_item2="Ogg. 2", short_item2_ms="Mira",
        short_item2_sel="Selettore", short_item3="Ogg. 3", short_item_main="Principale",
    ),
}
for _lang, _t in _TXT.items():
    if _lang in T:
        T[_lang].update(_t)

# ---------------------------------------------------------------- model
# The order the editor lists the buttons in (face buttons, then shoulders). The module's order is I.REMAP_BUTTONS.
ROW_ORDER = ("X", "Y", "A", "B", "L", "R", "ZL", "ZR")
FACE = ("A", "B", "X", "Y")
# glyph drawn for each game button per button style (tools/make_buttons.py GLYPHS)
GLYPHS = {
    "switch": {b: b for b in I.REMAP_BUTTONS},
    "xbox": {"A": "B", "B": "A", "X": "Y", "Y": "X", "L": "LB", "R": "RB", "ZL": "LT", "ZR": "RT"},
    "playstation": {"A": "circle", "B": "cross", "X": "triangle", "Y": "square",
                    "L": "L1", "R": "R1", "ZL": "L2", "ZR": "R2"},
}
PS_COLORS = {"circle": "#e0605a", "cross": "#7aa6e8", "triangle": "#5fc7a0", "square": "#d98cc8"}
ITEM_MARK = {"item1": "1", "item2": "2", "item3": "3", "item_main": "★"}
# core/hud.c: where each button sits (layout units, y up); ZL mirrors ZR. Items sit up-left of their button.
HUD_POS = {"L": (1020.4, 872.3), "X": (1292.6, 843.0), "R": (1545.2, 872.3), "Y": (1129.6, 680.0),
           "A": (1455.6, 680.0), "ZR": (1677.2, 680.0), "B": (1292.6, 517.0), "ZL": (908.0, 680.0)}
HUD_SIMPLE = {"item2": (1120.4, 872.3), "item3": (1445.2, 872.3), "item_main": (1677.2, 680.0),
              "item1": (1292.6, 680.0)}
ITEM_OFF = (-25.3, 25.3)
ROLE_KIND = {"jump": "move", "sword": "move", "action": "move", "target": "move",
             "item1": "item", "item2": "item", "item3": "item", "item_main": "item", "none": "none"}


def face_place(btn: str, layout: str) -> str:
    """core/hud.c face_place(): where a face button is drawn for the recompilers' pad layout."""
    if layout in ("ab", "xbox") and btn in ("A", "B"):
        btn = "B" if btn == "A" else "A"
    if layout == "xbox" and btn in ("X", "Y"):
        btn = "Y" if btn == "X" else "X"
    return btn


def role_vars(saved, master=None) -> dict:
    roles = I.normalize_roles(saved if isinstance(saved, dict) else I.CLASSIC_ROLES)
    return {b: tk.StringVar(master=master, value=roles[b]) for b in I.REMAP_BUTTONS}


def roles_value(rvars: dict) -> dict:
    return I.normalize_roles({b: v.get() for b, v in rvars.items()})


def effective_roles(remap_on: bool, rvars: dict) -> dict:
    """What the module will use: the player's table, or the classic layout."""
    return roles_value(rvars) if remap_on else dict(I.CLASSIC_ROLES)


def menu_buttons(roles: dict) -> dict:
    """core/remap.c remap_menu_buttons(): the pause-menu button that assigns each of items 1..3."""
    phys = {r: b for b, r in roles.items() if r != "none"}
    out, taken = {}, set()
    for r in ("item1", "item2", "item3"):
        b = phys.get(r)
        if b in ("X", "Y", "L", "R") and b not in taken:
            out[r] = b
            taken.add(b)
    classic = {"item1": "X", "item2": "L", "item3": "R"}
    for r in ("item1", "item2", "item3"):
        if r in out or r not in phys:
            continue
        pick = classic[r]
        for cand in (classic[r], "X", "L", "R", "Y"):
            if cand not in taken:
                pick = cand
                break
        out[r] = pick
        taken.add(pick)
    return out


# ---------------------------------------------------------------- editor
class RemapEditor:
    """The remap card's body: one row per button (its glyph and a role list) and the two previews."""

    def __init__(self, parent, L, fam, colors, v):
        """v: dict of the app's variables: bmap, bremap, roles (dict), bstyle, bplace, bsimple, blmode, mshield."""
        self.L, self.fam, self.c, self.v = L, fam, colors, v
        self.combos: dict[str, ttk.Combobox] = {}
        self.chips: dict[str, tk.Canvas] = {}
        self._guard = False
        self._traces = []
        bg = colors["PANEL"]
        self.frame = tk.Frame(parent, bg=bg)
        self.frame.pack(fill="x", pady=(12, 0))

        tk.Label(self.frame, text=L("rm_title"), bg=bg, fg=colors["ACCENT"], font=(fam, 10, "bold"),
                 anchor="w").pack(anchor="w")
        self.chk = tk.Checkbutton(self.frame, text=L("rm_on"), variable=v["bremap"], bg=bg, fg=colors["TEXT"],
                                  selectcolor=colors["PANEL2"], activebackground=bg,
                                  activeforeground=colors["ACCENT"], disabledforeground=colors["DIM"],
                                  font=(fam, 10), anchor="w", highlightthickness=0, bd=0)
        self.chk.pack(anchor="w")
        tk.Label(self.frame, text=L("rm_on_desc"), bg=bg, fg=colors["DIM"], font=(fam, 9), justify="left",
                 anchor="w", wraplength=740).pack(anchor="w", padx=(20, 0))

        body = tk.Frame(self.frame, bg=bg)
        body.pack(anchor="w", fill="x", pady=(8, 0), padx=(20, 0))
        left = tk.Frame(body, bg=bg)
        left.pack(side="left", anchor="n")
        right = tk.Frame(body, bg=bg)
        right.pack(side="left", anchor="n", padx=(18, 0))

        for b in ROW_ORDER:
            row = tk.Frame(left, bg=bg)
            row.pack(anchor="w", pady=2)
            chip = tk.Canvas(row, width=40, height=30, bg=bg, highlightthickness=0)
            chip.pack(side="left")
            self.chips[b] = chip
            cb = ttk.Combobox(row, state="readonly", style="SHB.TCombobox", width=30)
            cb.pack(side="left", padx=(6, 0))
            cb.bind("<<ComboboxSelected>>", lambda e, btn=b: self._pick(btn))
            self.combos[b] = cb
        self.reset_btn = tk.Button(left, text=L("rm_reset"), command=self._reset, relief="flat", cursor="hand2",
                                   bg=colors["PANEL2"], fg=colors["TEXT"], activebackground=colors["BORDER"],
                                   activeforeground=colors["TEXT"], disabledforeground=colors["DIM"],
                                   highlightthickness=1, highlightbackground=colors["BORDER"], padx=12, pady=4,
                                   font=(fam, 9))
        self.reset_btn.pack(anchor="w", pady=(8, 0))
        self.count = tk.Label(left, text="", bg=bg, fg=colors["DIM"], font=(fam, 9), anchor="w")
        self.count.pack(anchor="w", pady=(6, 0))

        tk.Label(right, text=L("rm_pad"), bg=bg, fg=colors["DIM"], font=(fam, 9, "bold"),
                 anchor="w").pack(anchor="w")
        self.pad = tk.Canvas(right, width=430, height=230, bg=colors["PANEL2"], highlightthickness=1,
                             highlightbackground=colors["BORDER"])
        self.pad.pack(anchor="w")
        tk.Label(right, text=L("rm_hud"), bg=bg, fg=colors["DIM"], font=(fam, 9, "bold"),
                 anchor="w").pack(anchor="w", pady=(8, 0))
        self.hud = tk.Canvas(right, width=430, height=200, bg="#101010", highlightthickness=1,
                             highlightbackground=colors["BORDER"])
        self.hud.pack(anchor="w")

        self.notes = tk.Label(self.frame, text="", bg=bg, fg=colors["AMBER"], font=(fam, 9), justify="left",
                              anchor="w", wraplength=740)
        self.notes.pack(anchor="w", padx=(20, 0), pady=(8, 0))
        self.info = tk.Label(self.frame, text="", bg=bg, fg=colors["DIM"], font=(fam, 9), justify="left",
                             anchor="w", wraplength=740)
        self.info.pack(anchor="w", padx=(20, 0), pady=(2, 0))

        for key in ("bmap", "bremap", "bstyle", "bplace", "bsimple", "blmode", "mshield"):
            self._traces.append((v[key], v[key].trace_add("write", lambda *_: self.redraw())))
        for var in v["roles"].values():
            self._traces.append((var, var.trace_add("write", lambda *_: self.redraw())))
        self.frame.bind("<Destroy>", self._drop_traces)
        self.redraw()

    # ---- helpers ----
    def _drop_traces(self, _e=None):
        for var, tid in self._traces:
            try:
                var.trace_remove("write", tid)
            except (tk.TclError, ValueError):
                pass
        self._traces = []

    def _role_key(self, role: str) -> str:
        if role == "target" and self.v["mshield"].get():
            return "target_ms"
        if role == "item2" and self.v["blmode"].get() == "selector":
            return "item2_sel"
        if role == "item2" and self.v["mshield"].get():
            return "item2_ms"
        return role

    def role_name(self, role: str) -> str:
        return self.L("role_" + self._role_key(role))

    def role_short(self, role: str) -> str:
        return self.L("short_" + self._role_key(role))

    def _style(self) -> str:
        s = self.v["bstyle"].get()
        return s if s in GLYPHS else "switch"

    # ---- editing ----
    def _pick(self, btn: str):
        cb = self.combos[btn]
        new = I.ROLES[cb.current()]
        rv = self.v["roles"]
        old = rv[btn].get()
        if new == old:
            return
        self._guard = True
        if new != "none":   # each role on one button: the button that had it takes this one's old role
            for other, var in rv.items():
                if other != btn and var.get() == new:
                    var.set(old)
        rv[btn].set(new)
        self._guard = False
        self.redraw()

    def _reset(self):
        self._guard = True
        for b, var in self.v["roles"].items():
            var.set(I.CLASSIC_ROLES[b])
        self._guard = False
        self.redraw()

    # ---- drawing ----
    def redraw(self):
        if self._guard:
            return
        try:
            if not self.frame.winfo_exists():
                return
        except tk.TclError:
            return
        on, remap = self.v["bmap"].get(), self.v["bremap"].get()
        roles = effective_roles(remap, self.v["roles"])
        names = [self.role_name(r) for r in I.ROLES]
        editable = on and remap
        self.chk.config(state="normal" if on else "disabled")
        self.reset_btn.config(state="normal" if editable else "disabled")
        for b, cb in self.combos.items():
            cb.config(values=names, state="readonly" if editable else "disabled")
            cb.current(I.ROLES.index(roles[b]))
            self._chip(self.chips[b], 20, 15, b, 13)
        n_items = sum(1 for r in roles.values() if r in I.ITEM_ROLES)
        self.count.config(text=self.L("rm_items", n=n_items))
        notes = []
        missing = [self.role_short(r) for r in I.roles_missing(roles)]
        if missing:
            notes.append(self.L("rm_missing", a=", ".join(missing)))
        if "item_main" not in roles.values():
            notes.append(self.L("rm_no_main"))
        self.notes.config(text="\n".join(notes))
        mb = menu_buttons(roles)
        glyph = GLYPHS[self._style()]
        pairs = []
        for r in ("item1", "item2", "item3"):
            if r in mb and not (r == "item2" and (self.v["blmode"].get() == "selector" or self.v["mshield"].get())):
                dst = next(b for b, x in roles.items() if x == r)
                pairs.append(f"{self._glyph_text(glyph[mb[r]])} → {self.role_short(r)} "
                             f"({self._glyph_text(glyph[dst])})")
        if "item_main" in roles.values():
            dst = next(b for b, x in roles.items() if x == "item_main")
            pairs.append(f"{self._glyph_text(glyph['A'])} → {self.role_short('item_main')} "
                         f"({self._glyph_text(glyph[dst])})")
        info = [self.L("rm_menu", a=",  ".join(pairs))] if pairs else []
        if remap:
            info.append(self.L("rm_swap_note"))
        info.append(self.L("rm_target_note"))
        self.info.config(text="\n".join(info))
        self._draw_pad(roles)
        self._draw_hud(roles)

    @staticmethod
    def _glyph_text(g: str) -> str:
        return {"circle": "○", "cross": "✕", "triangle": "△", "square": "□"}.get(g, g)

    def _chip(self, cv: tk.Canvas, x: float, y: float, btn: str, r: float, clear=True, tag=None):
        """One button in the chosen style: a round face button or a shoulder tab, with its glyph."""
        if clear:
            cv.delete("all")
        g = GLYPHS[self._style()][btn]
        kw = {"tags": tag} if tag else {}
        if btn in FACE:
            cv.create_oval(x - r, y - r, x + r, y + r, fill="#101012", outline="#5b5b60", width=1, **kw)
        else:
            w = r * 1.45
            cv.create_rectangle(x - w, y - r * 0.8, x + w, y + r * 0.8, fill="#101012", outline="#5b5b60",
                                width=1, **kw)
        col = "#c8c8cc"
        if g in PS_COLORS:
            col, s = PS_COLORS[g], r * 0.45
            if g == "circle":
                cv.create_oval(x - s, y - s, x + s, y + s, outline=col, width=2, **kw)
            elif g == "cross":
                cv.create_line(x - s, y - s, x + s, y + s, fill=col, width=2, **kw)
                cv.create_line(x - s, y + s, x + s, y - s, fill=col, width=2, **kw)
            elif g == "triangle":
                cv.create_polygon(x, y - s, x - s, y + s * 0.8, x + s, y + s * 0.8, outline=col, fill="",
                                  width=2, **kw)
            else:
                cv.create_rectangle(x - s, y - s, x + s, y + s, outline=col, width=2, **kw)
        else:
            size = max(7, int(r * (0.85 if len(g) == 1 else 0.62)))
            cv.create_text(x, y, text=g, fill=col, font=(self.fam, size, "bold"), **kw)

    def _role_color(self, role: str) -> str:
        kind = ROLE_KIND.get(role, "none")
        return self.c["ACCENT"] if kind == "item" else ("#7fc8a9" if kind == "move" else self.c["DIM"])

    def _draw_pad(self, roles: dict):
        cv = self.pad
        cv.delete("all")
        layout = self.v["bplace"].get()
        # body: a generic pad outline (sticks left-top and right-bottom, face buttons right, shoulders on top)
        cv.create_polygon(70, 64, 360, 64, 404, 130, 404, 196, 360, 218, 318, 186, 112, 186, 70, 218, 26, 196,
                          26, 130, fill="#1b2a22", outline=self.c["BORDER"], smooth=True, width=2)
        cv.create_oval(78, 96, 120, 138, fill="#0f1813", outline="#3b5444")                       # left stick
        cv.create_oval(232, 146, 266, 180, fill="#0f1813", outline="#3b5444")                     # right stick
        # where each button is drawn, and where its role label goes
        cx, cy, d = 318, 120, 27
        spot = {"Y": (cx - d, cy), "A": (cx + d, cy), "X": (cx, cy - d), "B": (cx, cy + d),
                "ZL": (60, 18), "L": (60, 44), "R": (370, 44), "ZR": (370, 18)}
        label_at = {"X": (cx, cy - d - 15, "s"), "B": (cx, cy + d + 15, "n"), "Y": (cx - d - 16, cy, "e"),
                    "A": (cx + d + 16, cy, "w"), "ZL": (86, 18, "w"), "L": (86, 44, "w"),
                    "R": (344, 44, "e"), "ZR": (344, 18, "e")}
        for btn in I.REMAP_BUTTONS:
            at = face_place(btn, layout) if btn in FACE else btn
            x, y = spot[at]
            self._chip(cv, x, y, btn, 13, clear=False)
            role = roles[btn]
            lx, ly, anchor = label_at[at]
            txt = self.role_short(role)
            cv.create_text(lx, ly, text=txt, fill=self._role_color(role), anchor=anchor, font=(self.fam, 9, "bold"))

    def _draw_hud(self, roles: dict):
        """core/hud.c sb_xy() / slots_draw(): the HUD cluster, centred in the preview."""
        cv = self.hud
        cv.delete("all")
        simple = self.v["bsimple"].get()
        layout = self.v["bplace"].get()
        selector = self.v["blmode"].get() == "selector"
        mshield = self.v["mshield"].get()
        phys = {r: b for b, r in roles.items() if r != "none"}
        sc = 0.40   # layout units -> pixels; the cluster spans x 908..1677, y 517..900 (items above the top row)
        ox, oy = 215 - 1292.6 * sc, 104 + 712.0 * sc

        def to_px(x, y):
            return ox + x * sc, oy - y * sc

        # parts in core/hud.c: a button per role (target has none), and the item / sword on it
        for role in ("item2", "jump", "item3", "sword", "action", "item_main", "item1"):
            btn = phys.get(role)
            if btn is None:
                continue
            if role == "item2" and selector:
                continue                                    # L as the item selector: no button
            if simple and role in ("jump", "sword", "action"):
                continue
            if simple:
                bx, by = HUD_SIMPLE[role]
            else:
                at = face_place(btn, layout) if btn in FACE else btn
                bx, by = HUD_POS[at]
            x, y = to_px(bx, by)
            r = 22
            if role == "jump":   # the unlettered button with the "Jump" label
                cv.create_oval(x - r, y - r, x + r, y + r, fill="#101012", outline="#5b5b60")
            else:
                self._chip(cv, x, y, btn, r, clear=False)
            # the item sits up-left of its button (drawn a bit further out here, so the glyph stays readable)
            ix, iy = to_px(bx + ITEM_OFF[0] * 1.9, by + ITEM_OFF[1] * 1.9)
            if role == "jump":
                cv.create_text(x, y, text=self.role_short("jump"), fill="#e8e8e8", font=(self.fam, 8, "bold"))
            elif role == "sword":
                cv.create_text(ix, iy, text="⚔", fill="#dfe6ee", font=(self.fam, 13, "bold"))
            elif role in ITEM_MARK and not (role == "item2" and mshield):
                s = 10
                cv.create_rectangle(ix - s, iy - s, ix + s, iy + s, fill="#3a2f12", outline=self.c["ACCENT"],
                                    width=2)
                cv.create_text(ix, iy, text=ITEM_MARK[role], fill=self.c["ACCENT"], font=(self.fam, 11, "bold"))
        if not phys:
            cv.create_text(215, 100, text="—", fill=self.c["DIM"])
