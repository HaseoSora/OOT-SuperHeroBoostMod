"""Minimal NSO/IPS32 helpers for the OoT remake mod work.

NSO layout used by Project Eglantine (build E0F3...):
  offset 0x00: magic 'NSO0'
  offset 0x0C: flags (bit0 = compressed)
  offset 0x10: text file offset, 0x14 text memory offset, 0x18 text size
  offset 0x20/0x24/0x28: rodata
  offset 0x30/0x34/0x38: data
  offset 0x3C: bss size
  offset 0x60: stored text size (uncompressed size when compressed)
  offset 0xA0: text SHA-256
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path


def _seg(header: bytes, index: int) -> tuple[int, int, int]:
    # file offset, memory offset, size
    return struct.unpack_from("<III", header, 0x10 + index * 0x10)


def parse_nso(raw: bytes) -> dict:
    if raw[:4] != b"NSO0":
        raise ValueError("not an NSO")
    flags = struct.unpack_from("<I", raw, 0x0C)[0]
    stored_text = struct.unpack_from("<I", raw, 0x60)[0]
    text_file, text_mem, text_size = _seg(raw, 0)
    ro_file, ro_mem, ro_size = _seg(raw, 1)
    data_file, data_mem, data_size = _seg(raw, 2)
    bss = struct.unpack_from("<I", raw, 0x3C)[0]
    return dict(
        header=raw[:0x100],
        flags=flags,
        compressed=bool(flags & 1),
        text_file=text_file,
        text_mem=text_mem,
        text_size=text_size,
        stored_text=stored_text,
        ro_file=ro_file,
        ro_mem=ro_mem,
        ro_size=ro_size,
        data_file=data_file,
        data_mem=data_mem,
        data_size=data_size,
        bss=bss,
        raw_size=len(raw),
    )


def text_bytes(raw: bytes) -> bytes:
    """Return the uncompressed text segment."""
    info = parse_nso(raw)
    data = raw[info["text_file"]:info["text_file"] + (info["stored_text"] if info["compressed"] else info["text_size"])]
    if info["compressed"]:
        import lz4.block
        import zbic

        try:
            data = zbic.decompress(data)
        except zbic.error:
            data = lz4.block.decompress(data, uncompressed_size=info["text_size"])
    if len(data) != info["text_size"]:
        raise ValueError(f"text size mismatch: {len(data)} != {info['text_size']}")
    return data


def memory_image(raw: bytes) -> bytearray:
    """Return [0x100 header][text][rodata][data] as the IPS loader sees it."""
    info = parse_nso(raw)
    out = bytearray(info["header"])
    # The loader normalises segments so text follows the synthetic header.
    out.extend(text_bytes(raw))
    while len(out) % 0x10:
        out.append(0)
    out.extend(raw[info["ro_file"]:info["ro_file"] + info["ro_size"]])
    while len(out) % 0x10:
        out.append(0)
    out.extend(raw[info["data_file"]:info["data_file"] + info["data_size"]])
    return out


def parse_ips32(raw: bytes) -> list[tuple[int, bytes, bool]]:
    """Parse the IPS32 dialect used by Lichii: 4-byte offsets, 2-byte sizes, EEOF."""
    if raw[:5] != b"IPS32":
        raise ValueError("not an IPS32 file")
    pos = 5
    records = []
    while pos < len(raw):
        if raw[pos:pos + 4] == b"EEOF" or raw[pos:pos + 3] == b"EOF":
            break
        if pos + 6 > len(raw):
            raise ValueError("truncated IPS32 record")
        offset = struct.unpack_from(">I", raw, pos)[0]
        size = struct.unpack_from(">H", raw, pos + 4)[0]
        pos += 6
        if size == 0:
            count = struct.unpack_from(">H", raw, pos)[0]
            value = raw[pos + 2:pos + 3]
            pos += 3
            records.append((offset, value * count, True))
        else:
            records.append((offset, raw[pos:pos + size], False))
            pos += size
    return records


def make_ips32(records: list[tuple[int, bytes]]) -> bytes:
    out = bytearray(b"IPS32")
    for offset, data in records:
        data = bytes(data)
        out += struct.pack(">I", offset)
        if len(data) >= 4 and len(set(data)) == 1 and len(data) <= 0xFFFF:
            out += struct.pack(">H", 0) + struct.pack(">H", len(data)) + data[:1]
        else:
            out += struct.pack(">H", len(data)) + data
    out += b"EEOF"
    return bytes(out)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    import sys

    for arg in sys.argv[1:]:
        raw = Path(arg).read_bytes()
        info = parse_nso(raw)
        info["header"] = info["header"].hex()
        print(arg)
        for k, v in info.items():
            print(f"  {k}: {v}")
