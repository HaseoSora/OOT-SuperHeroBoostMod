"""Decode a BC4 texture out of a BNTX (block-linear) to PNG, to validate the swizzle.

Usage: python tools/bntx_decode.py <bntx(.zs)> <texture name> <out.png> [bh_gobs]
"""
import struct, sys
from PIL import Image
sys.path.insert(0, __import__("os").path.dirname(__file__))
from bntx_probe import load, textures


def deswizzle(data, width_blocks, height_blocks, bpp, bh_gobs):
    pitch = width_blocks * bpp
    gobs_x = (pitch + 63) // 64
    out = bytearray(pitch * height_blocks)
    for y in range(height_blocks):
        for xb in range(0, pitch):
            x = xb
            gob = (y // (8 * bh_gobs)) * 512 * bh_gobs * gobs_x + (x // 64) * 512 * bh_gobs + ((y % (8 * bh_gobs)) // 8) * 512
            addr = gob + ((x % 64) // 32) * 256 + ((y % 8) // 2) * 64 + ((x % 32) // 16) * 32 + (y % 2) * 16 + (x % 16)
            if addr < len(data):
                out[y * pitch + xb] = data[addr]
    return bytes(out)


def bc4_block(b):
    r0, r1 = b[0], b[1]
    pal = [r0, r1]
    if r0 > r1:
        pal += [((6 - i) * r0 + (1 + i) * r1) // 7 for i in range(6)]
    else:
        pal += [((4 - i) * r0 + (1 + i) * r1) // 5 for i in range(4)] + [0, 255]
    bits = int.from_bytes(b[2:8], "little")
    return [pal[(bits >> (3 * i)) & 7] for i in range(16)]


def decode_bc4(raw, w, h):
    img = Image.new("L", (w, h))
    px = img.load()
    bw = w // 4
    for by in range(h // 4):
        for bx in range(bw):
            blk = bc4_block(raw[(by * bw + bx) * 8:(by * bw + bx) * 8 + 8])
            for i in range(16):
                px[bx * 4 + i % 4, by * 4 + i // 4] = blk[i]
    return img


if __name__ == "__main__":
    b = load(sys.argv[1])
    name = sys.argv[2]
    t = [t for t in textures(b) if t[0] == name][0]
    _, fmt, w, h, mips, tile, bh_log, size, o = t
    # data pointer: BRTI +0x70 -> mip table -> offset
    mip0 = struct.unpack_from("<Q", b, o + 0x70)[0]
    off = struct.unpack_from("<Q", b, mip0)[0] if mip0 < len(b) else mip0
    print(name, hex(fmt), w, h, "bh_log", bh_log, "data@", hex(off), "size", size)
    data = b[off:off + size]
    bhs = int(sys.argv[4]) if len(sys.argv) > 4 else (1 << bh_log)
    raw = deswizzle(data, w // 4, h // 4, 8, bhs)
    decode_bc4(raw, w, h).save(sys.argv[3])
    print("saved", sys.argv[3], "bh gobs", bhs)
