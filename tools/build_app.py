"""Developer step: bundle the companion app into a single executable (PyInstaller).

Works on Windows, macOS and Linux; PyInstaller must run on the target OS.
Needs app/payload (run tools/make_release.py first).

Output:
    Windows  release/SuperHeroBoostConfig.exe
    macOS    release/SuperHeroBoostConfig.app (and a Unix executable inside it)
    Linux    release/SuperHeroBoostConfig
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAME = "SuperHeroBoostConfig"
DIST = ROOT / "release"
WORK = ROOT / "build" / "pyi"
WORK.mkdir(parents=True, exist_ok=True)

subprocess.run([
    sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--windowed",
    "--name", NAME,
    "--distpath", str(DIST),
    "--workpath", str(WORK),
    "--specpath", str(WORK),
    "--add-data", f"{ROOT / 'app' / 'payload'}{os.pathsep}payload",
    str(ROOT / "app" / "main.py"),
], check=True, cwd=ROOT)

if sys.platform == "win32":
    out = DIST / f"{NAME}.exe"
elif sys.platform == "darwin":
    out = DIST / f"{NAME}.app"
else:
    out = DIST / NAME
print("built", out)
