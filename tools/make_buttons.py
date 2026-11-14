"""Draw the Classic-style HUD buttons (our own art, drawn here with plain shapes and text) and pack them as game
textures for the icon loader: romfs/UI/Tex/Icon/<name>.bntx.zs plus an empty romfs/UI/Tex/IconSh/<name>_Sh.

Look: a dark opaque circle with a thin rim and the button's glyph in a faint tone in the middle, the item icon
drawn on top of it by the HUD (like Classic Item Slots' default theme).

    python tools/make_buttons.py            # -> build/buttons/<platform>/romfs/...  (switch, xbox, playstation)

Texture names (<= 19 characters, see bntx_write): OotBtn<P>_<button>, P = S (Switch), X (Xbox), P (PlayStation);
button = A B X Y L R ZL ZR. The HUD picks the set of the platform chosen in the app.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bntx_write import compress_zs, make_rgba_bntx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "build" / "tpl.bntx"
OUT = ROOT / "build" / "buttons"
SIZE = 128
BUTTONS = ("A", "B", "X", "Y", "L", "R", "ZL", "ZR", "Blank")   # Blank: no glyph (a text label goes on it)

# glyph drawn for each logical button (the Switch name is the logical one, as the game uses it)
GLYPHS = {
    "switch": {b: (b if b != "Blank" else "") for b in BUTTONS},
    "xbox": {"A": "B", "B": "A", "X": "Y", "Y": "X", "L": "LB", "R": "RB", "ZL": "LT", "ZR": "RT", "Blank": ""},
    "playstation": {"A": "circle", "B": "cross", "X": "triangle", "Y": "square",
                    "L": "L1", "R": "R1", "ZL": "L2", "ZR": "R2", "Blank": ""},
}
PREFIX = {"switch": "S", "xbox": "X", "playstation": "P"}


def font(px: int) -> ImageFont.FreeTypeFont:
    for name in ("arialbd.ttf", "seguisb.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_shape(d: ImageDraw.ImageDraw, shape: str, c: float, r: float, col, width: int) -> None:
    if shape == "circle":
        d.ellipse((c - r, c - r, c + r, c + r), outline=col, width=width)
    elif shape == "cross":
        d.line((c - r, c - r, c + r, c + r), fill=col, width=width)
        d.line((c - r, c + r, c + r, c - r), fill=col, width=width)
    elif shape == "triangle":
        d.polygon([(c, c - r), (c + r * 0.95, c + r * 0.7), (c - r * 0.95, c + r * 0.7)], outline=col, width=width)
    elif shape == "square":
        d.rectangle((c - r * 0.85, c - r * 0.85, c + r * 0.85, c + r * 0.85), outline=col, width=width)


SHOULDER = {"L", "R", "ZL", "ZR", "LB", "RB", "LT", "RT", "L1", "R1", "L2", "R2"}


def shoulder_outline(s: float, trigger: bool, left: bool):
    """Shoulder button (bumper: wide rounded bar) or trigger (taller, slanted outer top), as on the pads."""
    import math
    pts = []
    x0, x1 = s * 0.06, s * 0.94
    if trigger:
        y0, y1 = s * 0.20, s * 0.80
    else:
        y0, y1 = s * 0.28, s * 0.72
    r = (y1 - y0) * 0.42
    # rounded rectangle as a polygon, with the outer top corner raised for triggers
    corners = [(x1 - r, y0 + r, -90, 0), (x1 - r, y1 - r, 0, 90), (x0 + r, y1 - r, 90, 180), (x0 + r, y0 + r, 180, 270)]
    for cx, cy, a0, a1 in corners:
        for i in range(9):
            a = math.radians(a0 + (a1 - a0) * i / 8)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    if trigger:   # lift the outer half of the top edge
        lift = (y1 - y0) * 0.22
        pts = [(x, y - lift * max(0.0, ((s - x) if left else x) / s - 0.5) * 2 if y < s / 2 else y) for x, y in pts]
    return pts


def button_image(glyph: str) -> Image.Image:
    s = SIZE * 4                                   # supersampled, then reduced for smooth edges
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = s * 0.04
    if glyph in SHOULDER:
        trigger = glyph in ("ZL", "ZR", "LT", "RT", "L2", "R2")
        pts = shoulder_outline(s, trigger, glyph.startswith("L") or glyph == "ZL")
        d.polygon(pts, fill=(16, 16, 18, 255))
        d.line(pts + [pts[0]], fill=(255, 255, 255, 46), width=int(s * 0.018), joint="curve")
    else:
        d.ellipse((pad, pad, s - pad, s - pad), fill=(16, 16, 18, 255))                      # opaque body
        d.ellipse((pad, pad, s - pad, s - pad), outline=(255, 255, 255, 46), width=int(s * 0.018))   # thin rim
    faint = (255, 255, 255, 120)
    if not glyph:
        pass
    elif glyph in ("circle", "cross", "triangle", "square"):
        draw_shape(d, glyph, s / 2, s * 0.17, faint, int(s * 0.04))
    else:
        f = font(int(s * (0.34 if len(glyph) == 1 else 0.26)))
        d.text((s / 2, s / 2), glyph, fill=faint, font=f, anchor="mm")
    return im.resize((SIZE, SIZE), Image.LANCZOS)


def main() -> int:
    tpl = TEMPLATE.read_bytes()
    empty = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for plat, glyphs in GLYPHS.items():
        icon = OUT / plat / "romfs" / "UI" / "Tex" / "Icon"
        sh = OUT / plat / "romfs" / "UI" / "Tex" / "IconSh"
        icon.mkdir(parents=True, exist_ok=True)
        sh.mkdir(parents=True, exist_ok=True)
        for b in BUTTONS:
            name = f"OotBtn{PREFIX[plat]}_{b}"
            img = button_image(glyphs[b])
            img.save(OUT / plat / f"{name}.png")
            packed = compress_zs(make_rgba_bntx(tpl, name, img))
            (icon / f"{name}.bntx.zs").write_bytes(packed)
            (sh / f"{name}_Sh.bntx.zs").write_bytes(compress_zs(make_rgba_bntx(tpl, name + "_Sh", empty)))
            # the HUD draws the button as the item icon's "shadow" (behind the icon): same art in IconSh
            (sh / f"{name}.bntx.zs").write_bytes(packed)
        print(plat, "->", icon.parent.parent.parent.parent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
