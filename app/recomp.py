"""Hookshot / Longshot install logic for the companion app.

Hookshot and Longshot are static recompilations: the game's code is translated to C and compiled into
`bin/hookshot` / `bin/longshot.exe`, and `image.bin` holds the guest image. An `exefs` folder inside a mod is ignored
("the code is compiled ahead of time"), so the module has to be built into the game. This module:

  * patches `.longshot_exefs/main` and writes `subsdk9` (with the chosen configuration) before a rebuild,
  * copies the selected romfs files to `<game>/mods/Super-Hero-Boost/romfs` (the recompilers' own mod layout),
  * can update the configuration and romfs without rebuilding (the config block lives in `image.bin` too),
  * runs the builder's `nx2/make_game.py --update` with its bundled toolchain, streaming progress,
  * restores the original executable and image from `.shb-backup` on uninstall.

All errors are `InstallError(key, arg)` so the window can translate them.
"""
from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path

import installer as I

MOD_NAME = "Super-Hero-Boost"
BACKUP = ".shb-backup"
CONFIG_MAGIC = b"SHBCFG01"
CONFIG_SIZE = 72
MODULE_BUILD = "e0f3ccfa"   # the game build the IPS and the module are made for (main's NSO module id)
# Longshot, Hookshot and ReLink are the same kind of static recompilation (an exefs, image.bin, a romfs and a
# launcher beside a game exe in bin/). The folder name and the exe say which one it is.
EXEFS_NAMES = (".longshot_exefs", ".hookshot_exefs", ".relink_exefs")
EXE_NAMES = (Path("bin") / "longshot.exe", Path("bin") / "hookshot.exe", Path("bin") / "hookshot",
             Path("bin") / "relink-game.exe")
LAUNCHER_NAMES = ("longshot.exe", "hookshot.exe", "hookshot", "ReLink.exe", "relink.exe")
BUILDER_NAMES = ("LongshotBuilder", "HookshotBuilder", "ReLink")
BUILDER_ROOTS = ("LongshotLauncher", "HookshotLauncher", "ReLink")
# Files the builders regenerate on every build: never copied (some are gigabytes) and deleted on uninstall, so a
# stale cache of the modded build cannot meet the restored game.
VOLATILE = (
    "cache/longshot_pipelines.bin", "longshot_pipelines.bin",
    "relink_programs.bin", "relink_programs.idx", "relink_pipelines.bin",
    "relink_pipeline_states.bin", "relink_shaders.bin", "relink_computes.bin",
    "relink_pipelines_warm.txt",
)
# Folders the builders write (their own dump repair mod).
VOLATILE_DIRS = ("mods/00-dump-repair",)


def flavor(game: Path) -> str:
    """'relink', 'hookshot' or 'longshot', from the exefs folder the game keeps."""
    name = exefs_of(game).name
    if name == ".relink_exefs":
        return "relink"
    if name == ".hookshot_exefs":
        return "hookshot"
    return "longshot"


def _env_prefix(game: Path) -> str:
    return "RELINK" if flavor(game) == "relink" else "LONGSHOT"


