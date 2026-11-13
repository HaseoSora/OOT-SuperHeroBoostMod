"""Install logic of the OOT Master Mod companion app. No compiler involved: it only patches the config block
inside the prebuilt module, merges the IPS patch files and copies files into the emulator's mod folder."""
import hashlib
import io
import json
import os
import re
import shutil
import struct
import sys
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

TITLE_ID = "0400486024DEC000"
BUILD_ID = "E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348"
MOD_NAME = "00-OOT-Master"
MARKER = ".oot-master-mod"
CLASSIC_SUBSDK_SIZE = 20744          # Classic Item Slots' module (identifies the original mod)


def resource_dir() -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "payload"


@dataclass
class Settings:
    classic: bool = True
    stamina: bool = True
    preset: int = 0                 # 0 hardcore, 1 combat only, 2 sprint only, 3 advanced
    jump: bool = True
    attack: bool = True
    sprint: bool = True
    block: bool = True
    shoot: bool = True
    roll: bool = True
    combat_only: bool = False

    def to_dict(self): return dict(self.__dict__)


# ---------- emulator / mods folder detection ----------
def find_mods_dir(emu: Path) -> Path | None:
    """<emu>/user/load/<title id>, honouring a custom load directory from qt-config.ini when present."""
    cfg = emu / "user" / "config" / "qt-config.ini"
    if cfg.exists():
        txt = cfg.read_text(errors="replace")
        m = re.search(r"^load_directory(?:\\default)?=(.+)$", txt, re.M)
        for m in re.finditer(r"^load_directory=(.+)$", txt, re.M):
            p = Path(m.group(1).strip().strip('"'))
            if p.exists():
                return p / TITLE_ID
    d = emu / "user" / "load"
    return d / TITLE_ID if d.exists() or (emu / "user").exists() else None


# the 14 main offsets patched by the original Classic Item Slots (identifies it among similar mods)
CLASSIC_SITES = {0x33A927C, 0x33AAC34, 0x33BD928, 0x33C9AB4, 0x34694F8, 0x3469524, 0x3469550, 0x346966C,
                 0x3469698, 0x33D7124, 0x33D8CC4, 0xD57CE4, 0x33F6894, 0x33E64E0}


def is_classic(d: Path) -> bool:
    """An unmodified Classic Item Slots folder: its module size and exactly its 14 patched sites."""
    try:
        s = d / "exefs" / "subsdk9"
        ips = d / "exefs" / f"{BUILD_ID}.ips"
        if not (s.exists() and ips.exists() and (d / "romfs").exists()):
            return False
        if s.stat().st_size != CLASSIC_SUBSDK_SIZE:
            return False
        return {off - 0x100 for off, _ in read_ips(ips.read_bytes())} == CLASSIC_SITES
    except Exception:
        return False


def find_classic(mods: Path) -> Path | None:
    """The user's installed Classic Item Slots mod (original, untouched)."""
    if not mods.exists():
        return None
    for d in sorted(mods.iterdir()):
        if d.is_dir() and is_classic(d):
            return d
    return None


def other_exefs_mods(mods: Path, skip: set[str]) -> list[str]:
    out = []
    if mods.exists():
        for d in sorted(mods.iterdir()):
            if d.name in skip:
                continue
            if (d / "exefs").exists() and any((d / "exefs").glob("*.ips")):
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
                    raise ValueError(f"IPS overlap at main+{k - 0x100:#x}")
                taken[k] = n
            recs.append((off, b))
    out = bytearray(b"IPS32")
    for off, b in recs:
        out += struct.pack(">I", off) + struct.pack(">H", len(b)) + b
    return bytes(out + b"EEOF")


# ---------- config block ----------
def patch_config(nso: bytes, s: Settings) -> bytes:
    i = nso.find(b"OOTMCFG1")
    if i < 0 or nso.count(b"OOTMCFG1") != 1:
        raise ValueError("config block not found in the module")
    version, size = struct.unpack_from("<II", nso, i + 8)
    if version != 1 or size < 28:
        raise ValueError(f"unsupported config version {version}")
    b = bytearray(nso)
    f = i + 16
    b[f + 0] = int(s.stamina)
    b[f + 1] = s.preset
    b[f + 2], b[f + 3], b[f + 4] = int(s.jump), int(s.attack), int(s.sprint)
    b[f + 5], b[f + 6], b[f + 7] = int(s.block), int(s.shoot), int(s.roll)
    b[f + 8] = int(s.combat_only)
    b[f + 9] = int(s.classic)
    return bytes(b)


# ---------- Classic Item Slots source (downloaded from its official release page, not shipped) ----------
CLASSIC_REPO = "sonofsilvanus/OoTNS2-Classic-Item-Slots"
CLASSIC_VARIANTS = {"default": "Botones Switch (por defecto)", "playstation": "Botones PlayStation", "xbox": "Botones Xbox"}
CACHE = Path(os.environ.get("APPDATA", str(Path.home()))) / "OotMasterConfig" / "classic"


def _find_classic_in(root: Path) -> Path | None:
    for d in [root] + [p for p in root.rglob("*") if p.is_dir()]:
        if is_classic(d):
            return d
    return None


