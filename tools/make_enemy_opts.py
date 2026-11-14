"""Build the two beta enemy mods from the user's own game dump.

Output (installed by the app only when the corresponding beta option is enabled):
  app/payload/romfs_opts/enemy_double/...   duplicated generic enemies (Banc placements + field auto-spawn)
  app/payload/romfs_opts/enemy_speed/...    x2 animation/movement/attack cadence data edits

The files are game data, so they are generated locally from the dump and are not part of the repository.
This is a beta generator: the exclusion list is deliberately conservative and some enemies are left alone.
"""
import copy
import os
import random
import struct
import sys
import zstandard
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEVTOOL = Path(os.environ.get("SHB_DEVTOOL", r"F:\project\oot\vendor\devtool\oot-remake-devtool-main"))
ROMFS = Path(os.environ.get("SHB_ROMFS", r"F:\switch2\Longshot\romfs"))
OUT = ROOT / "app" / "payload" / "romfs_opts"
DICT_CACHE = ROOT / "build" / "enemy_opts_dicts"
RESTBL_REL = "System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable.zs"

sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(DEVTOOL))
from lib import sarc  # noqa: E402
import byml  # noqa: E402

# Boss / miniboss / scripted or otherwise special actors. Generic enemies pass.
BLOCK = (
    "Boss", "boss", "Ganon", "Gohma", "Dodongo", "Barinade", "PhantomGanon", "Volvagia",
    "Morpha", "BongoBongo", "Twinrova", "Kotake", "Koume", "IronKnuckle", "DeadHand",
    "FlareDancer", "BigOcto", "Naboru", "Meg", "DarkLink", "Skulltula_Gold",
    "Scrub_Business", "Scrub_Mad", "GerudoThief", "WolfosStage", "StalfosStage",
    "LizalfosStage", "DinolfosStage", "EnemyMuseum", "Amy", "Beth", "Joelle",
)
BLOCK_BANCS = (
    "Banc/GameBancParam", "Banc/BancBasedResource", "Banc/DreamWorld",
    "Banc/BossRushIntervalRoom", "Banc/EnemyMuseum", "Banc/FinalBattleField",
    "Banc/CrumblingGanonCastle", "Banc/SageRoom", "Banc/Demo_",
)


def load_dicts():
    DICT_CACHE.mkdir(parents=True, exist_ok=True)
    raw = (ROMFS / "Pack/ZsDic.pack.zs").read_bytes()
    data = zstandard.ZstdDecompressor().decompress(raw, max_output_size=20_000_000)
    files = sarc.read_sarc(data)
    out = {}
    for name, (s, e) in files.items():
        p = DICT_CACHE / Path(name).name
        if not p.exists():
            p.write_bytes(data[s:e])
        out[Path(name).name] = p.read_bytes()
    return out


def pack_of(data, dictionary):
    return zstandard.ZstdDecompressor(dict_data=zstandard.ZstdCompressionDict(dictionary)).decompress(
        data, max_output_size=200_000_000)


def pack_to(data, dictionary):
    return zstandard.ZstdCompressor(dict_data=zstandard.ZstdCompressionDict(dictionary)).compress(data)


def byml_bytes_tree(data):
    b = byml.Byml(data)
    return b, b.tree()


def set_float(buf, off, value):
    struct.pack_into("<f", buf, off, float(value))


def scale_fields(buf, data, suffix, factor, min_positive=0.01):
    """Scale float fields whose path ends with one of suffix (in-place, same file size)."""
    changed = 0
    b = byml.Byml(data)
    for path, typ, value, off in b.flat():
        if typ != byml.T_FLOAT or not isinstance(value, float):
            continue
        if not any(path.endswith(s.lstrip("/")) for s in suffix):
            continue
        if value > min_positive:
            set_float(buf, off, value * factor)
            changed += 1
    return changed