def launcher_options(game: Path) -> dict:
    """How the game was built (DLSS, FSR, XeSS), as its launcher remembers it.

    A rebuild that ignores these silently changes the renderer: the DLSS path is compiled out, the ngx runtime is
    removed and the game can stop on a setting it no longer has. ReLink keeps them in launcher.ini; the Longshot and
    Hookshot launchers in settings.json, with the per-folder entry of builds.json."""
    home = Path(os.environ.get("LOCALAPPDATA", ""))
    opt = {"dlss": False, "dlssLicense": False, "fsr": False, "fsrLicense": False,
           "xess": False, "xessLicense": False, "ngx": None, "launcher": None}
    if flavor(game) == "relink":
        ini = home / "ReLink" / "launcher.ini"
        opt["launcher"] = str(ini) if ini.is_file() else None
        try:
            for line in ini.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip().startswith("nvidia_dlss="):
                    opt["dlss"] = line.split("=", 1)[1].strip() == "1"
        except OSError:
            pass
        opt["ngx"] = home / "ReLink" / "ngx-sdk"
    else:
        base = home / "LongshotLauncher"
        if not base.is_dir():
            base = home / "HookshotLauncher"
        opt["launcher"] = str(base / "settings.json") if (base / "settings.json").is_file() else None
        try:
            settings = json.loads((base / "settings.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            settings = {}
        for key in ("dlss", "dlssLicense", "fsr", "fsrLicense", "xess", "xessLicense"):
            opt[key] = bool(settings.get(key))
        try:
            builds = json.loads((base / "builds.json").read_text(encoding="utf-8")).get("builds", [])
        except (OSError, ValueError):
            builds = []
        for b in builds:
            try:
                same = Path(str(b.get("folder", ""))).resolve() == game.resolve()
            except OSError:
                same = False
            if same:
                for key in ("dlss", "fsr", "xess"):
                    opt[key] = bool(b.get(key, opt[key]))
        opt["ngx"] = base / "ngx-sdk"
    if not opt["ngx"] or not opt["ngx"].is_dir():
        opt["ngx"] = None
    return opt


_proc: subprocess.Popen | None = None
_cancel = threading.Event()


@dataclass
class Result:
    target: Path
    rebuilt: bool
    notes: list = field(default_factory=list)


# --------------------------------------------------------------------------- paths / detection

def find_game(path) -> Path | None:
    """The game folder (the one with `.longshot_exefs`/`.hookshot_exefs` and `bin/longshot.exe`)."""
    if not path:
        return None
    p = Path(path).expanduser()
    if not p.exists():
        return None
    if p.is_file():
        p = p.parent
    candidates = [p]
    if p.name.lower() == "bin":
        candidates.append(p.parent)
    for c in candidates:
        if any((c / n / "main").exists() for n in EXEFS_NAMES) and any((c / e).exists() for e in EXE_NAMES):
            return c
    # a folder prepared but not run yet: accept it if the exefs is there
    for c in candidates:
        if any((c / n / "main").exists() for n in EXEFS_NAMES):
            return c
    return None


def exefs_of(game: Path) -> Path:
    for n in EXEFS_NAMES:
        if (game / n / "main").exists():
            return game / n
    raise I.InstallError("recomp_no_game", str(game))


def exe_of(game: Path) -> Path | None:
    for e in EXE_NAMES:
        if (game / e).exists():
            return game / e
    return None


def expected_exefs(builder: Path | None) -> str | None:
    """The folder name the builder's --update reads (Longshot keeps `.longshot_exefs`)."""
    if not builder:
        return None
    try:
        txt = (builder / "tools" / "nx2" / "make_game.py").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in txt.splitlines():
        if "kept" in line and "os.path.join(out" in line:
            for n in EXEFS_NAMES:
                if n in line:
                    return n
    for n in EXEFS_NAMES:
        if '"%s"' % n in txt or "'%s'" % n in txt:
            return n
    return None


def is_builder(path: Path) -> bool:
    return (path / "tools" / "nx2" / "make_game.py").is_file()


def find_builder(game: Path | None = None) -> Path | None:
    """The builder folder (the one with tools/nx2/make_game.py) for this game.

    Longshot and Hookshot keep it in `%LOCALAPPDATA%\\LongshotLauncher|HookshotLauncher\\toolchains\\<version>\\…Builder`;
    ReLink in `%LOCALAPPDATA%\\ReLink\\versions\\<version>\\ReLink`. The environment variables win, then the newest
    folder found, then one beside the game."""
    for name in ("LONGSHOT_BUILDER", "HOOKSHOT_BUILDER", "RELINK_BUILDER"):
        env = os.environ.get(name)
        if env and is_builder(Path(env)):
            return Path(env)
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    found: list[Path] = []
    for root in BUILDER_ROOTS:
        base = local / root
        if not base.is_dir():
            continue
        try:
            for pat in ("toolchains/*", "versions/*", "versions/*/*"):
                for p in base.glob(pat):
                    if p.name in BUILDER_NAMES and is_builder(p):
                        found.append(p)
                    else:
                        for name in BUILDER_NAMES:
                            q = p / name
                            if q.is_dir() and is_builder(q):
                                found.append(q)
        except OSError:
            pass
    if game:
        for rel in (("LongshotBuilder",), ("HookshotBuilder",), ("ReLink",),
                    ("..", "LongshotBuilder"), ("..", "HookshotBuilder"), ("..", "ReLink")):
            p = game.joinpath(*rel)
            if is_builder(p):
                found.append(p)
    return sorted(set(found))[-1] if found else None


def find_work(game: Path | None = None) -> Path | None:
    """The build cache folder the launchers use, so a rebuild is incremental instead of a full recompile."""
    home = Path(os.environ.get("LOCALAPPDATA", ""))
    relink = False
    if game:
        try:
            relink = flavor(game) == "relink"
        except I.InstallError:
            relink = False
    order = ("ReLink",) if relink else ("LongshotLauncher", "HookshotLauncher", "ReLink")
    for name in order:
        base = home / name
        if not base.is_dir():
            continue
        try:
            w = json.loads((base / "settings.json").read_text(encoding="utf-8")).get("work")
            if w and Path(w).is_dir():
                return Path(w)
        except (OSError, ValueError):
            pass
        if (base / "work").is_dir():
            return base / "work"
        if name == "ReLink" and ((base / "build_times.json").is_file() or (base / "objcache").is_dir()):
            return base   # ReLink keeps objcache/, image/, build_times.json in its own folder
    if game:
        for cand in (game.parent / "temp", game / ".shb-work"):
            if cand.is_dir():
                return cand
    return None


def payload_dir() -> Path:
    return I.resource_dir()


def game_running() -> bool:
    """The recompiled game (or a builder) is running: the update cannot replace it."""
    names = {"longshot.exe", "hookshot.exe", "hookshot", "longshot"}
    if os.name == "nt":
        try:
            out = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), timeout=10).stdout
            for line in out.splitlines():
                n = line.split(",")[0].strip('"').lower() if line else ""
                if n in names:
                    return True
        except (OSError, subprocess.SubprocessError):
            return False
    else:
        try:
            out = subprocess.run(["pgrep", "-fl", "longshot|hookshot"], capture_output=True, text=True,
                                 timeout=5).stdout
            return bool(out.strip())
        except (OSError, subprocess.SubprocessError):
            return False
    return False


