"""Modern widget kit for the companion app (CustomTkinter).

The app's logic and layout stay in :mod:`main`; this module supplies the visual layer: a dark forest palette,
rounded cards and buttons, styled selects, switches and entries, the scrolling page, and the help window.

The wrappers keep the tkinter call shapes the rest of the app already uses (``bg``, ``fg``, ``highlightbackground``,
``.config``, ``.current``, ``.bind("<<ComboboxSelected>>")``) so a widget can be swapped without rewriting its
call site. Text labels remain tkinter labels: their wrapping is the most predictable part of tkinter, and colour and
font are enough there.
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

# --------------------------------------------------------------------------- palette
BG = "#0A1410"
SIDEBAR = "#0C1A13"
PANEL = "#13261C"
PANEL2 = "#0C1A14"
CARD = "#162B20"
BORDER = "#2A4836"
ACCENT = "#E7BA4B"
ACCENT2 = "#F2D27A"
ACCENT_DARK = "#7A5C1F"
TEAL = "#63C79A"
TEXT = "#F5EFDD"
DIM = "#A8B8AA"
DISABLED = "#6B7C70"
RED = "#E06A5A"
AMBER = "#F2B45E"

FAM = "Segoe UI"
DISPLAY = "Palatino Linotype"
HELP_TITLE = "Ayuda"
CLOSE_LABEL = "Cerrar"


def set_fonts(fam: str, display: str) -> None:
    global FAM, DISPLAY
    FAM, DISPLAY = fam, display


def setup() -> None:
    ctk.set_appearance_mode("dark")
    try:
        ctk.set_default_color_theme("dark-blue")
    except Exception:
        pass
    # The app still calls .config on some widgets (tkinter's spelling). CustomTkinter implements .configure only;
    # alias it so the visual layer stays a drop-in.
    for cls in (ctk.CTk, ctk.CTkFrame, ctk.CTkLabel, ctk.CTkButton, ctk.CTkEntry, ctk.CTkCheckBox,
                ctk.CTkRadioButton, ctk.CTkOptionMenu, ctk.CTkProgressBar, ctk.CTkTextbox,
                ctk.CTkScrollableFrame, ctk.CTkToplevel):
        try:
            cls.config = cls.configure
        except Exception:
            pass


def _parent_bg(parent) -> str:
    for key in ("bg", "fg_color"):
        try:
            value = parent.cget(key)
            if isinstance(value, str) and value:
                return value
        except Exception:
            pass
    return PANEL


def _strip(kw: dict) -> dict:
    for k in ("bd", "relief", "insertbackground", "activebackground", "activeforeground", "selectcolor",
              "highlightcolor", "highlightthickness", "highlightbackground", "padx", "pady", "takefocus",
              "overrelief", "offrelief", "troughcolor", "indicatoron", "indicator_color", "border_spacing"):
        kw.pop(k, None)
    return kw


# --------------------------------------------------------------------------- frames and labels
class Frame(ctk.CTkFrame):
    """``tk.Frame``-shaped CTk frame: ``bg`` colours the surface, a 1 px border is optional."""

    def __init__(self, parent, bg=None, highlightbackground=None, highlightthickness=None, radius=0, **kw):
        fg = bg or kw.pop("fg_color", PANEL)
        width = kw.pop("width", None)
        height = kw.pop("height", 0)
        bw = int(highlightthickness if highlightthickness is not None else 0)
        _strip(kw)
        super().__init__(parent, fg_color=fg, border_width=bw, border_color=highlightbackground or BORDER,
                         corner_radius=radius, **({"width": width} if width else {}),
                         height=height, **kw)


class Card(ctk.CTkFrame):
    """A rounded card with a quiet gold line across its top."""

    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=PANEL, border_width=1, border_color=BORDER, corner_radius=16,
                         height=kw.pop("height", 0), **{k: v for k, v in kw.items() if k == "width"})
        self.accent = ctk.CTkFrame(self, height=3, fg_color=ACCENT, corner_radius=2)
        self.accent.pack(fill="x", padx=16, pady=(12, 0))


class Label(tk.Label):
    """A tk label with the app's palette, so wrapping stays reliable."""

    def __init__(self, parent, text="", bg=None, fg=TEXT, font=None, size=10, bold=False, italic=False,
                 wrap=760, anchor="w", justify="left", **kw):
        bg = bg or _parent_bg(parent)
        fg = kw.pop("color", fg)
        wrap = kw.pop("wraplength", wrap)
        if font is None:
            style = "bold" if bold else ("italic" if italic else "normal")
            font = (FAM, size, style)
        super().__init__(parent, text=text, bg=bg, fg=fg, font=font, anchor=anchor, justify=justify,
                         wraplength=wrap, **kw)


