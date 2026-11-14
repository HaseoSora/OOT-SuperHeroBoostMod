"""Install logic of the Super Hero Boost companion app. No compiler involved: it only patches the config block
inside the prebuilt module, merges the IPS patch files and copies files into the emulator's mod folder.
User-facing problems are raised as InstallError(key, arg) so the window can show them in the chosen language."""
import json
import re
import shutil
import struct
import sys
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import paths

TITLE_ID = "0400486024DEC000"
BUILD_ID = "E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348"
MOD_NAME = "00-Super-Hero-Boost"
MARKER = ".super-hero-boost"
CLASSIC_SUBSDK_SIZE = 20744          # Classic Item Slots' module


class InstallError(Exception):
    def __init__(self, key: str, arg: str = ""):
        super().__init__(f"{key}: {arg}")
        self.key, self.arg = key, arg


def resource_dir() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "payload"


@dataclass
class Settings:
    classic: bool = True
    stamina: bool = True
    preset: int = 0                 # 0 hardcore, 1 hardcore combat only, 2 sprint only, 3 advanced
    jump: bool = True
    attack: bool = True
    sprint: bool = True
    block: bool = True
    shoot: bool = True
    roll: bool = True
    combat_only: bool = False
    enemy_hp: int = 100             # enemy health, percent of vanilla
    sprint_speed: int = 125         # sprint (A held while moving) speed, percent of vanilla
    damage: int = 100               # damage the player takes, percent of vanilla
    no_heart_drop: bool = False     # hearts dropped by enemies/grass become green rupees
    hud_rupees: bool = False
    hud_clock: bool = False
    clock_24h: bool = False
    songbook: bool = True            # play a learned song by selecting it in the native songbook
    enemy_double: bool = False       # beta: install the duplicated-enemy romfs mod
    enemy_speed: bool = False        # beta: install the x2 enemy animation/movement/cadence romfs mod

    def to_dict(self): return dict(self.__dict__)


# what each preset switches on (what the window shows greyed out); "advanced" uses the user's own choices
PRESET_VIEW = {
    0: dict(jump=1, attack=1, sprint=1, block=1, shoot=1, roll=1, combat_only=0),
    1: dict(jump=1, attack=1, sprint=1, block=1, shoot=1, roll=1, combat_only=1),
    2: dict(jump=0, attack=0, sprint=1, block=0, shoot=0, roll=0, combat_only=0),
}


# ---------- emulator / mods folder detection ----------
def _load_directory(emu: Path) -> Path | None:
    """Read `load_directory` from the emulator's qt-config.ini (portable across platforms)."""
    for cfg in (emu / "user" / "config" / "qt-config.ini", emu / "config" / "qt-config.ini"):
        if not cfg.exists():
            continue
        try:
            txt = cfg.read_text(errors="replace")
        except OSError:
            continue
        for m in re.finditer(r"^\s*load_directory\s*=\s*(.+?)\s*$", txt, re.M):
            value = m.group(1).strip().strip('"')
            if not value:
                continue
            p = Path(value).expanduser()
            if not p.is_absolute():
                p = emu / p
            if p.exists():
                return p
    return None


def find_mods_dir(emu: Path) -> Path | None:
    """Find the folder that holds the per-title mod folders.

    Accepts the emulator folder, its `user`/`load` folder or the title folder
    itself, and honours a custom `load_directory` from `qt-config.ini`.
    """
    if not emu or not emu.exists():
        return None
    if emu.name == TITLE_ID:
        return emu
    if (emu / TITLE_ID).is_dir():
        return emu / TITLE_ID
    load = _load_directory(emu)
    if load is not None:
        return load / TITLE_ID
    for cand in (emu / "user" / "load" / TITLE_ID, emu / "load" / TITLE_ID,
                 emu / "mods" / "contents" / TITLE_ID, emu / "mods" / TITLE_ID):
        if cand.exists():
            return cand
    if (emu / "user").exists():
        return emu / "user" / "load" / TITLE_ID
    return None


def other_exefs_mods(mods: Path, skip: set[str]) -> list[str]:
    out = []
    if mods.exists():
        for d in sorted(mods.iterdir()):
            if d.name not in skip and (d / "exefs").exists() and any((d / "exefs").glob("*.ips")):
                out.append(d.name)
    return out


