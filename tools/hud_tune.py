"""Tune the clock/rupee plates live: read/write g_hudp in the running game and take screenshots.

The emulator must already be running with the debug server (e.g. `python tools/live_check.py --keep`).

Usage:
    python tools/hud_tune.py get
    python tools/hud_tune.py set 0=-1400 3=0.8 [--shot build/tune.png]
    python tools/hud_tune.py shot build/tune.png [--crop x0,y0,x1,y1]
    python tools/hud_tune.py dbg

Indices of g_hudp are documented in core/hud.c.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient, HostMemory, lichii_pids  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_check import PORT, log_addr, symbols  # noqa: E402

N = 20


def connect():
    c = DebugClient(port=PORT, timeout=10)
    base = log_addr("main")
    if base is None:
        raise SystemExit("no main base in the emulator log")
    return c, base, symbols()


def shot(c, out: str, crop: str | None) -> None:
    png, _, _ = c.screenshot()
    Path(out).write_bytes(png)
    if crop:
        from io import BytesIO
        from PIL import Image
        box = tuple(int(v) for v in crop.split(","))
        Image.open(BytesIO(png)).crop(box).save(out)
    print("saved", out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["get", "set", "shot", "dbg", "cfg"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--shot", default="")
    ap.add_argument("--crop", default="")
    a = ap.parse_args()
    c, base, syms = connect()
    addr = base + syms["g_hudp"]
    if a.cmd == "get":
        print([round(v, 3) for v in struct.unpack(f"<{N}f", bytes(c.read(addr, 4 * N)))])
    elif a.cmd == "set":
        pids = lichii_pids()
        if not pids:
            raise SystemExit("lichii.exe is not running")
        hm = HostMemory(pids[0])
        hm.calibrate(c, [base])
        for kv in a.args:
            i, v = kv.split("=")
            hm.write(addr + 4 * int(i), struct.pack("<f", float(v)))
        print([round(v, 3) for v in struct.unpack(f"<{N}f", bytes(c.read(addr, 4 * N)))])
        if a.shot:
            import time
            time.sleep(0.4)
            shot(c, a.shot, a.crop)
    elif a.cmd == "cfg":   # cfg rupees=1 clock=1 clock24=0: switch the HUD options in the running game
        offs = {"rupees": 30, "clock": 31, "clock24": 32}   # OotConfig field offsets (core/config.h)
        pids = lichii_pids()
        hm = HostMemory(pids[0])
        hm.calibrate(c, [base])
        cfg = base + syms["g_ootcfg"]
        for kv in a.args:
            k, v = kv.split("=")
            hm.write(cfg + offs[k], bytes([int(v)]))
        print("g_ootcfg", bytes(c.read(cfg, 40)).hex())
    elif a.cmd == "shot":
        shot(c, a.args[0] if a.args else "build/tune.png", a.crop)
    elif a.cmd == "dbg":
        for name, fmt in (("g_hud_dbg", "<12Q"), ("g_txt_dbg", "<8Q"), ("g_hud_show", "<2I"), ("g_clk_dbg", "<4I")):
            if name in syms:
                size = struct.calcsize(fmt)
                print(name, [hex(v) for v in struct.unpack(fmt, bytes(c.read(base + syms[name], size)))])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
