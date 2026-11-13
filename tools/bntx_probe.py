"""List textures of a BNTX (optionally .zs): name, format, size, tile mode. Reads the user's dump only.

Usage: python tools/bntx_probe.py <file.bntx[.zs]> [name_regex]
"""
import re, struct, sys
import zstandard

DICT = r"F:\project\oot\data\zsdic1.bin"


def load(path):
    raw = open(path, "rb").read()
    if raw[:4] == b"BNTX":
        return raw
    for d in (None, DICT):
        try:
            dd = zstandard.ZstdDecompressor(dict_data=zstandard.ZstdCompressionDict(open(d, "rb").read()) if d else None)
            return dd.decompress(raw, max_output_size=400_000_000)
        except Exception:
            continue
    raise SystemExit("cannot decompress")


def textures(b):
    out = []
    for m in re.finditer(b"BRTI", b):
        o = m.start()
        w = lambda off: struct.unpack_from("<I", b, o + off)[0]
        tile, = struct.unpack_from("<H", b, o + 0x12)
        mips, = struct.unpack_from("<H", b, o + 0x16)
        fmt, width, height = w(0x1C), w(0x24), w(0x28)
        bh = w(0x34)
        size = w(0x50)
        name_ptr = struct.unpack_from("<Q", b, o + 0x60)[0]
        nlen, = struct.unpack_from("<H", b, name_ptr)
        name = b[name_ptr + 2:name_ptr + 2 + nlen].decode("latin1")
        out.append((name, fmt, width, height, mips, tile, bh, size, o))
    return out


if __name__ == "__main__":
    b = load(sys.argv[1])
    print("bntx bytes", len(b), "header", b[:8], "nx", b[0x20:0x24])
    ts = textures(b)
    print(len(ts), "textures")
    pat = re.compile(sys.argv[2]) if len(sys.argv) > 2 else None
    for t in ts:
        if not pat or pat.search(t[0]):
            print(f"  {t[0]:34s} fmt {t[1]:#08x} {t[2]}x{t[3]} mips {t[4]} tile {t[5]} bh {t[6]} size {t[7]} @ {t[8]:#x}")
