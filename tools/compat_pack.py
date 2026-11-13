"""Pack the compat test mod: Classic Item Slots as installed + our stamina module.

Layout written to <out>:
  exefs/subsdk8   Classic's module, byte for byte (links at main+0x4F80000)
  exefs/subsdk9   ours (build_core.py --compat, linked right after Classic's mapped size)
  exefs/<id>.ips  union of Classic's IPS records and ours (the game applies one IPS only)
  romfs/          Classic's romfs (its HUD layout, textures, texts), copied as is

Classic is read from the user's installed copy; nothing of it is stored in the repo.
Usage: python tools/compat_pack.py <out_dir> [classic_dir]
"""
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD_ID = "E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348"
CLASSIC = Path(r"E:\Switch2\Emu\lichii-windows-x86_64\user\load\0400486024DEC000\Classic Item Slots")


def read_ips(data: bytes) -> list[tuple[int, bytes]]:
    assert data[:5] == b"IPS32"
    i, out = 5, []
    while data[i:i + 4] != b"EEOF":
        off = struct.unpack(">I", data[i:i + 4])[0]
        size = struct.unpack(">H", data[i + 4:i + 6])[0]
        assert size, "RLE records not supported"
        out.append((off, data[i + 6:i + 6 + size]))
        i += 6 + size
    return out


def main() -> int:
    out = Path(sys.argv[1])
    classic = Path(sys.argv[2]) if len(sys.argv) > 2 else CLASSIC
    ours = ROOT / "build" / "native" / "exefs"

    rec = read_ips((classic / "exefs" / f"{BUILD_ID}.ips").read_bytes())
    mine = read_ips((ours / f"{BUILD_ID}.ips").read_bytes())
    taken = {}
    for off, b in rec:
        for k in range(off, off + len(b)):
            taken[k] = "classic"
    for off, b in mine:
        for k in range(off, off + len(b)):
            if k in taken:
                raise SystemExit(f"IPS overlap at main+{k - 0x100:#x}: ours vs Classic")
    merged = bytearray(b"IPS32")
    for off, b in rec + mine:
        merged += struct.pack(">I", off) + struct.pack(">H", len(b)) + b
    merged += b"EEOF"

    if out.exists():
        shutil.rmtree(out)
    (out / "exefs").mkdir(parents=True)
    shutil.copy2(classic / "exefs" / "subsdk9", out / "exefs" / "subsdk8")
    shutil.copy2(ours / "subsdk9", out / "exefs" / "subsdk9")
    (out / "exefs" / f"{BUILD_ID}.ips").write_bytes(bytes(merged))
    shutil.copytree(classic / "romfs", out / "romfs")
    print(f"packed {out}: {len(rec)} Classic + {len(mine)} own IPS records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
