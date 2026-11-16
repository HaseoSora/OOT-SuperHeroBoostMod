"""Stage app/payload in a clean CI checkout.

The payload is deliberately not versioned (see docs/AUDIT.md): it holds the compiled module, the button
textures and the optional romfs files generated from the game dump. The build workflow downloads it from
the release tagged `payload` instead.

    python tools/ci_payload.py      # CI step; does nothing if app/payload is already complete

Create or update that release asset with tools/make_payload_zip.py.
"""
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD = ROOT / "app" / "payload"
REQUIRED = ("standalone/subsdk9", "button_romfs")
FALLBACK_REPO = "kuribox/OOT-SuperHeroBoostMod"


def complete() -> bool:
    return all((PAYLOAD / rel).exists() for rel in REQUIRED)


def download(url: str, dest: Path) -> None:
    headers = {"User-Agent": "super-hero-boost-ci"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(req, timeout=120) as response, dest.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)


def main() -> None:
    if complete():
        print("app/payload is already staged")
        return

    repo = os.environ.get("GITHUB_REPOSITORY", FALLBACK_REPO)
    url = f"https://github.com/{repo}/releases/download/payload/payload.zip"
    dest = ROOT / "build" / "payload.zip"
    print(f"downloading {url}")
    try:
        download(url, dest)
    except Exception as exc:  # noqa: BLE001 - the message matters more than the type
        raise SystemExit(
            f"could not download the payload: {exc}\n"
            "Create the `payload` release with its payload.zip asset: run tools/make_payload_zip.py and upload\n"
            "release/payload.zip to GitHub > Releases (tag `payload`). See docs/CI.md."
        ) from exc

    with zipfile.ZipFile(dest) as archive:
        for name in archive.namelist():
            if name.startswith(("/", "\\")) or ".." in Path(name).parts:
                raise SystemExit(f"payload.zip has an unsafe path: {name}")
        archive.extractall(PAYLOAD)

    missing = [rel for rel in REQUIRED if not (PAYLOAD / rel).exists()]
    if missing:
        raise SystemExit("payload.zip is incomplete, missing: " + ", ".join(missing))
    print(f"payload staged in {PAYLOAD}")


if __name__ == "__main__":
    sys.exit(main())
