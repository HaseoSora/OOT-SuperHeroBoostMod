"""Write single-texture BNTX files (Switch 2 "Ounc" layout) with uncompressed RGBA8 (sRGB) data, for our own UI
textures loaded by name from romfs/UI/Tex/Icon (the item-icon loader, main+0xA73920).

A small single-texture BNTX is used as the container template (only its structure: header, BRTI fields, string
table, relocation table). The texture name, format, size, block height and data are replaced; the data block and
the relocation table move to fit the new size.

    from bntx_write import make_rgba_bntx
    data = make_rgba_bntx(template_bytes, "OotBtn_A_SW", pil_image)      # PIL RGBA image, power-of-two friendly

Name length: names are written into the template's string table in place, so they must not be longer than the
template's name (19 characters for the template in build/tpl.bntx); shorter names are zero padded.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bntx_lib import swizzle  # noqa: E402  (Switch 2 GOB sector order)

FMT_RGBA8_SRGB = 0x0B06
BPP = 4


def _u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def _u64(b, o):
    return struct.unpack_from("<Q", b, o)[0]


def block_height_log2(rows: int) -> int:
    """GOB block height (log2, in GOBs of 8 rows) the console uses for a texture this tall."""
    bh = 16
    while bh > 1 and rows <= (bh // 2) * 8:
        bh //= 2
    return bh.bit_length() - 1


def surface_size(width: int, height: int, bh_log: int) -> int:
    pitch = width * BPP
    gobs_x = (pitch + 63) // 64
    bh = 1 << bh_log
    rows_per_block = 8 * bh
    blocks_y = (height + rows_per_block - 1) // rows_per_block
    return gobs_x * 512 * bh * blocks_y


def make_rgba_bntx(template: bytes, name: str, image) -> bytes:
    b = bytearray(template)
    if b[:4] != b"BNTX" or b[0x20:0x24] != b"Ounc":
        raise ValueError("template is not a Switch 2 BNTX")
    brti = b.find(b"BRTI")
    if brti < 0 or b.count(b"BRTI") != 1:
        raise ValueError("template must hold exactly one texture")
    img = image.convert("RGBA")
    w, h = img.size
    # texture name: the BRTI name pointer (+0x60) -> u16 length + chars in the string table
    name_off = _u64(b, brti + 0x60)
    old_len = struct.unpack_from("<H", b, name_off)[0]
    nb = name.encode("ascii")
    if len(nb) > old_len:
        raise ValueError(f"name longer than the template's ({old_len} chars)")
    struct.pack_into("<H", b, name_off, len(nb))
    b[name_off + 2:name_off + 2 + old_len] = nb + b"\0" * (old_len - len(nb))
    # also the file name copy in the header string (same text in the template)
    # pixel data, block-linear
    bh_log = block_height_log2(h)
    size = surface_size(w, h, bh_log)
    raw = img.tobytes()
    data = swizzle(raw, w, h, BPP, 1 << bh_log, size)
    # BRTI fields (offsets relative to BRTI, as read by bntx_probe.textures)
    struct.pack_into("<I", b, brti + 0x1C, FMT_RGBA8_SRGB)
    struct.pack_into("<I", b, brti + 0x24, w)
    struct.pack_into("<I", b, brti + 0x28, h)
    struct.pack_into("<I", b, brti + 0x34, bh_log)
    struct.pack_into("<I", b, brti + 0x50, size)
    # data block: BRTD header (0x10) then the data at a 0x1000-aligned offset, as in the template
    brtd = b.find(b"BRTD")
    data_off = _u64(b, _u64(b, brti + 0x70))          # mip 0 address (file offset)
    rlt_old = _u32(b, 0x18)
    rlt = bytes(b[rlt_old:])
    old_data_size = rlt_old - data_off
    out = bytearray(b[:data_off]) + data
    pad = (-len(out)) % 0x1000
    out += b"\0" * pad
    new_rlt = len(out)
    struct.pack_into("<I", out, brtd + 8, new_rlt - brtd)            # BRTD block size (magic, next, size, 0)
    out += rlt
    # relocation table: its own offset field and the size of the section that holds the data block
    struct.pack_into("<I", out, new_rlt + 4, new_rlt)
    nsec = _u32(rlt, 8)
    for i in range(nsec):
        so = new_rlt + 0x10 + i * 0x18
        sec_off, sec_size = _u32(out, so + 8), _u32(out, so + 12)
        if sec_off <= brtd < sec_off + sec_size:
            struct.pack_into("<I", out, so + 12, new_rlt - sec_off)
    struct.pack_into("<I", out, 0x18, new_rlt)                          # header: relocation table offset
    struct.pack_into("<I", out, 0x1C, len(out))                         # header: file size
    _ = old_data_size
    return bytes(out)


def compress_zs(data: bytes) -> bytes:
    """zstd with the UI dictionary, like the game's own UI/Tex/Icon files."""
    import zstandard
    d = zstandard.ZstdCompressionDict(open(r"F:\project\oot\data\zsdic1.bin", "rb").read())
    return zstandard.ZstdCompressor(level=19, dict_data=d).compress(data)
