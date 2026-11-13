"""Developer step (NOT done by the app): compile the two prebuilt variants and stage them as the app payload.

  classic     module linked after Classic Item Slots (base 0x4F87000)
  standalone  module linked right after subsdk0 (base 0x4F80000)

Output: app/payload/<variant>/{subsdk9,ours.ips} + app/payload/manifest.json
"""
import hashlib, json, shutil, subprocess, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "payload"
BUILD_ID = "E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348"
VARIANTS = {"classic": "0x4F87000", "standalone": "0x4F80000"}


CLASSIC_TAG = "v1.4.3"
CLASSIC_ASSETS = {"default": f"Classic-Item-Slots-{CLASSIC_TAG}.zip", "xbox": f"Classic-Item-Slots-{CLASSIC_TAG}-Xbox.zip",
                  "playstation": f"Classic-Item-Slots-{CLASSIC_TAG}-PlayStation.zip"}
CLASSIC_URL = "https://github.com/sonofsilvanus/OoTNS2-Classic-Item-Slots/releases/download/{tag}/{name}"


def stage_classic():
    """Bundle Classic Item Slots v1.4.3 (the three official zips) next to the variants. Cached in build/."""
    cache = ROOT / "build" / "classic_cache"
    cache.mkdir(parents=True, exist_ok=True)
    dst = OUT / "classic_src"
    dst.mkdir(parents=True, exist_ok=True)
    for key, name in CLASSIC_ASSETS.items():
        f = cache / name
        if not f.exists():
            req = urllib.request.Request(CLASSIC_URL.format(tag=CLASSIC_TAG, name=name), headers={"User-Agent": "oot-master-build"})
            f.write_bytes(urllib.request.urlopen(req, timeout=120).read())
        shutil.copy2(f, dst / f"{key}.zip")


def stage_rupee_ips():
    """rupee.ips: skip the 'hide the numeric display when its value is stable' call (main+0x33C3B80 -> branch over it)."""
    import struct
    rec = struct.pack(">I", 0x33C3B80 + 0x100) + struct.pack(">H", 4) + struct.pack("<I", 0x14000000 | 3)
    (OUT / "rupee.ips").write_bytes(b"IPS32" + rec + b"EEOF")


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    man = {"build_id": BUILD_ID, "variants": {}}
    for name, base in VARIANTS.items():
        subprocess.run([sys.executable, str(ROOT / "tools" / "build_core.py"), "--features", "hero_core",
                        "--compat", "--base", base], check=True, cwd=ROOT)
        d = OUT / name
        d.mkdir(parents=True)
        src = ROOT / "build" / "native" / "exefs"
        shutil.copy2(src / "subsdk9", d / "subsdk9")
        shutil.copy2(src / f"{BUILD_ID}.ips", d / "ours.ips")
        man["variants"][name] = {"base": base, "sha256": hashlib.sha256((d / "subsdk9").read_bytes()).hexdigest()}
    stage_classic()
    subprocess.run([sys.executable, str(ROOT / "tools" / "make_romfs_opts.py")], check=True, cwd=ROOT)
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2))
    print("payload staged in", OUT)


if __name__ == "__main__":
    main()