class Chip(ctk.CTkLabel):
    """A small rounded status chip."""

    def __init__(self, parent, text="", bg=None, fg=None, **kw):
        super().__init__(parent, text=text, fg_color=bg or PANEL2, text_color=fg or ACCENT,
                         corner_radius=12, border_width=1, border_color=BORDER,
                         font=(FAM, 9, "bold"), height=26, padx=10, **kw)

    def configure(self, **kw):
        if "fg" in kw:
            kw["text_color"] = kw.pop("fg")
        if "bg" in kw:
            kw["fg_color"] = kw.pop("bg")
        return super().configure(**kw)

    config = configure


class ChoiceCard(ctk.CTkFrame):
    """A large selectable card with a left-aligned title and description."""

    def __init__(self, parent, title, desc="", command=None, **kw):
        super().__init__(parent, fg_color=PANEL2, border_width=1, border_color=BORDER, corner_radius=12,
                         height=kw.pop("height", 0), **{k: v for k, v in kw.items() if k == "width"})
        self._command = command
        self._enabled_cmd = command
        self._active = False
        self.title = tk.Label(self, text=title, bg=PANEL2, fg=TEXT, font=(FAM, 10, "bold"),
                              anchor="w", justify="left")
        self.title.pack(fill="x", padx=14, pady=(8, 0))
        self.desc = tk.Label(self, text=desc, bg=PANEL2, fg=DIM, font=(FAM, 8), anchor="w",
                             justify="left", wraplength=520)
        self.desc.pack(fill="x", padx=14, pady=(1, 8))
        for w in (self, self.title, self.desc):
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass
            w.bind("<Button-1>", self._click)

    def _click(self, _e=None):
        if self._command:
            self._command()

    def set_active(self, active: bool):
        self._active = active
        fg = ACCENT if active else PANEL2
        border = ACCENT if active else BORDER
        title = "#1A1408" if active else TEXT
        desc = "#3A2C08" if active else DIM
        try:
            self.configure(fg_color=fg, border_color=border)
            self.title.configure(bg=fg, fg=title)
            self.desc.configure(bg=fg, fg=desc)
        except Exception:
            pass

    def set_enabled(self, enabled: bool):
        self._command = self._enabled_cmd if enabled else None
        try:
            self.configure(cursor="hand2" if enabled else "arrow")
            if self._active:
                self.title.configure(fg="#1A1408")
                self.desc.configure(fg="#3A2C08")
            else:
                self.title.configure(fg=TEXT if enabled else DISABLED)
                self.desc.configure(fg=DIM if enabled else DISABLED)
        except Exception:
            pass


# --------------------------------------------------------------------------- controls
class Button(ctk.CTkButton):
    def __init__(self, parent, text="", cmd=None, primary=False, ghost=False, danger=False, **kw):
        fg = ACCENT if primary else ("transparent" if ghost else PANEL2)
        hover = ACCENT2 if primary else (BORDER if not ghost else PANEL)
        fg_text = "#1A1408" if primary else (RED if danger else TEXT)
        _strip(kw)
        super().__init__(parent, text=text, command=cmd, fg_color=fg, hover_color=hover,
                         text_color=fg_text, text_color_disabled=DISABLED, font=(FAM, 10, "bold"),
                         corner_radius=10, height=34, border_width=0 if primary or ghost else 1,
                         border_color=BORDER, **kw)
        self._on_fg, self._on_hover, self._on_text = fg, hover, fg_text

    def configure(self, **kw):
        if "state" in kw:
            state = kw.pop("state")
            if state == "disabled":
                super().configure(state="disabled", fg_color=PANEL, hover_color=PANEL, text_color=DISABLED,
                                  border_color=BORDER)
            else:
                super().configure(state="normal", fg_color=self._on_fg, hover_color=self._on_hover,
                                  text_color=self._on_text)
        return super().configure(**kw)

    config = configure


class Entry(ctk.CTkEntry):
    def __init__(self, parent, textvariable=None, bg=None, fg=None, font=None, highlightbackground=None,
                 highlightthickness=None, **kw):
        _strip(kw)
        kw.setdefault("placeholder_text_color", DIM)
        super().__init__(parent, textvariable=textvariable, fg_color=bg or PANEL2, text_color=fg or TEXT,
                         font=font or (FAM, 10), border_width=1, border_color=highlightbackground or BORDER,
                         corner_radius=9, height=36, **kw)


