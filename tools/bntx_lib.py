"""Minimal BNTX helpers for the Switch 2 ("Ounc") block-linear layout (BC4 textures).

Verified against Circle64_00: inside a 512-byte GOB the 16-byte sector index is
(addr bits 4..8) = (y0, y1, x4, y2, x5) with x in bytes, y in block rows.
"""
import struct
from bntx_probe import load, textures  # noqa: F401


def _addr(x, y, pitch, bh):
    gobs_x = (pitch + 63) // 64
    gob = (y // (8 * bh)) * 512 * bh * gobs_x + (x // 64) * 512 * bh + ((y % (8 * bh)) // 8) * 512
    return (gob + (x % 16) + (y % 2) * 16 + ((y % 8) // 2 % 2) * 32 + ((x % 32) // 16) * 64
            + ((y % 8) // 4) * 128 + ((x % 64) // 32) * 256)


def swizzle(raw, wb, hb, bpp, bh, size):
    pitch = wb * bpp
    out = bytearray(size)
    for y in range(hb):
        for x in range(pitch):
            a = _addr(x, y, pitch, bh)
            if a < size:
                out[a] = raw[y * pitch + x]
    return bytes(out)


def deswizzle(data, wb, hb, bpp, bh):
    pitch = wb * bpp
    out = bytearray(pitch * hb)
    for y in range(hb):
        for x in range(pitch):
            a = _addr(x, y, pitch, bh)
            if a < len(data):
                out[y * pitch + x] = data[a]
    return bytes(out)


def bc4_encode(pixels, w, h):
    """pixels: list of rows (0..255 ints). Returns linear BC4 blocks (row-major blocks)."""
    out = bytearray()
    for by in range((h + 3) // 4):
        for bx in range((w + 3) // 4):
            blk = []
            for j in range(4):
                for i in range(4):
                    x = min(bx * 4 + i, w - 1)
                    y = min(by * 4 + j, h - 1)
                    blk.append(pixels[y][x])
            hi, lo = max(blk), min(blk)
            if hi == lo:
                out += bytes([hi, lo]) + b"\0" * 6
                continue
            pal = [hi, lo] + [((6 - k) * hi + (1 + k) * lo) // 7 for k in range(6)]
            bits = 0
            for k, v in enumerate(blk):
                idx = min(range(8), key=lambda q: abs(pal[q] - v))
                bits |= idx << (3 * k)
            out += bytes([hi, lo]) + bits.to_bytes(6, "little")
    return bytes(out)


def bc4_decode(raw, w, h):
    rows = [[0] * w for _ in range(h)]
    wb = (w + 3) // 4
    for by in range((h + 3) // 4):
        for bx in range(wb):
            b = raw[(by * wb + bx) * 8:(by * wb + bx) * 8 + 8]
            r0, r1 = b[0], b[1]
            if r0 > r1:
                pal = [r0, r1] + [((6 - i) * r0 + (1 + i) * r1) // 7 for i in range(6)]
            else:
                pal = [r0, r1] + [((4 - i) * r0 + (1 + i) * r1) // 5 for i in range(4)] + [0, 255]
            bits = int.from_bytes(b[2:8], "little")
            for k in range(16):
                x, y = bx * 4 + k % 4, by * 4 + k // 4
                if x < w and y < h:
                    rows[y][x] = pal[(bits >> (3 * k)) & 7]
    return rows


def find(b, name):
    t = [t for t in textures(b) if t[0] == name][0]
    _, fmt, w, h, mips, tile, bh_log, size, o = t
    mip0 = struct.unpack_from("<Q", b, o + 0x70)[0]
    off = struct.unpack_from("<Q", b, mip0)[0]
    return dict(name=name, fmt=fmt, w=w, h=h, bh=1 << bh_log, size=size, off=off, brti=o)


def read_gray(b, name):
    t = find(b, name)
    assert t["fmt"] == 0x1D01
    raw = deswizzle(b[t["off"]:t["off"] + t["size"]], (t["w"] + 3) // 4, (t["h"] + 3) // 4, 8, t["bh"])
    return bc4_decode(raw, t["w"], t["h"]), t


def write_gray(b, name, rows):
    """Replace a BC4 texture's pixels in place (same size/format). b is a bytearray."""
    t = find(b, name)
    assert t["fmt"] == 0x1D01 and len(rows) == t["h"] and len(rows[0]) == t["w"]
    lin = bc4_encode(rows, t["w"], t["h"])
    data = swizzle(lin, (t["w"] + 3) // 4, (t["h"] + 3) // 4, 8, t["bh"], t["size"])
    b[t["off"]:t["off"] + t["size"]] = data
    return t
