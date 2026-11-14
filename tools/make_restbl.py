"""Build a ResourceSizeTable mod file that raises the memory budget of UI resources.

The game sizes its UI heap from this table (RESTBL, crc32(path) -> bytes). Our HUD adds
layout instances, so the Common layout archive needs a bigger budget; without it the
engine fails to create the extra child layouts (their frame objects come back null).

Reads the vanilla table from the user's dump (read only), writes
<out>/System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs
"""
import argparse
import struct
import sys
import zlib
from pathlib import Path

import zstandard

VANILLA = Path(r"F:\switch2\Longshot\romfs\System\Resource"
               r"\ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs")
NAME = VANILLA.name

# path -> extra bytes
GROW = {
    "UI/Layout2Archive/Common.Product.100.Nin_Ounce_NVN2.blarc": 0x600000,   # 12 extra item-button parts
}


def load(data: bytes):
    assert data[:6] == b"RESTBL"
    ver, sbs, ncrc, nname = struct.unpack_from("<IIII", data, 6)
    p = 0x16
    crc = {}
    for _ in range(ncrc):
        c, s = struct.unpack_from("<II", data, p)
        crc[c] = s
        p += 8
    names = {}
    for _ in range(nname):
        nm = data[p:p + sbs].split(b"\0")[0].decode()
        names[nm] = struct.unpack_from("<I", data, p + sbs)[0]
        p += sbs + 4
    return ver, sbs, crc, names


def dump(ver, sbs, crc, names) -> bytes:
    out = bytearray(b"RESTBL")
    out += struct.pack("<IIII", ver, sbs, len(crc), len(names))
    for c in sorted(crc):
        out += struct.pack("<II", c, crc[c])
    for nm in sorted(names):
        out += nm.encode().ljust(sbs, b"\0") + struct.pack("<I", names[nm])
    return bytes(out)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out", help="mod romfs folder to write into")
    ap.add_argument("--vanilla-raw", help="an already decompressed vanilla table (e.g. build/rsizetable.bin)")
    args = ap.parse_args()
    if args.vanilla_raw:
        raw = Path(args.vanilla_raw).read_bytes()
    else:
        raw = zstandard.ZstdDecompressor().decompressobj().decompress(VANILLA.read_bytes())
    ver, sbs, crc, names = load(raw)
    for path, extra in GROW.items():
        key = zlib.crc32(path.encode())
        if path in names:
            names[path] += extra
            print(f"{path}: +{extra:#x} -> {names[path]:#x} (name table)")
        elif key in crc:
            old = crc[key]
            crc[key] = (old + extra + 31) & ~31
            print(f"{path}: {old:#x} -> {crc[key]:#x}")
        else:
            sys.exit(f"{path} not in the table")
    out = Path(args.out) / "System" / "Resource" / NAME
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(zstandard.ZstdCompressor(level=19).compress(dump(ver, sbs, crc, names)))
    print("wrote", out)


if __name__ == "__main__":
    main()
