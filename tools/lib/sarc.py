"""Minimal SARC reader/writer (own implementation) for the game's UI archives."""
import struct


def read_sarc(data: bytes) -> dict[str, tuple[int, int]]:
    """Return {file name: (start, end)} offsets into `data`."""
    assert data[:4] == b"SARC"
    hdr, bom, size, data_off = struct.unpack_from("<HHII", data, 4)
    assert data[0x14:0x18] == b"SFAT"
    _, count, _ = struct.unpack_from("<HHI", data, 0x18)
    entries = []
    for i in range(count):
        h, attr, s, e = struct.unpack_from("<IIII", data, 0x20 + i * 16)
        entries.append((h, attr, s, e))
    sfnt = 0x20 + count * 16
    assert data[sfnt:sfnt + 4] == b"SFNT"
    names_off = sfnt + 8
    out = {}
    for h, attr, s, e in entries:
        if attr >> 24:
            no = names_off + (attr & 0xFFFFFF) * 4
            end = data.index(b"\0", no)
            out[data[no:end].decode()] = (data_off + s, data_off + e)
    return out
