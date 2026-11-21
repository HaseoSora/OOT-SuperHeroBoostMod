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
HELP_HANDLER = None


def set_help_handler(handler) -> None:
    """Register the inline help strip: HelpIcon sends the text there instead of opening a window."""
    global HELP_HANDLER
    HELP_HANDLER = handler


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

    def __init__(self, parent, title, desc="", command=None, desc_wrap=520, title_size=10,
                 help_text=None, **kw):
        super().__init__(parent, fg_color=PANEL2, border_width=1, border_color=BORDER, corner_radius=12,
                         height=kw.pop("height", 0), **{k: v for k, v in kw.items() if k == "width"})
        self._command = command
        self._enabled_cmd = command
        self._active = False
        self.head = tk.Frame(self, bg=PANEL2)
        self.head.pack(fill="x", padx=14, pady=(8, 0))
        self.title = tk.Label(self.head, text=title, bg=PANEL2, fg=TEXT, font=(FAM, title_size, "bold"),
                              anchor="w", justify="left")
        self.title.pack(side="left")
        self.help = None
        if help_text:
            self.help = tk.Label(self.head, text="?", bg=PANEL2, fg=DIM, font=(FAM, 9, "bold"),
                                 cursor="hand2", padx=2)
            self.help.pack(side="right")
            self.help.bind("<Button-1>", lambda e: _show_help(title, _help_text(help_text)))
            self.help.bind("<Enter>", lambda e: self.help.configure(fg=ACCENT))
            self.help.bind("<Leave>", lambda e: self.help.configure(fg=DIM if not self._active else "#1A1408"))
        self.desc = tk.Label(self, text=desc, bg=PANEL2, fg=DIM, font=(FAM, 8), anchor="w",
                             justify="left", wraplength=desc_wrap)
        self.desc.pack(fill="x", padx=14, pady=(1, 8))
        for w in (self, self.head, self.title, self.desc):
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
            self.head.configure(bg=fg)
            self.title.configure(bg=fg, fg=title)
            self.desc.configure(bg=fg, fg=desc)
            if self.help is not None:
                self.help.configure(bg=fg, fg="#1A1408" if active else DIM)
        except Exception:
            pass

    def set_enabled(self, enabled: bool):
        self._command = self._enabled_cmd if enabled else None
        try:
            self.configure(cursor="hand2" if enabled else "arrow")
            if self._active:
                self.title.configure(fg="#1A1408")
                self.desc.configure(fg="#3A2C08")
                if self.help is not None:
                    self.help.configure(fg="#1A1408" if enabled else DISABLED)
            else:
                self.title.configure(fg=TEXT if enabled else DISABLED)
                self.desc.configure(fg=DIM if enabled else DISABLED)
                if self.help is not None:
                    self.help.configure(fg=DIM if enabled else DISABLED)
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
        width = kw.pop("width", 1)
        _strip(kw)
        super().__init__(parent, text=text, variable=var, fg_color=ACCENT, hover_color=ACCENT2,
                         border_color=BORDER, checkmark_color="#1A1408", text_color=TEXT,
                         text_color_disabled=DISABLED, font=font, corner_radius=5, width=width,
                         checkbox_width=20, checkbox_height=20, **kw)
        try:   # the box sits a hair high next to Segoe UI's text; nudge it to the visual centre
            self._canvas.grid_configure(pady=(0, 2))
        except Exception:
            pass

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
        width = kw.pop("width", 1)
        _strip(kw)
        super().__init__(parent, text=text, variable=var, value=value, command=cmd, fg_color=ACCENT,
                         hover_color=ACCENT2, border_color=BORDER, text_color=TEXT, text_color_disabled=DISABLED,
                         font=font, width=width, radiobutton_width=18, radiobutton_height=18, corner_radius=9, **kw)
        try:   # same optical nudge as the checkbox: the ring should centre on the text, not on its line box
            self._canvas.grid_configure(pady=(0, 2))
        except Exception:
            pass

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
        self._popup = None
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
            self._close_popup()
        if "state" in kw:
            state = kw.pop("state")
            if state == "disabled":
                self._close_popup()
                kw.update(state="disabled", fg_color=PANEL, button_color=PANEL, text_color=DISABLED)
            else:
                kw.update(state="normal", fg_color=PANEL2, button_color=PANEL2, text_color=TEXT)
        return super().configure(**kw)

    config = configure

    # ---- the list itself: a rounded popup instead of Tk's square, white-edged native menu ----
    def _clicked(self, event=0):
        if self._state == "disabled" or not self._values:
            return
        if self._popup is not None and self._popup.winfo_exists():
            self._close_popup()
        else:
            self._open_popup()

    def _open_dropdown_menu(self):
        self._open_popup()

    def _open_popup(self):
        self._close_popup()
        top = tk.Toplevel(self)
        top.withdraw()
        top.overrideredirect(True)
        top.configure(bg=BORDER)
        try:
            top.attributes("-topmost", True)
        except Exception:
            pass
        shell = ctk.CTkFrame(top, fg_color=PANEL, corner_radius=12, border_width=1, border_color=BORDER)
        shell.pack(fill="both", expand=True)
        width = max(190, self.winfo_width())
        total = max(1, len(self._values)) * 30 + 18
        height = min(450, total)
        if total <= 450:
            inner = ctk.CTkFrame(shell, fg_color=PANEL, corner_radius=8)
        else:
            inner = ctk.CTkScrollableFrame(shell, fg_color=PANEL, corner_radius=8,
                                           width=width - 12, height=height - 12,
                                           scrollbar_button_color=BORDER,
                                           scrollbar_button_hover_color=ACCENT_DARK)
        inner.pack(fill="both", expand=True, padx=6, pady=6)
        current = self._var.get()
        for value in self._values:
            active = value == current
            b = ctk.CTkButton(inner, text=value, anchor="w", height=30, corner_radius=7,
                              fg_color=BORDER if active else "transparent",
                              hover_color=BORDER, text_color=ACCENT if active else TEXT,
                              font=(FAM, 10),
                              command=lambda v=value: self._choose(v))
            b.pack(fill="x")
        top.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = min(max(4, self.winfo_rootx()), screen_w - width - 8)
        y = self.winfo_rooty() + self.winfo_height() + 3
        if y + height > screen_h - 48:
            y = max(8, self.winfo_rooty() - height - 3)
        top.geometry(f"{width}x{height}+{int(x)}+{int(y)}")
        top.deiconify()
        top.lift()
        try:
            top.focus_force()
        except Exception:
            pass
        top.bind("<FocusOut>", lambda e: self._close_popup())
        top.bind("<Escape>", lambda e: self._close_popup())
        self._popup = top

    def _choose(self, value):
        self._dropdown_callback(value)
        self._close_popup()

    def _close_popup(self):
        pop = self._popup
        self._popup = None
        if pop is not None:
            try:
                pop.destroy()
            except Exception:
                pass


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


