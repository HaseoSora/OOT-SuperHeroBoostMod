"""Build the per-area collectible table used by the HUD counter (beta).

For every Banc file this records:
  - the Gold Skulltulas in that Banc: their IsGoldSkullDead Bool entry, and
  - the heart pieces with a HeartPieceAnchor_GameDataPath: its Bool entry.

The table stores the indexes of those entries in the GameData Bool table, which is
the same order as the Bool section of GameDataList.Product.*.byml.zs, so the module
can read the live value with a simple array index. It is generated from the user's
own dump and written to build/collectibles_data.h (not committed).

Output format (C):
  COLLECT_STAGES records of 48 bytes:
    char name[40]; u16 skull_off; u8 skull_n; u8 pad; u16 heart_off; u8 heart_n; u8 pad;
  COLLECT_FLAGS u16 indexes into the live Bool table.
"""
import os
import sys
import zstandard
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEVTOOL = Path(os.environ.get("SHB_DEVTOOL", r"F:\project\oot\vendor\devtool\oot-remake-devtool-main"))
ROMFS = Path(os.environ.get("SHB_ROMFS", r"F:\switch2\Longshot\romfs"))
OUT = ROOT / "build" / "collectibles_data.h"
REC_SIZE = 48

sys.path.insert(0, str(DEVTOOL))
import byml  # noqa: E402
import gamedata  # noqa: E402


def v(x):
    return getattr(x, "v", x)


def stage_key(p):
    n = p.name
    for suffix in (".bcett.byml.zs", ".bcett.byml"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
    for suffix in ("_Static", "_Dynamic"):
        if n.endswith(suffix):
            n = n[: -len(suffix)]
    return n


def write_empty(reason):
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        f"/* generated collectible table: {reason} */\n"
        "#define COLLECT_STAGES 0\n#define COLLECT_FLAGS 0\n"
        "static const unsigned char g_collect_table[1] = {0};\n"
        "static const unsigned short g_collect_flags[1] = {0};\n",
        encoding="ascii")
    print("collectibles: empty table (" + reason + ")")


def main():
    if not (ROMFS / "Banc").exists():
        return write_empty("game dump not found")
    try:
        gdl = gamedata.find_gamedatalist(str(ROMFS))
        raw = gamedata.RomFS(str(ROMFS)).read(str(Path(gdl).relative_to(ROMFS)).replace("\\", "/"))
        tree = byml.Byml(raw).tree()
        bool_index = {v(e["Hash"]): i for i, e in enumerate(tree["Data"]["Bool"])}
        dic = Path(os.environ.get("SHB_BCETT_DICT", r"C:\Users\Kuri\AppData\Local\Temp\opencode\bcett.byml.zsdic"))
        if not dic.exists():
            # Extract it from the game's own ZsDic.pack.zs if available.
            zstd = zstandard.ZstdDecompressor()
            pack = (ROMFS / "Pack" / "ZsDic.pack.zs").read_bytes()
            data = zstd.decompress(pack, max_output_size=20_000_000)
            from lib import sarc  # noqa: E402
            for name, (s, e) in sarc.read_sarc(data).items():
                if Path(name).name == "bcett.byml.zsdic":
                    dic = ROOT / "build" / "bcett.byml.zsdic"
                    dic.parent.mkdir(parents=True, exist_ok=True)
                    dic.write_bytes(data[s:e])
                    break
        zd = zstandard.ZstdDecompressor(dict_data=zstandard.ZstdCompressionDict(dic.read_bytes()))
    except Exception as exc:
        return write_empty("cannot read game data: %s" % exc)

    skulls = {}
    hearts = {}
    for p in sorted((ROMFS / "Banc").rglob("*.bcett.byml.zs")):
        try:
            t = byml.Byml(zd.decompress(p.read_bytes(), max_output_size=100_000_000)).tree()
        except Exception:
            continue
        key = stage_key(p)
        for a in t.get("Actors") or []:
            g = v(a.get("Gyaml"))
            if g == "Enemy_Skulltula_Gold":
                h = int(v(a.get("Hash")))
                flag = gamedata.mmh(f"IsGoldSkullDead.IsGoldSkullDead_{h}")
                if flag in bool_index:
                    skulls.setdefault(key, set()).add(bool_index[flag])
            elif g == "HeartPieceAnchor":
                dyn = a.get("Dynamic")
                path = v(dyn.get("HeartPieceAnchor_GameDataPath")) if isinstance(dyn, byml.BDict) else None
                if path:
                    flag = gamedata.mmh(path)
                    if flag in bool_index:
                        hearts.setdefault(key, set()).add(bool_index[flag])

    keys = sorted(set(skulls) | set(hearts))
    flags = []
    records = bytearray()
    for key in keys:
        sk = sorted(skulls.get(key, ()))
        he = sorted(hearts.get(key, ()))
        if len(key.encode()) >= 40:
            print("collectibles: skipping long stage name", key)
            continue
        skull_off = len(flags)
        flags.extend(sk)
        heart_off = len(flags)
        flags.extend(he)
        rec = bytearray(REC_SIZE)
        name = key.encode()
        rec[:len(name)] = name
        rec[40:42] = skull_off.to_bytes(2, "little")
        rec[42] = len(sk)
        rec[44:46] = heart_off.to_bytes(2, "little")
        rec[46] = len(he)
        records += rec

    stages = len(records) // REC_SIZE
    lines = [
        "/* generated by tools/make_collectibles.py from the user's dump; do not commit */",
        f"#define COLLECT_STAGES {stages}",
        f"#define COLLECT_FLAGS {len(flags)}",
        f"static const unsigned char g_collect_table[{max(1, len(records))}] = {{",
    ]
    lines.append(",".join(str(b) for b in records) if records else "0")
    lines.append("};")
    lines.append(f"static const unsigned short g_collect_flags[{max(1, len(flags))}] = {{")
    lines.append(",".join(str(x) for x in flags) if flags else "0")
    lines.append("};")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="ascii")
    print(f"collectibles: {stages} stages, {len(flags)} flags -> {OUT}")
    for key in keys:
        print(f"  {key:40} skull {len(skulls.get(key, ())):3} heart {len(hearts.get(key, ())):2}")


if __name__ == "__main__":
    main()