def fetch_classic(variant: str, log=lambda m: None) -> Path:
    """Download (once) the chosen variant of Classic Item Slots from its GitHub release and return its folder."""
    if variant not in CLASSIC_VARIANTS:
        raise ValueError(variant)
    hdr = {"User-Agent": "oot-master-config", "Accept": "application/vnd.github+json"}
    log("Consultando la última versión de Classic Item Slots…")
    rel = json.load(urllib.request.urlopen(urllib.request.Request(
        f"https://api.github.com/repos/{CLASSIC_REPO}/releases/latest", headers=hdr), timeout=30))
    tag = rel["tag_name"]
    want = {"default": lambda n: not n.endswith(("-Xbox.zip", "-PlayStation.zip")),
            "xbox": lambda n: n.endswith("-Xbox.zip"), "playstation": lambda n: n.endswith("-PlayStation.zip")}[variant]
    asset = next(a for a in rel["assets"] if a["name"].endswith(".zip") and want(a["name"]))
    dest = CACHE / f"{tag}-{variant}"
    found = _find_classic_in(dest) if dest.exists() else None
    if found:
        return found
    log(f"Descargando {asset['name']} ({asset['size'] // 1024} KB)…")
    data = urllib.request.urlopen(urllib.request.Request(asset["browser_download_url"], headers=hdr), timeout=120).read()
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    zipfile.ZipFile(io.BytesIO(data)).extractall(dest)
    found = _find_classic_in(dest)
    if not found:
        raise ValueError(f"La versión {tag} de Classic Item Slots cambió y esta app aún no la soporta.")
    return found


def classic_from_zip(zpath: Path) -> Path:
    dest = CACHE / ("zip-" + hashlib.sha1(str(zpath).encode()).hexdigest()[:8])
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    zipfile.ZipFile(zpath).extractall(dest)
    found = _find_classic_in(dest)
    if not found:
        raise ValueError("Ese .zip no contiene una versión compatible de Classic Item Slots.")
    return found


# ---------- install ----------
@dataclass
class Result:
    target: Path
    variant: str
    notes: list = field(default_factory=list)


def install(emu: Path, s: Settings, classic_dir: Path | None = None, name: str = MOD_NAME,
            classic_variant: str = "", log=lambda m: None) -> Result:
    mods = find_mods_dir(emu)
    if mods is None:
        raise FileNotFoundError("No encuentro la carpeta de mods en el emulador (user/load).")
    mods.mkdir(parents=True, exist_ok=True)
    variant = "classic" if s.classic else "standalone"
    pay = resource_dir() / variant
    if not (pay / "subsdk9").exists():
        raise FileNotFoundError(f"Falta el módulo precompilado ({variant}).")
    res = Result(mods / name, variant)

    if s.classic:
        if not classic_dir and classic_variant:
            classic_dir = fetch_classic(classic_variant, log)       # official release, cached
        classic_dir = classic_dir or find_classic(mods)
        if not classic_dir:
            raise FileNotFoundError("Classic Item Slots está activado pero no encuentro sus archivos "
                                    "(elige una variante para descargarla).")
        if not is_classic(classic_dir):
            raise ValueError("La carpeta de Classic Item Slots no es una versión compatible.")

    target = mods / name
    if target.exists():
        if not (target / MARKER).exists():
            raise FileExistsError(f"{target} existe y no es de esta app; elige otro nombre o bórrala.")
        shutil.rmtree(target)
    (target / "exefs").mkdir(parents=True)
    (target / MARKER).write_text(json.dumps({"variant": variant, **s.to_dict()}))

    nso = patch_config((pay / "subsdk9").read_bytes(), s)
    (target / "exefs" / "subsdk9").write_bytes(nso)
    ours = (pay / "ours.ips").read_bytes()
    if s.classic:
        cips = (classic_dir / "exefs" / f"{BUILD_ID}.ips").read_bytes()
        (target / "exefs" / f"{BUILD_ID}.ips").write_bytes(merge_ips(cips, ours))
        shutil.copy2(classic_dir / "exefs" / "subsdk9", target / "exefs" / "subsdk8")
        shutil.copytree(classic_dir / "romfs", target / "romfs")
        res.notes.append(f"Classic Item Slots tomado de: {classic_dir.name}")
    else:
        (target / "exefs" / f"{BUILD_ID}.ips").write_bytes(ours)

    skip = {name} | ({classic_dir.name} if classic_dir and classic_dir.parent == mods else set())
    conflicts = other_exefs_mods(mods, skip)
    if classic_dir and classic_dir.parent == mods:
        res.notes.append(f"Desactiva el mod original '{classic_dir.name}' en el emulador: ya va incluido.")
    if conflicts:
        res.notes.append("Otros mods con parches de ejecutable (pueden chocar): " + ", ".join(conflicts))
    return res


def uninstall(emu: Path, name: str = MOD_NAME) -> bool:
    mods = find_mods_dir(emu)
    t = mods / name if mods else None
    if t and t.exists() and (t / MARKER).exists():
        shutil.rmtree(t)
        return True
    return False
