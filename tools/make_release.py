"""Developer step (NOT done by the app): compile the two prebuilt variants and stage them as the app payload.

  classic     module linked after Classic Item Slots (base 0x4F87000)
  standalone  module linked right after subsdk0 (base 0x4F80000)

Output: app/payload/<variant>/{subsdk9,ours.ips} + app/payload/manifest.json
"""
import hashlib, json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "payload"
BUILD_ID = "E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348"
VARIANTS = {"classic": "0x4F87000", "standalone": "0x4F80000"}


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
    (OUT / "manifest.json").write_text(json.dumps(man, indent=2))
    print("payload staged in", OUT)


if __name__ == "__main__":
    main()
