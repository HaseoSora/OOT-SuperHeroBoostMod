"""Fail if a game-dump or generated payload file is tracked by git.

Usage: python tools/check_no_game_data.py

The repository must contain sources and documentation only. Game data
(romfs, BYML, BNTX, SARC, NSO/NRO, etc.), the prebuilt payload and release
binaries belong in a release artifact, never in the git index.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BAD_SUFFIXES = {
    ".byml", ".bgyml", ".bntx", ".sarc", ".blarc", ".bfres", ".bfstm", ".bfsar",
    ".bars", ".genvb", ".pack", ".zs", ".nso", ".nro", ".nsp", ".xci", ".nca",
    ".ips", ".bin", ".png",
}
BAD_DIRS = ("romfs/", "exefs/", "stock-exefs/", "app/payload/", "release/", "build/", "data/")
BAD_MAGIC = {
    b"NSO0": "NSO",
    b"BNTX": "BNTX",
    b"SARC": "SARC",
    b"Yaz0": "Yaz0",
    b"FRES": "FRES",
    b"BFSI": "BFSI",
    b"BYML": "BYML",
    b"YBML": "YBML",
}


def git_exe() -> str:
    found = shutil.which("git")
    if found:
        return found
    for candidate in (r"C:\Program Files\Git\cmd\git.exe", r"C:\Program Files (x86)\Git\cmd\git.exe"):
        if Path(candidate).exists():
            return candidate
    raise SystemExit("git not found in PATH")


def main() -> int:
    tracked = subprocess.run([git_exe(), "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    bad = []
    for rel in tracked.splitlines():
        rel_norm = rel.replace("\\", "/")
        p = ROOT / rel
        why = None
        if p.suffix.lower() in BAD_SUFFIXES:
            why = f"extension {p.suffix}"
        elif any(part in rel_norm for part in BAD_DIRS):
            why = "generated/dump folder"
        elif p.is_file() and p.stat().st_size:
            head = p.read_bytes()[:4]
            if head in BAD_MAGIC:
                why = f"magic {BAD_MAGIC[head]}"
        if why:
            bad.append((rel, why))

    if bad:
        print("Tracked game data / generated files found:")
        for rel, why in bad:
            print(f"  {rel}  ({why})")
        print("\nRemove them from git (git rm --cached <file>) and keep them in .gitignore.")
        return 1
    print(f"OK: {len(tracked.splitlines())} tracked files; no game dump or payload files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
