"""Package app/payload as the zip the CI workflow downloads.

The payload is not versioned (docs/AUDIT.md), so the workflow tagged `payload` in GitHub Releases carries it.
Run this after tools/make_release.py and upload the result once per payload change:

    python tools/make_payload_zip.py
    # GitHub > Releases > tag `payload` > upload release/payload.zip
    # or with the GitHub CLI:
    #   gh release create payload release/payload.zip -t "Build payload" -n "app/payload for the CI builds"

The zip holds the payload contents at its root (standalone/, button_romfs/, romfs_opts/), which is what
tools/ci_payload.py extracts into app/payload.
"""
import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "app" / "payload"
OUT = ROOT / "release" / "payload.zip"
REQUIRED = ("standalone/subsdk9", "button_romfs")


def main() -> None:
    missing = [rel for rel in REQUIRED if not (PAYLOAD / rel).exists()]
    if missing:
        raise SystemExit("app/payload is incomplete, missing: " + ", ".join(missing))
    if not (PAYLOAD / "romfs_opts").is_dir():
        print("warning: app/payload/romfs_opts is missing; the presets pack needs it (run tools/make_romfs_opts.py)")

    files = sorted(p for p in PAYLOAD.rglob("*") if p.is_file())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(PAYLOAD).as_posix(), date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())

    data = OUT.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    print(f"wrote {OUT} ({len(data) / 1024 / 1024:.1f} MB, {len(files)} files)")
    print("sha256", digest)
    print("upload it to the release tagged `payload` (GitHub > Releases)")


if __name__ == "__main__":
    main()
