"""Stage monochrome GameCube face textures using the game's UI zstd dictionary."""
import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw
import zstandard

from bntx_write import make_rgba_bntx
from make_buttons import ROOT, SIZE, font

FILL = (16, 16, 18, 255)
RIM = (255, 255, 255, 46)
GLYPH = (128, 128, 132, 255)


def button_image(button, label):
    size = SIZE * 4
    image = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(image)
    rim_width = round(size * 0.018)
    if button in "AB":
        radius = size * (0.46 if button == "A" else 0.31)
        bounds = (size / 2 - radius, size / 2 - radius,
                  size / 2 + radius, size / 2 + radius)
        draw.ellipse(bounds, fill=FILL, outline=RIM, width=rim_width)
    else:
        # A rounded annular segment gives both caps their concave inner edge.
        cap = Image.new("RGBA", (size, size))
        cap_draw = ImageDraw.Draw(cap)
        radius, half_width, sweep = size * 0.77, size * 0.19, 0.30
        arc = [(size / 2 + radius * math.sin(t), size / 2 + radius * (1 - math.cos(t)))
               for t in (sweep * step / 32 for step in range(-32, 33))]
        for thickness, color in ((half_width, RIM), (half_width - rim_width, FILL)):
            for x, y in arc:
                cap_draw.ellipse((x - thickness, y - thickness, x + thickness, y + thickness),
                                 fill=color)
        image = cap.rotate(-80 if button == "X" else 17, Image.Resampling.BICUBIC)
        draw = ImageDraw.Draw(image)
    if label:
        draw.text((size / 2, size / 2), button, fill=GLYPH,
                  font=font(round(size * (0.34 if button == "A" else 0.27))), anchor="mm")
    return image.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def ui_dictionary():
    """Load the UI compression dictionary from the local romfs dump, or an extracted copy."""
    import os

    explicit = os.environ.get("SHB_UI_DICTIONARY")
    if explicit:
        return zstandard.ZstdCompressionDict(Path(explicit).expanduser().read_bytes())
    romfs = os.environ.get("SHB_ROMFS")
    if romfs:
        from lib.sarc import read_sarc
        pack = Path(romfs).expanduser() / "Pack" / "ZsDic.pack.zs"
        data = zstandard.ZstdDecompressor().decompress(pack.read_bytes(), max_output_size=8_000_000)
        for name, (start, end) in read_sarc(data).items():
            if Path(name).name == "zs.zsdic":
                return zstandard.ZstdCompressionDict(data[start:end])
        raise ValueError(f"No zs.zsdic dictionary in {pack}")
    raise SystemExit("The GameCube buttons need the game's UI dictionary: set SHB_ROMFS to a romfs dump "
                     "(it reads Pack/ZsDic.pack.zs) or SHB_UI_DICTIONARY to the extracted zs.zsdic.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dictionary", type=Path)
    parser.add_argument("--payload", type=Path, default=ROOT / "app" / "payload")
    args = parser.parse_args()
    source = args.payload / "button_romfs" / "switch" / "UI" / "Tex"
    output = args.payload / "button_romfs" / "gamecube" / "UI" / "Tex"
    dictionary = zstandard.ZstdCompressionDict(args.dictionary.read_bytes()) if args.dictionary else ui_dictionary()
    decode = zstandard.ZstdDecompressor(dict_data=dictionary)
    encode = zstandard.ZstdCompressor(level=19, dict_data=dictionary)
    transparent = Image.new("RGBA", (16, 16))
    for version in ("A", "B", "X", "Y", "A0", "B0", "X0", "Y0"):
        button = version[0]
        original = "Blank" if version.endswith("0") else button
        filename = f"OotBtnS_{original}"
        base = decode.decompress((source / "Icon" / f"{filename}.bntx.zs").read_bytes())
        shadow = decode.decompress((source / "IconSh" / f"{filename}_Sh.bntx.zs").read_bytes())
        name = f"OotBtnG_{version}"
        image = button_image(button, len(version) == 1)
        for directory, texture, template, pixels in (
            ("Icon", name, base, image),
            ("IconSh", name + "_Sh", shadow, transparent),
        ):
            folder = output / directory
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{texture}.bntx.zs").write_bytes(encode.compress(make_rgba_bntx(template, texture, pixels)))


if __name__ == "__main__":
    main()