class Check(ctk.CTkCheckBox):
    def __init__(self, parent, text="", var=None, bg=None, **kw):
        if var is None and "variable" in kw:
            var = kw.pop("variable")
        else:
            kw.pop("variable", None)
        font = kw.pop("font", (FAM, 10))
        kw.pop("fg", None)
        _strip(kw)
        super().__init__(parent, text=text, variable=var, fg_color=ACCENT, hover_color=ACCENT2,
                         border_color=BORDER, checkmark_color="#1A1408", text_color=TEXT,
                         text_color_disabled=DISABLED, font=font, corner_radius=5,
                         checkbox_width=20, checkbox_height=20, **kw)

    def configure(self, **kw):
        if "state" in kw:
            state = kw.pop("state")
            if state == "disabled":
                super().configure(state="disabled", fg_color=BORDER, hover_color=BORDER,
                                  border_color=BORDER, text_color=DISABLED)
            else:
                super().configure(state="normal", fg_color=ACCENT, hover_color=ACCENT2,
                                  border_color=BORDER, text_color=TEXT)
        return super().configure(**kw)

    config = configure


class Radio(ctk.CTkRadioButton):
    def __init__(self, parent, text="", var=None, value=0, cmd=None, bg=None, **kw):
        if var is None and "variable" in kw:
            var = kw.pop("variable")
        else:
            kw.pop("variable", None)
        font = kw.pop("font", (FAM, 10))
        kw.pop("fg", None)
        _strip(kw)
        super().__init__(parent, text=text, variable=var, value=value, command=cmd, fg_color=ACCENT,
                         hover_color=ACCENT2, border_color=BORDER, text_color=TEXT, text_color_disabled=DISABLED,
                         font=font, radiobutton_width=18, radiobutton_height=18, corner_radius=9, **kw)

    def configure(self, **kw):
        if "state" in kw:
            state = kw.pop("state")
            if state == "disabled":
                super().configure(state="disabled", fg_color=BORDER, hover_color=BORDER,
                                  border_color=BORDER, text_color=DISABLED)
            else:
                super().configure(state="normal", fg_color=ACCENT, hover_color=ACCENT2,
                                  border_color=BORDER, text_color=TEXT)
        return super().configure(**kw)

    config = configure


class Select(ctk.CTkOptionMenu):
    """A styled option list with the small part of the ttk.Combobox API the app uses."""

    def __init__(self, parent, values, var, width=16, **kw):
        self._values = list(values or [""])
        self._var = var
        self._cb = None
        _strip(kw)
        super().__init__(parent, values=self._values or [""], variable=var, width=max(80, int(width) * 9),
                         height=34, fg_color=PANEL2, button_color=PANEL2, button_hover_color=BORDER,
                         dropdown_fg_color=PANEL2, dropdown_hover_color=BORDER, dropdown_text_color=TEXT,
                         text_color=TEXT, text_color_disabled=DISABLED, font=(FAM, 10), dropdown_font=(FAM, 10),
                         corner_radius=8, command=self._chosen, **kw)
        if self._values and var.get() not in self._values:
            var.set(self._values[0])

    def _chosen(self, _value):
        if self._cb is not None:
            self._cb(None)

    def bind(self, seq, func, add=None):
        if seq == "<<ComboboxSelected>>":
            self._cb = func
            return None
        return super().bind(seq, func, add)

    def current(self, idx=None):
        if idx is None:
            value = self._var.get()
            return self._values.index(value) if value in self._values else 0
        if 0 <= idx < len(self._values):
            self._var.set(self._values[idx])

    def get(self):
        return self._var.get()

    def set(self, value):
        if value in self._values:
            self._var.set(value)

    def configure(self, **kw):
        if "values" in kw:
            self._values = list(kw.pop("values") or [""])
            if self._var.get() not in self._values:
                self._var.set(self._values[0])
            super().configure(values=self._values)
        if "state" in kw:
            state = kw.pop("state")
            if state == "disabled":
                kw.update(state="disabled", fg_color=PANEL, button_color=PANEL, text_color=DISABLED)
            else:
                kw.update(state="normal", fg_color=PANEL2, button_color=PANEL2, text_color=TEXT)
        return super().configure(**kw)

    config = configure


class Progress(ctk.CTkProgressBar):
    """A progress bar that accepts both 0..1 and 0..100 values."""

    def __init__(self, parent, **kw):
        kw.pop("style", None)
        kw.pop("maximum", None)
        value = kw.pop("value", 0)
        super().__init__(parent, height=12, corner_radius=6, fg_color=PANEL2, progress_color=ACCENT,
                         border_width=0, **kw)
        self.set(value)

    def set(self, value):
        if value is None:
            return
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        if value > 1.0:
            value /= 100.0
        super().set(max(0.0, min(1.0, value)))

    def configure(self, **kw):
        if "value" in kw:
            self.set(kw.pop("value"))
        kw.pop("maximum", None)
        kw.pop("style", None)
        return super().configure(**kw)

    config = configure

    def __setitem__(self, key, value):
        if key == "value":
            self.set(value)
        else:
            super().__setitem__(key, value)