# ---------- IPS32 ----------
def read_ips(data: bytes):
    assert data[:5] == b"IPS32"
    i, out = 5, []
    while data[i:i + 4] != b"EEOF":
        off = struct.unpack(">I", data[i:i + 4])[0]
        size = struct.unpack(">H", data[i + 4:i + 6])[0]
        assert size, "RLE records are not supported"
        out.append((off, data[i + 6:i + 6 + size]))
        i += 6 + size
    return out


def merge_ips(*blobs: bytes) -> bytes:
    taken, recs = {}, []
    for n, blob in enumerate(blobs):
        for off, b in read_ips(blob):
            for k in range(off, off + len(b)):
                if k in taken and taken[k] != n:
                    raise InstallError("ips_overlap", f"main+{k - 0x100:#x}")
                taken[k] = n
            recs.append((off, b))
    out = bytearray(b"IPS32")
    for off, b in recs:
        out += struct.pack(">I", off) + struct.pack(">H", len(b)) + b
    return bytes(out + b"EEOF")


# ---------- config block ----------
def patch_config(nso: bytes, s: Settings) -> bytes:
    i = nso.find(b"SHBCFG01")
    if i < 0 or nso.count(b"SHBCFG01") != 1:
        raise InstallError("bad_module", "config block not found")
    version, size = struct.unpack_from("<II", nso, i + 8)
    if version != 1 or size < 0x48:
        raise InstallError("bad_module", f"config version {version}")
    b = bytearray(nso)
    f = i + 16
    b[f + 0] = int(s.stamina)
    b[f + 1] = s.preset
    b[f + 2], b[f + 3], b[f + 4] = int(s.jump), int(s.attack), int(s.sprint)
    b[f + 5], b[f + 6], b[f + 7] = int(s.block), int(s.shoot), int(s.roll)
    b[f + 8] = int(s.combat_only)
    b[f + 9] = int(s.classic)
    struct.pack_into("<HH", b, f + 10, int(s.enemy_hp), int(s.damage))
    b[f + 14], b[f + 15], b[f + 16], b[f + 17] = int(s.hud_rupees), int(s.hud_clock), int(s.clock_24h), int(s.no_heart_drop)
    struct.pack_into("<H", b, f + 18, int(s.sprint_speed))
    b[f + 20] = int(s.songbook)
    return bytes(b)


# ---------- Classic Item Slots v1.4.3 (downloaded from its official release, not bundled) ----------
CLASSIC_VARIANTS = ("default", "playstation", "xbox")
CLASSIC_VERSION = "1.4.3"
CLASSIC_TAG = f"v{CLASSIC_VERSION}"
CLASSIC_ASSETS = {
    "default": f"Classic-Item-Slots-{CLASSIC_TAG}.zip",
    "playstation": f"Classic-Item-Slots-{CLASSIC_TAG}-PlayStation.zip",
    "xbox": f"Classic-Item-Slots-{CLASSIC_TAG}-Xbox.zip",
}
CLASSIC_URL = "https://github.com/sonofsilvanus/OoTNS2-Classic-Item-Slots/releases/download/{tag}/{name}"
CACHE = paths.cache_dir()
# the 14 main offsets its patch file touches (checked after unpacking, so a wrong archive is never installed)
CLASSIC_SITES = {0x33A927C, 0x33AAC34, 0x33BD928, 0x33C9AB4, 0x34694F8, 0x3469524, 0x3469550, 0x346966C,
                 0x3469698, 0x33D7124, 0x33D8CC4, 0xD57CE4, 0x33F6894, 0x33E64E0}


def is_classic(d: Path) -> bool:
    try:
        s, ips = d / "exefs" / "subsdk9", d / "exefs" / f"{BUILD_ID}.ips"
        if not (s.exists() and ips.exists() and (d / "romfs").exists() and s.stat().st_size == CLASSIC_SUBSDK_SIZE):
            return False
        return {off - 0x100 for off, _ in read_ips(ips.read_bytes())} == CLASSIC_SITES
    except Exception:
        return False


def _find_classic_in(root: Path) -> Path | None:
    for d in [root] + [p for p in root.rglob("*") if p.is_dir()]:
        if is_classic(d):
            return d
    return None