_built_cache: dict = {}


def is_built(game: Path) -> bool:
    """The executable was rebuilt with the module (it differs from the pre-install backup)."""
    try:
        exefs = exefs_of(game)
    except I.InstallError:
        return False
    mod = exefs / "subsdk9"
    img = game / "image.bin"
    exe = exe_of(game)
    if not mod.exists() or not img.exists() or not exe:
        return False
    bak = game / BACKUP / "files" / exe.relative_to(game).as_posix()
    if not bak.exists():
        bak = game / BACKUP / exe.name
    try:
        key = (str(game), img.stat().st_mtime_ns, exe.stat().st_mtime_ns, mod.stat().st_mtime_ns,
               bak.stat().st_mtime_ns if bak.exists() else 0,
               bak.stat().st_size if bak.exists() else 0)
    except OSError:
        return False
    if key in _built_cache:
        return _built_cache[key]
    try:
        # The builder writes a new executable; a plain `--no-build` leaves the old one (the backup).
        ok = not bak.exists() or exe.stat().st_size != bak.stat().st_size or \
            exe.stat().st_mtime_ns != bak.stat().st_mtime_ns
        if ok:
            with open(img, "rb") as f:
                ok = f.read().find(CONFIG_MAGIC) >= 0
    except OSError:
        ok = False
    _built_cache.clear()
    _built_cache[key] = ok
    return ok


# --------------------------------------------------------------------------- main / config / romfs

def _read(data: bytes) -> bytes:
    i = data.find(CONFIG_MAGIC)
    if i < 0:
        raise I.InstallError("bad_module", "config block not found")
    return data[i:i + CONFIG_SIZE]