def edit_pack(path, dictionaries, speed=True):
    raw = path.read_bytes()
    data = bytearray(pack_of(raw, dictionaries["pack.zsdic"]))
    files = sarc.read_sarc(bytes(data))
    changed = False
    for name, (start, end) in files.items():
        if not (name.endswith(".bgyml") or name.endswith(".byml")):
            continue
        block = data[start:end]
        try:
            b = byml.Byml(block)
        except Exception:
            continue
        if speed:
            before = bytes(block)
            if "BSA/MovementParam/" in name:
                scale_fields(block, before, ("/WalkSpeed", "/RunSpeed", "/DashSpeed", "/EscapeSpeed",
                                             "/SpecialMoveSpeed", "/StrafeSpeed", "/LiftWalkSpeed",
                                             "/WalkBackwardsSpeed"), 2.0)
            # AttackIntervalRatio multiplies the global AttackInterval table, so scaling both
            # would give x4. Keep the ratio and shorten the table plus the explicit cooldowns.
            if "Game/BSA/ActionSeqContainer/" in name:
                scale_fields(block, before, ("/AttackStartTimeoutFrames",
                                             "/AttackIntervalTimeFromDamage", "/AttackIntervalTimeFromGuard",
                                             "/AttackIntervalTimeGuarded", "/AttackIntervalTimeMinGrdedCombo",
                                             "/BackWalkTimeMax", "/BackWalkTimeMin", "/TimeoutTime"), 0.5)
            if "GameBalance/AttackInterval/" in name:
                scale_fields(block, before, ("/LongIntervalMax", "/LongIntervalMin", "/MediumIntervalMax",
                                             "/MediumIntervalMin", "/ShortIntervalMax", "/ShortIntervalMin"), 0.5)
            if bytes(block) != before:
                data[start:end] = block
                changed = True
    if changed:
        return pack_to(bytes(data), dictionaries["pack.zsdic"])
    return None


def edit_asb(path, zs_dict):
    raw = path.read_bytes()
    try:
        data = bytearray(zstandard.ZstdDecompressor(
            dict_data=zstandard.ZstdCompressionDict(zs_dict)).decompress(raw, max_output_size=20_000_000))
    except Exception:
        return None
    if data[:4] != b"ASB ":
        return None
    # Header: 0x14 = element count, 0x18 = element array (stride 0x24).
    count, arr = struct.unpack_from("<II", data, 0x14)
    if not (0 < count < 10000 and 0 < arr < len(data)):
        return None
    changed = False
    for i in range(count):
        off = arr + i * 0x24
        if off + 0x0C > len(data):
            break
        if struct.unpack_from("<H", data, off)[0] != 12:   # FrameController
            continue
        body = struct.unpack_from("<I", data, off + 0x08)[0]
        if not (0 < body <= len(data) - 8):
            continue
        rate = struct.unpack_from("<f", data, body + 0x04)[0]   # playback rate (1.0 = normal)
        if 0.01 < rate < 8.0:
            struct.pack_into("<f", data, body + 0x04, min(rate * 2.0, 8.0))
            changed = True
    if not changed:
        return None
    return zstandard.ZstdCompressor(dict_data=zstandard.ZstdCompressionDict(zs_dict)).compress(bytes(data))


def new_hash(rng, used):
    while True:
        v = rng.getrandbits(64)
        if v not in used:
            used.add(v)
            return v


def duplicate_banc(path, rng, size_changes):
    raw = path.read_bytes()
    try:
        data = zstandard.ZstdDecompressor(
            dict_data=zstandard.ZstdCompressionDict(DICTS["bcett.byml.zsdic"])).decompress(
            raw, max_output_size=100_000_000)
    except Exception:
        return None
    try:
        b, tree = byml_bytes_tree(data)
    except Exception:
        return None
    actors = tree.get("Actors")
    if actors is None:
        return None
    used = {a.get("Hash").v for a in actors if isinstance(a, dict) and a.get("Hash") is not None}
    add = []
    for a in actors:
        g = a.get("Gyaml")
        if g is None:
            continue
        name = g.v
        if not name.startswith("Enemy_") or any(x in name for x in BLOCK):
            continue
        if a.get("Links") is not None or a.get("Name") is not None:
            continue
        c = copy.deepcopy(a)
        h = new_hash(rng, used)
        c["Hash"] = byml.Val(byml.T_U64, h)
        ph = c.get("Phive")
        if ph is not None and ph.get("Placement") is not None:
            ph["Placement"]["ID"] = byml.Val(byml.T_U64, h)
        c["SRTHash"] = byml.Val(byml.T_UINT, rng.getrandbits(32))
        tr = c.get("Translate")
        if tr is not None and len(tr) == 3:
            tr[0] = byml.Val(byml.T_FLOAT, tr[0].v + 1.5)
            tr[2] = byml.Val(byml.T_FLOAT, tr[2].v + 1.5)
        add.append(c)
    if not add:
        return None
    actors.extend(add)
    out = byml.write(tree, version=b.version, e=b.e)
    size_changes.append((str(path.relative_to(ROMFS)).replace("\\", "/").removesuffix(".zs"), len(out)))
    return zstandard.ZstdCompressor(
        dict_data=zstandard.ZstdCompressionDict(DICTS["bcett.byml.zsdic"])).compress(out)