def _show_help(title, text) -> None:
    if HELP_HANDLER is not None and text:
        HELP_HANDLER(_help_text(title) or HELP_TITLE, _help_text(text))


class HelpBanner(ctk.CTkFrame):
    """A slim inline strip that shows an explanation above the page. No popup, no window."""

    def __init__(self, parent, **kw):
        super().__init__(parent, fg_color=PANEL2, border_width=1, border_color=BORDER,
                         corner_radius=10, height=0, **kw)
        self.accent = ctk.CTkFrame(self, width=3, height=1, fg_color=ACCENT, corner_radius=2)
        self.accent.pack(side="left", fill="y", padx=(10, 0), pady=10)
        body = tk.Frame(self, bg=PANEL2)
        body.pack(side="left", fill="x", expand=True, padx=10, pady=8)
        self.title = tk.Label(body, text="", bg=PANEL2, fg=ACCENT, font=(DISPLAY, 12, "bold"), anchor="w")
        self.title.pack(anchor="w")
        self.text = tk.Label(body, text="", bg=PANEL2, fg=TEXT, font=(FAM, 9), anchor="w",
                             justify="left", wraplength=880)
        self.text.pack(anchor="w", pady=(2, 0))
        close = tk.Label(self, text="×", bg=PANEL2, fg=DIM, font=(FAM, 13, "bold"), cursor="hand2")
        close.pack(side="right", anchor="n", padx=10, pady=6)
        close.bind("<Button-1>", lambda e: self.hide())
        close.bind("<Enter>", lambda e: close.configure(fg=TEXT))
        close.bind("<Leave>", lambda e: close.configure(fg=DIM))

    def show(self, title, text):
        self.title.configure(text=title or HELP_TITLE)
        self.text.configure(text=text)
        self.text.configure(wraplength=max(420, self.winfo_toplevel().winfo_width() - 420))

    def hide(self):
        self.pack_forget()


class HelpIcon(tk.Label):
    """A quiet "?" without a button background; it feeds the inline help strip."""

    def __init__(self, parent, text, title=None, bg=None, **kw):
        self._text = text
        self._title = title
        super().__init__(parent, text="?", bg=bg or _parent_bg(parent), fg=DIM,
                         font=(FAM, 9, "bold"), cursor="hand2", padx=2, **kw)
        self.bind("<Button-1>", self._open)
        self.bind("<Enter>", lambda e: self.configure(fg=ACCENT))
        self.bind("<Leave>", lambda e: self.configure(fg=DIM))

    def _open(self, _e=None):
        if HELP_HANDLER is None:
            return
        text = _help_text(self._text)
        if not text:
            return
        title = _help_text(self._title) if self._title is not None else HELP_TITLE
        HELP_HANDLER(title, text)