def _patch_bytes(data: bytes, s: I.Settings) -> bytes:
    i = data.find(CONFIG_MAGIC)
    if i < 0:
        raise I.InstallError("bad_module", "config block not found")
    cfg = I.patch_config(data[i:i + CONFIG_SIZE], s)
    return data[:i] + cfg + data[i + CONFIG_SIZE:]


def main_build_id(main: Path) -> str:
    """The NSO module id (header +0x40, 32 bytes) as hex: the builders call the first 8 characters the build."""
    try:
        with open(main, "rb") as f:
            head = f.read(0x60)
    except OSError:
        return ""
    return head[0x40:0x60].hex()


def patch_main(main: Path, ips: Path) -> int:
    data = bytearray(main.read_bytes())
    text_off = struct.unpack_from("<I", data, 0x10)[0]
    delta = text_off - 0x100
    n = 0
    for off, patch in I.read_ips(ips.read_bytes()):
        at = off + delta
        if data[at:at + len(patch)] != patch:
            data[at:at + len(patch)] = patch
            n += 1
    main.write_bytes(bytes(data))
    return n


def _backup_candidates(game: Path, exefs_name: str) -> list[str]:
    """Every file the install and the builder's finish step can write, replace or remove, as game-relative paths.

    The builders stage their BESIDE list (the game exe, the renderer, SDL, ffmpeg, the VC runtime for FSR) into bin/
    when a launcher exists, write image.bin and their caches, replace the root launcher and remove the old loose
    libraries. Our install patches exefs/main and writes exefs/subsdk9. ReLink uses its own names."""
    if exefs_name == ".relink_exefs":
        rels = [
            "image.bin", "relink_prepared.bin", "relink_version.txt",
            "ReLink.exe", "relink.exe", "relink-game.exe", "relink-game.map",
            "bin/relink-game.exe", "bin/relink_vk.dll", "bin/relink_vk.so",
            "bin/SDL2.dll", "bin/SDL3.dll", "bin/libSDL2-2.0.so.0",
            "bin/wgpu_native.dll", "bin/amd_fidelityfx_vk.dll", "bin/LICENSE-FidelityFX.txt",
            "bin/vcrt/msvcp140.dll", "bin/vcrt/vcruntime140.dll", "bin/vcrt/vcruntime140_1.dll",
            "wheel/icons.bin", "wheel/names.bin", "wheel/sounds.bin",
            "language.txt", "relink_options.ini",
            f"{exefs_name}/main", f"{exefs_name}/subsdk9",
        ]
    else:
        rels = [
            "image.bin", "longshot_prepared.bin",
            "longshot.exe", "hookshot.exe", "hookshot", "longshot",
            "longshot.map", "longshot-game.exe", "wgpu_native.dll",
            "bin/longshot.exe", "bin/hookshot.exe", "bin/hookshot", "bin/longshot",
            "bin/longshot_vk.dll", "bin/longshot_vk.so",
            "bin/SDL2.dll", "bin/SDL3.dll", "bin/libSDL2-2.0.so.0",
            "bin/wgpu_native.dll", "bin/longshot.map", "bin/longshot-game.exe",
            f"{exefs_name}/main", f"{exefs_name}/subsdk9",
        ]
    for d in (game / "bin", game):
        if d.is_dir():
            try:
                for f in d.iterdir():
                    if f.is_file() and f.suffix.lower() == ".dll" and f.name.startswith(("av", "sw")):
                        rel = f.relative_to(game).as_posix()
                        if rel not in rels:
                            rels.append(rel)
            except OSError:
                pass
    return rels


MANIFEST_VERSION = 3


