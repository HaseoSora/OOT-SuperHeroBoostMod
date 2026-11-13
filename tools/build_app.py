"""Developer step: bundle the companion app into a single Windows executable (PyInstaller).
Needs app/payload (run tools/make_release.py first). Output: release/OotMasterConfig.exe"""
import shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
                "--name", "OotMasterConfig", "--distpath", str(ROOT / "release"),
                "--workpath", str(ROOT / "build" / "pyi"), "--specpath", str(ROOT / "build" / "pyi"),
                "--add-data", f"{ROOT / 'app' / 'payload'};payload",
                str(ROOT / "app" / "ootconfig.py")], check=True, cwd=ROOT)
print("built", ROOT / "release" / "OotMasterConfig.exe")
