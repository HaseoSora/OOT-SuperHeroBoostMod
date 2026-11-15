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
EXEFS_NAMES = (".longshot_exefs", ".hookshot_exefs")
EXE_NAMES = (Path("bin") / "longshot.exe", Path("bin") / "hookshot.exe", Path("bin") / "hookshot")
BUILDER_NAMES = ("LongshotBuilder", "HookshotBuilder")

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


def find_builder(game: Path | None = None) -> Path | None:
    env = os.environ.get("LONGSHOT_BUILDER") or os.environ.get("HOOKSHOT_BUILDER")
    if env and (Path(env) / "tools" / "nx2" / "make_game.py").exists():
        return Path(env)
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    found = []
    for root in (local / "LongshotLauncher" / "toolchains", local / "HookshotLauncher" / "toolchains"):
        if root.is_dir():
            for pat in ("*/LongshotBuilder", "*/HookshotBuilder"):
                for p in root.glob(pat):
                    if (p / "tools" / "nx2" / "make_game.py").exists():
                        found.append(p)
    if game:
        for rel in (("LongshotBuilder",), ("HookshotBuilder",), ("..", "LongshotBuilder"), ("..", "HookshotBuilder")):
            p = game.joinpath(*rel)
            if (p / "tools" / "nx2" / "make_game.py").exists():
                found.append(p)
    return sorted(found)[-1] if found else None


def find_work(game: Path | None = None) -> Path | None:
    for name in ("LongshotLauncher", "HookshotLauncher"):
        cfg = Path(os.environ.get("LOCALAPPDATA", "")) / name / "settings.json"
        try:
            w = json.loads(cfg.read_text(encoding="utf-8")).get("work")
            if w and Path(w).is_dir():
                return Path(w)
        except (OSError, ValueError):
            pass
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


def backup_once(game: Path) -> Path:
    exefs = exefs_of(game)
    bak = game / BACKUP
    bak.mkdir(parents=True, exist_ok=True)
    pairs = [(exefs / "main", bak / "main")]
    exe = exe_of(game)
    if exe:
        pairs.append((exe, bak / exe.name))
    pairs += [(game / "image.bin", bak / "image.bin"),
              (game / "longshot_prepared.bin", bak / "longshot_prepared.bin")]
    for src, dst in pairs:
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
    return bak


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
    for opt, enabled in (("enemy_double", s.enemy_double), ("enemy_speed", s.enemy_speed),
                         ("farore_outdoor", s.farore_outdoor),
                         ("great_fairy", s.great_fairy)):
        if enabled and not copy(pay / "romfs_opts" / opt):
            notes.append((opt + "_missing", ""))
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
    env = dict(os.environ)
    env.update({"PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
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
    backup_once(game)
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
    restored = False
    for src, dst in ((bak / "main", exefs / "main"),
                     (bak / "longshot.exe", game / "bin" / "longshot.exe"),
                     (bak / "hookshot", game / "bin" / "hookshot"),
                     (bak / "hookshot.exe", game / "bin" / "hookshot.exe"),
                     (bak / "image.bin", game / "image.bin"),
                     (bak / "longshot_prepared.bin", game / "longshot_prepared.bin")):
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            restored = True
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