class Textbox(ctk.CTkTextbox):
    def __init__(self, parent, bg=None, fg=None, font=None, wrap="none", height=120, state="normal", **kw):
        for k in ("highlightthickness", "highlightbackground", "highlightcolor", "insertbackground", "relief"):
            kw.pop(k, None)
        if isinstance(height, int) and height < 40:   # call sites still say "6 lines"
            height *= 18
        super().__init__(parent, fg_color=bg or PANEL2, text_color=fg or DIM, font=font or (FAM, 8),
                         wrap=wrap, height=height, border_width=1, border_color=BORDER, corner_radius=8, **kw)
        if state != "normal":
            self.configure(state=state)


class Toplevel(ctk.CTkToplevel):
    def __init__(self, parent, bg=None, **kw):
        super().__init__(parent, fg_color=bg or BG, **kw)

    def configure(self, **kw):
        if "bg" in kw:
            kw["fg_color"] = kw.pop("bg")
        return super().configure(**kw)

    config = configure


# --------------------------------------------------------------------------- scrolling page
class ScrollArea:
    """The app's scrolling content, on CustomTkinter's own scrollable frame."""

    def __init__(self, parent, bg=BG):
        self.frame = Frame(parent, bg=bg)
        self.inner = ctk.CTkScrollableFrame(self.frame, fg_color=bg, corner_radius=0,
                                            scrollbar_fg_color=bg, scrollbar_button_color=BORDER,
                                            scrollbar_button_hover_color=ACCENT_DARK)
        self.inner.pack(fill="both", expand=True)
        self.canvas = getattr(self.inner, "_parent_canvas", None)

    def refresh(self):
        try:
            self.inner.update_idletasks()
        except Exception:
            pass

    def destroy(self):
        try:
            self.frame.destroy()
        except Exception:
            pass


# --------------------------------------------------------------------------- help
def _help_text(text) -> str:
    return text() if callable(text) else str(text or "")


def help_window(parent, title: str, body: str) -> None:
    root = parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent
    win = Toplevel(root, bg=BG)
    win.title(title)
    win.transient(root)
    win.resizable(False, False)
    win.geometry("620x480")
    win.lift()
    try:
        win.grab_set()
    except tk.TclError:
        pass
    head = tk.Frame(win, bg=BG)
    head.pack(fill="x", padx=20, pady=(18, 6))
    tk.Label(head, text=title, bg=BG, fg=ACCENT, font=(DISPLAY, 17, "bold"), anchor="w").pack(side="left")
    tk.Label(head, text="?", bg=BG, fg=ACCENT_DARK, font=(DISPLAY, 22, "bold")).pack(side="right")
    box = Textbox(win, bg=PANEL, fg=TEXT, font=(FAM, 10), wrap="word", height=360)
    box.pack(fill="both", expand=True, padx=20, pady=(4, 12))
    box.insert("1.0", body)
    box.configure(state="disabled")
    Button(win, CLOSE_LABEL, win.destroy, primary=True).pack(anchor="e", padx=20, pady=(0, 16))


class HelpIcon(ctk.CTkButton):
    """A small gold-edged "?" that opens the full explanation in a readable window."""

    def __init__(self, parent, text, title: str | None = None, **kw):
        super().__init__(parent, text="?", width=23, height=23, corner_radius=12, fg_color=PANEL2,
                         hover_color=BORDER, text_color=DIM, font=(FAM, 9, "bold"), border_width=1,
                         border_color=BORDER, command=lambda: help_window(parent, title or HELP_TITLE,
                                                                           _help_text(text)), **kw)


class Tooltip:
    """A short native tooltip for the few controls whose label is not enough."""

    def __init__(self, widget, text, delay=550):
        self.widget, self.text, self.delay, self.tip, self.job = widget, text, delay, None, None
        widget.bind("<Enter>", self._enter, add="+")
        widget.bind("<Leave>", self._leave, add="+")
        widget.bind("<Destroy>", self._leave, add="+")

    def _enter(self, _e=None):
        self.job = self.widget.after(self.delay, self._show)

    def _show(self):
        if self.tip:
            return
        text = _help_text(self.text)
        if not text:
            return
        try:
            x = self.widget.winfo_rootx() + 16
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
            self.tip = tk.Toplevel(self.widget)
            self.tip.wm_overrideredirect(True)
            self.tip.wm_geometry(f"+{x}+{y}")
            tk.Label(self.tip, text=text, justify="left", wraplength=360, bg=PANEL2, fg=TEXT,
                     font=(FAM, 9), padx=9, pady=6, highlightthickness=1, highlightbackground=ACCENT_DARK
                     ).pack()
        except tk.TclError:
            self.tip = None

    def _leave(self, _e=None):
        if self.job:
            try:
                self.widget.after_cancel(self.job)
            except Exception:
                pass
            self.job = None
        if self.tip:
            try:
                self.tip.destroy()
            except tk.TclError:
                pass
            self.tip = None