def backup_once(game: Path, exefs_original: str | None = None) -> Path:
    """Snapshot, once, everything the install and the rebuild can change.

    Files that exist are copied under `.shb-backup/files/` (folders too); files that do not exist are recorded as
    created, so the uninstall deletes them instead of leaving a half-built game. The builders' caches are only
    recorded: they are regenerated on every build (some are gigabytes) and deleted on uninstall, so a stale cache
    of the modded build cannot meet the restored game. The manifest keeps the first snapshot: installing again never
    overwrites the originals. Older backups (flat files in `.shb-backup/`, or a version 2 manifest) keep working."""
    bak = game / BACKUP
    files = bak / "files"
    files.mkdir(parents=True, exist_ok=True)
    man_path = bak / "manifest.json"
    man = None
    try:
        data = json.loads(man_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("version") in (2, MANIFEST_VERSION):
            man = data
    except (OSError, ValueError):
        man = None
    if man is None:
        man = {"version": MANIFEST_VERSION, "exefs": exefs_original or exefs_of(game).name, "files": []}
    else:
        man["version"] = MANIFEST_VERSION
    known = {e.get("path") for e in man.get("files", []) if isinstance(e, dict)}
    current = exefs_of(game).name          # (the folder may have been renamed to match the builder)
    for rel in _backup_candidates(game, current):
        if rel in known:
            continue
        src = game / rel
        entry = {"path": rel}
        if src.is_file():
            dst = files / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            entry["kind"] = "file"
        elif src.is_dir():
            dst = files / rel
            if dst.exists():
                shutil.rmtree(dst, ignore_errors=True)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dst)
            entry["kind"] = "dir"
        else:
            entry["kind"] = "created"
        man["files"].append(entry)
        known.add(rel)
    for rel in VOLATILE:
        if rel not in known:
            man["files"].append({"path": rel, "kind": "volatile"})
            known.add(rel)
    for rel in VOLATILE_DIRS:
        if rel not in known:
            man["files"].append({"path": rel, "kind": "volatile-dir"})
            known.add(rel)
    man_path.write_text(json.dumps(man, indent=1), encoding="utf-8")
    return bak