def edit_autoplace(path, size_changes):
    raw = path.read_bytes()
    try:
        b, tree = byml_bytes_tree(raw)
    except Exception:
        return None
    changed = False

    def walk(node):
        nonlocal changed
        if isinstance(node, byml.BDict):
            for k, v in list(node.items()):
                if k in ("CreateActorCountMinAtOnce", "CreateActorCountMaxAtOnce",
                         "MinExistActorCountToCreate") and isinstance(v, byml.Val) and isinstance(v.v, int):
                    node[k] = byml.Val(v.t, max(1, v.v * 2))
                    changed = True
                elif k in ("IntervalToCreateFrame", "IntervalRandomToCreateFrame") and isinstance(v, byml.Val) \
                        and isinstance(v.v, (int, float)):
                    node[k] = byml.Val(v.t, v.v / 2.0)
                    changed = True
                walk(v)
        elif isinstance(node, byml.BArr):
            for v in node:
                walk(v)

    walk(tree)
    if not changed:
        return None
    out = byml.write(tree, version=b.version, e=b.e)
    size_changes.append((str(path.relative_to(ROMFS)).replace("\\", "/"), len(out)))
    return out


def update_restbl(size_changes):
    if not size_changes:
        return None
    p = ROMFS / RESTBL_REL
    data = bytearray(zstandard.ZstdDecompressor().decompress(p.read_bytes(), max_output_size=20_000_000))
    n = struct.unpack_from("<I", data, 0x0E)[0]
    base = 0x16
    by_crc = {}
    for i in range(n):
        crc, size = struct.unpack_from("<II", data, base + i * 8)
        by_crc[crc] = (base + i * 8, size)
    changed = False
    import binascii
    for path, size in size_changes:
        crc = binascii.crc32(path.encode()) & 0xFFFFFFFF
        hit = by_crc.get(crc)
        if hit is None:
            continue
        off, old = hit
        new = max(old, (size + 0x2000 + 7) & ~7)
        if new != old:
            struct.pack_into("<I", data, off + 4, new)
            changed = True
    if not changed:
        return None
    return zstandard.ZstdCompressor().compress(bytes(data))


def main():
    global DICTS
    if not (ROMFS / "Banc").exists():
        print("enemy options: game dump not found (set ROMFS); keeping existing payload")
        return
    import shutil
    DICTS = load_dicts()
    for name in ("enemy_double", "enemy_speed"):
        d = OUT / name
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    rng = random.Random(0x5A17B005)
    size_changes = []

    # Field enemies that are auto-placed: double counts and halve intervals.
    for p in sorted((ROMFS / "Scene/Component/AutoPlacementMgrParam").glob("*.bgyml")):
        out = edit_autoplace(p, size_changes)
        if out:
            dst = OUT / "enemy_double" / p.relative_to(ROMFS)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(out)

    # Hand-placed generic enemies: one clone each.
    for p in sorted((ROMFS / "Banc").rglob("*.bcett.byml.zs")):
        rel = str(p.relative_to(ROMFS)).replace("\\", "/")
        if any(rel.startswith(x) for x in BLOCK_BANCS):
            continue
        out = duplicate_banc(p, rng, size_changes)
        if out:
            dst = OUT / "enemy_double" / p.relative_to(ROMFS)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(out)

    # Enemy animation: ASB frame-controller playback rates. Same exclusions as the packs,
    # so bosses and scripted fights keep their original timing.
    for p in sorted((ROMFS / "AS").glob("Enemy_*.root.asb.zs")):
        if any(x in p.stem for x in BLOCK):
            continue
        out = edit_asb(p, DICTS["zs.zsdic"])
        if out:
            dst = OUT / "enemy_speed" / p.relative_to(ROMFS)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(out)

    # Enemy movement and attack cadence: values inside enemy packs.
    for p in sorted((ROMFS / "Pack/Actor").glob("Enemy_*.pack.zs")):
        if any(x in p.stem for x in BLOCK):
            continue
        out = edit_pack(p, DICTS)
        if out:
            dst = OUT / "enemy_speed" / p.relative_to(ROMFS)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(out)

    table = update_restbl(size_changes)
    if table:
        dst = OUT / "enemy_double" / RESTBL_REL
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(table)
    print("enemy options written to", OUT)


if __name__ == "__main__":
    main()
