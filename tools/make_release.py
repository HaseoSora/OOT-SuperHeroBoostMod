"""Developer step (NOT done by the app): compile the two prebuilt variants and stage them as the app payload.

  classic     module linked after Classic Item Slots (base 0x4F87000)
  standalone  module linked right after subsdk0 (base 0x4F80000)

Output: app/payload/<variant>/{subsdk9,ours.ips} + app/payload/manifest.json

Classic Item Slots is NOT bundled: the app downloads the chosen official
release from GitHub when the user installs it.
"""
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "payload"
BUILD_ID = "E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348"
VARIANTS = {"classic": "0x4F87000", "standalone": "0x4F80000"}


def stage_rupee_ips():
    """rupee.ips: skip the 'hide the numeric display when its value is stable' call (main+0x33C3B80 -> branch over it)."""
    import struct
    rec = struct.pack(">I", 0x33C3B80 + 0x100) + struct.pack(">H", 4) + struct.pack("<I", 0x14000000 | 3)
    (OUT / "rupee.ips").write_bytes(b"IPS32" + rec + b"EEOF")


def main():
    keep = None
    if (OUT / "romfs_opts").exists():
        keep = ROOT / "build" / "payload_keep" / "romfs_opts"
        shutil.rmtree(keep.parent, ignore_errors=True)
        shutil.copytree(OUT / "romfs_opts", keep)
    if OUT.exists():
        shutil.rmtree(OUT)
    man = {"build_id": BUILD_ID, "variants": {}}
    for name, base in VARIANTS.items():
        subprocess.run([sys.executable, str(ROOT / "tools" / "build_core.py"), "--features", "stamina,songbook,quick_select",
                        "--compat", "--base", base], check=True, cwd=ROOT)
        d = OUT / name
        d.mkdir(parents=True)
        src = ROOT / "build" / "native" / "exefs"
        shutil.copy2(src / "subsdk9", d / "subsdk9")
        shutil.copy2(src / f"{BUILD_ID}.ips", d / "ours.ips")
        man["variants"][name] = {"base": base, "sha256": hashlib.sha256((d / "subsdk9").read_bytes()).hexdigest()}
    if keep is not None and keep.exists():
        shutil.copytree(keep, OUT / "romfs_opts")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "make_romfs_opts.py")], cwd=ROOT)
    if r.returncode:
        print("WARNING: romfs options not built (game dump missing?): the payload keeps any previous 'romfs_opts'")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "make_enemy_opts.py")], cwd=ROOT)
    if r.returncode:
        print("WARNING: beta enemy mods not built (game dump missing?): the payload keeps any previous files")
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2))
    print("payload staged in", OUT)


if __name__ == "__main__":
    main()