def _restore_backup(game: Path, bak: Path) -> bool:
    """Undo everything the snapshot recorded: copy the saved files back and delete the ones that were not there."""
    restored = False
    man = None
    try:
        data = json.loads((bak / "manifest.json").read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("version") in (2, MANIFEST_VERSION):
            man = data
    except (OSError, ValueError):
        man = None
    if man is not None:
        files = bak / "files"
        for e in man.get("files", []):
            if not isinstance(e, dict):
                continue
            rel = str(e.get("path") or "").replace("\\", "/")
            if not rel or rel.startswith("/") or ".." in rel.split("/") or ":" in rel:
                continue
            dst = game / rel
            kind = e.get("kind")
            try:
                if kind == "file":
                    src = files / rel
                    if src.is_file():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                        restored = True
                elif kind == "dir":
                    src = files / rel
                    if src.is_dir():
                        if dst.exists():
                            shutil.rmtree(dst, ignore_errors=True)
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copytree(src, dst)
                        restored = True
                elif kind in ("volatile", "volatile-dir"):
                    if dst.is_dir():
                        shutil.rmtree(dst, ignore_errors=True)
                        restored = True
                    elif dst.is_file():
                        dst.unlink()
                        restored = True
                else:   # created by the install/build: removed again
                    if dst.is_dir():
                        shutil.rmtree(dst, ignore_errors=True)
                        restored = True
                    elif dst.is_file():
                        dst.unlink()
                        restored = True
            except OSError:
                pass
        name = man.get("exefs")
        if name in EXEFS_NAMES:
            for other in EXEFS_NAMES:
                p = game / other
                if other != name and p.exists() and not (game / name).exists():
                    try:
                        p.rename(game / name)
                        restored = True
                    except OSError:
                        pass
    # older backups: flat copies in .shb-backup/ (main, longshot.exe, hookshot, image.bin, longshot_prepared.bin)
    for src, dst in ((bak / "main", exefs_of(game) / "main"),
                     (bak / "longshot.exe", game / "bin" / "longshot.exe"),
                     (bak / "hookshot", game / "bin" / "hookshot"),
                     (bak / "hookshot.exe", game / "bin" / "hookshot.exe"),
                     (bak / "image.bin", game / "image.bin"),
                     (bak / "longshot_prepared.bin", game / "longshot_prepared.bin")):
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            restored = True
    return restored



def write_module(game: Path, s: I.Settings) -> None:
    src = payload_dir() / "standalone" / "subsdk9"
    if not src.exists():
        raise I.InstallError("no_payload", "standalone")
    (exefs_of(game) / "subsdk9").write_bytes(_patch_bytes(src.read_bytes(), s))


def write_image(game: Path, s: I.Settings) -> bool:
    img = game / "image.bin"
    if not img.exists():
        return False
    data = img.read_bytes()
    if CONFIG_MAGIC not in data:
        return False
    img.write_bytes(_patch_bytes(data, s))
    return True


def install_romfs(game: Path, s: I.Settings) -> tuple[int, list]:
    """Copy the selected romfs files into the recompiler's mod folder."""
    pay = payload_dir()
    target = game / "mods" / MOD_NAME / "romfs"
    notes = []
    if target.parent.exists():
        shutil.rmtree(target.parent)
    copied = 0

    def copy(src: Path):
        nonlocal copied
        if not src.exists():
            return False
        for f in src.rglob("*"):
            if f.is_file():
                dst = target / f.relative_to(src)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
                copied += 1
        return True

    if s.button_mapping:
        style = s.button_style if s.button_style in I.BUTTON_STYLES else "switch"
        copy(pay / "button_romfs" / style)
        copy(pay / "button_romfs" / "common")
    if s.no_heart_drop and not copy(pay / "romfs_opts" / "no_heart_drop"):
        notes.append(("no_heart_drop_missing", ""))
    for opt, enabled in (("enemy_double", s.enemy_double),
                         ("farore_outdoor", s.farore_outdoor),
                         ("great_fairy", s.great_fairy)):
        if enabled and not copy(pay / "romfs_opts" / opt):
            notes.append((opt + "_missing", ""))
    notes.extend(I.install_enemy_mods(target, s, pay))
    if copied:
        (target.parent / ".super-hero-boost").write_text(
            json.dumps({"variant": "recomp", **s.to_dict()}, indent=1))
    return copied, notes


# --------------------------------------------------------------------------- build

STAGE_RANGE = {
    "read": (0.00, 0.03),
    "lift": (0.03, 0.15),
    "compile": (0.15, 0.90),
    "shaders": (0.90, 0.99),
}


def cancel() -> None:
    _cancel.set()
    p = _proc
    if p is not None and p.poll() is None:
        try:
            p.terminate()
        except OSError:
            pass


def _python(builder: Path) -> Path:
    tools = builder / "tools"
    for p in (tools / "python" / "python.exe", tools / "python" / "bin" / "python3", tools / "python" / "bin" / "python"):
        if p.exists():
            return p
    return Path(sys.executable)


def _vk_headers_ok(builder: Path, work: Path | None) -> bool:
    """Ask the builder itself whether it can find the Vulkan, SPIR-V and VMA headers.

    Some builder packages keep the CPM cache at tools/cpm, which the builder finds by itself; a source
    build may not ship it at all. That is when make_game.py stops with "no headers for longshot_vk.dll".
    """
    tools = builder / "tools"
    code = ("import sys; sys.path.insert(0, 'nx2'); import build; "
            "print(1 if all(build.vulkan_headers(sys.argv[1] if len(sys.argv) > 1 else None)) else 0)")
    cmd = [str(_python(builder)), "-I", "-c", code]
    if work:
        cmd.append(str(work))
    try:
        r = subprocess.run(cmd, cwd=str(tools), capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=90,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError):
        return True   # cannot tell: let the builder run its normal path
    if r.returncode:
        return True
    lines = [line.strip() for line in (r.stdout or "").splitlines() if line.strip()]
    return (lines[-1] if lines else "") == "1"


def _vk_prebuilt(game: Path, work: Path | None) -> Path | None:
    """A copy of the game's working renderer, safe to hand to make_game.py as <FLAVOR>_VK_PREBUILT.

    The copy lives in the build work folder: make_game.py copies the prebuilt back beside the new exe, and
    source and destination must not be the same file (it builds in place)."""
    names = ("relink_vk.dll", "relink_vk.so") if flavor(game) == "relink" else ("longshot_vk.dll", "longshot_vk.so")
    for sub in ("bin", ""):
        for name in names:
            src = game / sub / name if sub else game / name
            if not src.is_file():
                continue
            out = Path(work) if work else game / ".shb-work"
            try:
                out.mkdir(parents=True, exist_ok=True)
                dst = out / ("shb-" + name)
                if src.resolve() != dst.resolve():
                    shutil.copy2(src, dst)
                return dst
            except OSError:
                return None
    return None


def build_env(game: Path, builder: Path, work: Path | None) -> tuple[dict, str | None]:
    """Environment for make_game.py: the packaged CPM cache, the renderer when the builder cannot compile it
    (missing Vulkan/VMA headers) and the DLSS SDK the game was built with."""
    env = dict(os.environ)
    prefix = _env_prefix(game)
    cpm = builder / "tools" / "cpm"
    if cpm.is_dir() and not env.get("RX_CPM"):
        env["RX_CPM"] = str(cpm)
    opt = launcher_options(game)
    if opt["dlss"] and not env.get(f"{prefix}_NGX_SDK") and opt["ngx"]:
        env[f"{prefix}_NGX_SDK"] = str(opt["ngx"])
    if not env.get(f"{prefix}_VK_PREBUILT") and not _vk_headers_ok(builder, work):
        pre = _vk_prebuilt(game, work)
        if pre is not None:
            env[f"{prefix}_VK_PREBUILT"] = str(pre)
            return env, "Vulkan headers not found: reusing the installed renderer (%s)" % pre.name
    return env, None


def build(game: Path, builder: Path, work: Path | None, progress=None, log=None) -> None:
    """Run the builder's update, reporting (fraction, text) and every output line."""
    global _proc
    _cancel.clear()
    tools = builder / "tools"
    if not (tools / "nx2" / "make_game.py").exists():
        raise I.InstallError("recomp_no_builder", str(builder))
    if work is None:
        work = game / ".shb-work"
    try:
        Path(work).mkdir(parents=True, exist_ok=True)
    except OSError:
        work = None
    cmd = [str(_python(builder)), "-I", "nx2/make_game.py", "--update", str(game), "--jobs", "0"]
    if work:
        cmd += ["--work", str(work)]
    env, note = build_env(game, builder, work)
    prefix = _env_prefix(game)
    opt = launcher_options(game)
    if opt["dlss"] and not env.get(f"{prefix}_NGX_SDK"):
        if opt["dlssLicense"]:
            cmd += ["--fetch-ngx-sdk", "--accept-nvidia-license"]
        else:
            raise I.InstallError("recomp_no_dlss", str(opt["launcher"] or prefix))
    elif opt["dlss"]:
        note = ((note + "; ") if note else "") + "keeping DLSS (%s)" % Path(env[f"{prefix}_NGX_SDK"]).name
    if flavor(game) != "relink" and opt["fsr"]:
        cmd += ["--fsr"]
    env.update({"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    if note and log:
        log(note)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    stage = "read"
    fraction = 0.0

    def report(text):
        if progress:
            progress(min(1.0, max(0.0, fraction)), text, stage)

    report("starting")
    try:
        _proc = subprocess.Popen(cmd, cwd=str(tools), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 text=True, encoding="utf-8", errors="replace", bufsize=1, env=env,
                                 creationflags=flags)
    except OSError as ex:
        raise I.InstallError("recomp_no_builder", str(ex))
    last = []
    with _proc:
        for line in _proc.stdout or ():
            line = line.rstrip("\r\n")
            if not line:
                continue
            last.append(line)
            last = last[-40:]
            if line.startswith("@@stage "):
                parts = line.split(" ", 2)
                stage = parts[1] if len(parts) > 1 else stage
                fraction = STAGE_RANGE.get(stage, (fraction, fraction))[0]
                report(parts[2] if len(parts) > 2 else stage)
            elif line.startswith("@@progress "):
                try:
                    p = float(line.split(" ", 1)[1])
                except ValueError:
                    continue
                lo, hi = STAGE_RANGE.get(stage, (0.0, 1.0))
                fraction = lo + max(0.0, min(1.0, p)) * (hi - lo)
                report("")
            elif line.startswith("@@plan "):
                report("")
            elif line.startswith("@@eta "):
                report("")
            elif line.startswith("@@error "):
                try:
                    _proc.terminate()
                except OSError:
                    pass
                raise I.InstallError("recomp_build_failed", line[8:])
            elif line.startswith("@@"):
                continue
            else:
                if log:
                    log(line)
            if _cancel.is_set():
                raise I.InstallError("recomp_cancelled")
        code = _proc.wait()
    _proc = None
    if _cancel.is_set():
        raise I.InstallError("recomp_cancelled")
    if code:
        raise I.InstallError("recomp_build_failed", "\n".join(last[-8:]))
    if progress:
        progress(1.0, "done", "done")


# --------------------------------------------------------------------------- install / remove

def install(game_path, s: I.Settings, rebuild: bool = True, builder_path=None, work=None,
            progress=None, log=None) -> Result:
    game = find_game(game_path)
    if game is None:
        raise I.InstallError("recomp_no_game", str(game_path))
    if game_running():
        raise I.InstallError("recomp_running", str(game))
    builder = None
    exefs_name = exefs_of(game).name          # (the name the folder had before any rename: restored on uninstall)
    if rebuild:
        builder = Path(builder_path).expanduser() if builder_path else find_builder(game)
        exp = expected_exefs(builder)
        ex = exefs_of(game)
        if exp and ex.name != exp:
            dest = game / exp
            if not dest.exists():
                ex.rename(dest)
    exefs = exefs_of(game)
    ips = payload_dir() / "standalone" / "ours.ips"
    if not ips.exists():
        raise I.InstallError("no_payload", "standalone")
    bid = main_build_id(exefs / "main")
    if bid and not bid.startswith(MODULE_BUILD):
        raise I.InstallError("recomp_bad_build", bid[:8])
    backup_once(game, exefs_name)
    n = patch_main(exefs / "main", ips)
    write_module(game, s)
    copied, notes = install_romfs(game, s)
    write_image(game, s)

    if rebuild:
        if not builder or not (Path(builder) / "tools" / "nx2" / "make_game.py").exists():
            raise I.InstallError("recomp_no_builder", str(builder_path or ""))
        w = Path(work).expanduser() if work else find_work(game)
        build(game, Path(builder), w, progress=progress, log=log)
        write_image(game, s)          # the new image may have been written by the lift
    return Result(game, rebuild, notes)


def apply_settings(game_path, s: I.Settings) -> Result:
    """Configuration and romfs only: no rebuild (the code is already in the executable)."""
    game = find_game(game_path)
    if game is None:
        raise I.InstallError("recomp_no_game", str(game_path))
    if game_running():
        raise I.InstallError("recomp_running", str(game))
    if not (exefs_of(game) / "subsdk9").exists():
        raise I.InstallError("recomp_needs_build", str(game))
    bid = main_build_id(exefs_of(game) / "main")
    if bid and not bid.startswith(MODULE_BUILD):
        raise I.InstallError("recomp_bad_build", bid[:8])
    backup_once(game)
    write_module(game, s)
    copied, notes = install_romfs(game, s)
    if not write_image(game, s):
        raise I.InstallError("recomp_needs_build", str(game))
    return Result(game, False, notes)


def uninstall(game_path) -> bool:
    game = find_game(game_path)
    if game is None:
        return False
    exefs = exefs_of(game)
    bak = game / BACKUP
    restored = _restore_backup(game, bak)
    for name in ("subsdk9", "subsdk9.bak-longshot"):
        p = exefs / name
        if p.exists():
            p.unlink()
            restored = True
    mods = game / "mods" / MOD_NAME
    if mods.exists():
        shutil.rmtree(mods)
        restored = True
    return restored