def fetch_classic(variant: str) -> Path:
    """Reuse the cached copy or download the chosen official release asset from GitHub."""
    if variant not in CLASSIC_VARIANTS:
        raise InstallError("classic_missing", variant)
    dest = CACHE / f"{CLASSIC_VERSION}-{variant}"
    found = _find_classic_in(dest) if dest.exists() else None
    if found:
        return found

    shutil.rmtree(dest, ignore_errors=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = CACHE / f"{variant}.zip.part"
    try:
        url = CLASSIC_URL.format(tag=CLASSIC_TAG, name=CLASSIC_ASSETS[variant])
        req = urllib.request.Request(url, headers={"User-Agent": "super-hero-boost"})
        with urllib.request.urlopen(req, timeout=60) as response, open(tmp, "wb") as out:
            shutil.copyfileobj(response, out)
        dest.mkdir(parents=True)
        with zipfile.ZipFile(tmp) as archive:
            archive.extractall(dest)
    except Exception:
        shutil.rmtree(dest, ignore_errors=True)
        try:
            tmp.unlink()
        except OSError:
            pass
        raise InstallError("classic_download", variant)
    try:
        tmp.unlink()
    except OSError:
        pass
    found = _find_classic_in(dest)
    if not found:
        raise InstallError("classic_invalid", variant)
    return found


# ---------- install ----------
@dataclass
class Result:
    target: Path
    variant: str
    notes: list = field(default_factory=list)      # (key, arg) pairs, localized by the window


def install(emu: Path, s: Settings, classic_variant: str = "default", name: str = MOD_NAME) -> Result:
    mods = find_mods_dir(emu)
    if mods is None:
        raise InstallError("no_mods_dir")
    variant = "classic" if s.classic else "standalone"
    pay = resource_dir() / variant
    if not (pay / "subsdk9").exists():
        raise InstallError("no_payload", variant)
    classic_dir = fetch_classic(classic_variant) if s.classic else None
    target = mods / name
    mods.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if not (target / MARKER).exists():
            raise InstallError("exists_not_ours", str(target))
        try:
            shutil.rmtree(target)
        except OSError:
            raise InstallError("in_use", str(target))
    (target / "exefs").mkdir(parents=True)
    (target / MARKER).write_text(json.dumps({"variant": variant, **s.to_dict()}))

    (target / "exefs" / "subsdk9").write_bytes(patch_config((pay / "subsdk9").read_bytes(), s))
    ours = (pay / "ours.ips").read_bytes()
    if classic_dir:
        cips = (classic_dir / "exefs" / f"{BUILD_ID}.ips").read_bytes()
        (target / "exefs" / f"{BUILD_ID}.ips").write_bytes(merge_ips(cips, ours))
        shutil.copy2(classic_dir / "exefs" / "subsdk9", target / "exefs" / "subsdk8")
        shutil.copytree(classic_dir / "romfs", target / "romfs")
    else:
        (target / "exefs" / f"{BUILD_ID}.ips").write_bytes(ours)

    res = Result(target, variant)
    if s.no_heart_drop:                       # romfs files generated from the game's own data (tools/make_romfs_opts.py)
        src = pay.parent / "romfs_opts" / "no_heart_drop"
        if src.exists():
            shutil.copytree(src, target / "romfs", dirs_exist_ok=True)
        else:
            # The option needs a file generated from the user's own game dump. Never block the
            # rest of the installation just because this optional file was not built.
            res.notes.append(("no_heart_drop_missing", ""))

    for opt, enabled in (("enemy_double", s.enemy_double), ("enemy_speed", s.enemy_speed)):
        if not enabled:
            continue
        src = pay.parent / "romfs_opts" / opt
        if src.exists():
            shutil.copytree(src, target / "romfs", dirs_exist_ok=True)
        else:
            res.notes.append((opt + "_missing", ""))

    conflicts = other_exefs_mods(mods, {name})
    if conflicts:
        res.notes.append(("conflicts", ", ".join(conflicts)))
    return res


def uninstall(emu: Path, name: str = MOD_NAME) -> bool:
    mods = find_mods_dir(emu)
    t = mods / name if mods else None
    if t and t.exists() and (t / MARKER).exists():
        shutil.rmtree(t)
        return True
    return False
