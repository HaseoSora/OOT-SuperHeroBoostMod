"""Live check of the mod in Fritchii via the emulator debug server.

Launches the game with EDEN_NX2_DEBUG_SERVER, reads our module's globals from
guest memory, optionally sends button input, checks the log for criticals and
backtraces, and closes the emulator.

Usage:
    python tools/live_check.py --wait 40 --press B:60

Symbols come from build/native/module.elf (run tools/build_core.py first).
"""
from __future__ import annotations

import argparse
import re
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient  # noqa: E402

TOOLCHAIN_BIN = Path(
    r"F:\project\oot\tools\llvm-mingw\llvm-mingw-20261104-ucrt-x86_64\bin"
)
NM = TOOLCHAIN_BIN / "llvm-nm.exe"
ELF = ROOT / "build" / "native" / "module.elf"

FRITCHII = Path(r"E:\Switch2\Emu\Fritchii-v4.1-Windows-x64\Fritchii-v4.1")
GAME = Path(r"E:\Switch2\Roms\NX\Zelda Ocarina.nx")
LOG = FRITCHII / "user" / "log" / "eden_log.txt"
PORT = 6545


def symbols() -> dict[str, int]:
    out = subprocess.run([str(NM), "-n", str(ELF)], capture_output=True, text=True).stdout
    syms: dict[str, int] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 3:
            syms[parts[2]] = int(parts[0], 16)
    return syms


def log_addr(name: str) -> int | None:
    if not LOG.exists():
        return None
    m = None
    for line in LOG.read_text(errors="replace").splitlines():
        r = re.search(rf"Module {name} loaded at 0x([0-9a-fA-F]+)", line)
        if r:
            m = int(r.group(1), 16)
    return m


def wait_for_status(c: DebugClient, tries: int = 40) -> dict | None:
    for _ in range(tries):
        try:
            return c.status()
        except Exception:
            time.sleep(1.5)
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--wait", type=float, default=30.0, help="seconds to run before reading")
    ap.add_argument("--press", default="", help="BUTTON:frames to send, e.g. B:60")
    ap.add_argument("--keep", action="store_true", help="do not close the emulator")
    ap.add_argument("--boot-wait", type=float, default=35.0,
                    help="seconds after launch before the first A (title screen must be up)")
    ap.add_argument("--load-timeout", type=float, default=150.0,
                    help="max seconds to wait for the save to load after the A presses")
    ap.add_argument("--linger", type=float, default=8.0,
                    help="seconds to keep the game running after the inputs")
    ap.add_argument("--settle", type=float, default=30.0,
                    help="seconds after the last A before reading (save loading)")
    ap.add_argument("--load-a", type=int, default=4,
                    help="presses of A to load the save after boot (user's procedure)")
    ap.add_argument("--shots", type=int, default=0, help="extra screenshots, 0.35 s apart")
    ap.add_argument("--shot-gap", type=float, default=0.35)
    args = ap.parse_args()

    syms = symbols()
    env = dict(**__import__("os").environ, EDEN_NX2_DEBUG_SERVER=f"127.0.0.1:{PORT}")
    proc = subprocess.Popen(
        [str(FRITCHII / "lichii.exe"), "-g", str(GAME)],
        cwd=str(FRITCHII), env=env,
    )
    try:
        from lib.winmove import move_to_secondary  # keep the emulator off the primary monitor
        move_to_secondary(proc.pid)
        c = DebugClient(port=PORT, timeout=10)
        st = wait_for_status(c)
        print("debug status:", "ok" if st is not None else "NO CONNECTION")
        time.sleep(args.wait)
        if not proc.poll() is None:
            print("EMULATOR EXITED early, code", proc.returncode)
            return 1

        # Boot to the title screen first; pressing A earlier loses presses.
        time.sleep(args.boot_wait)
        for _ in range(args.load_a):
            c.input([{"buttons": ["A"], "frames": 20}])
            time.sleep(6.0)

        main_base = log_addr("main")
        sub_base = log_addr("subsdk9")
        print(f"main base {main_base and hex(main_base)}, subsdk9 base {sub_base and hex(sub_base)}")
        if main_base is None:
            print("no main base in log")
            return 1

        # Wait until the game is actually loaded: the input hooks only count
        # once the player is in gameplay. Poll the probe counters.
        # ~20 s from the last A until the save is in gameplay, plus margin; the
        # probe counters cannot tell (input sites also run on loading screens).
        # Wait until the save is really in gameplay: a black/loading screenshot is tiny,
        # gameplay is large. The machine may be busy, so allow up to --load-timeout.
        print(f"waiting for the save to load (min {args.settle:.0f}s, max {args.load_timeout:.0f}s)")
        t_wait = time.time()
        time.sleep(args.settle)
        loaded = False
        while time.time() - t_wait < args.load_timeout:
            try:
                png, w, h = c.screenshot()
                if len(png) > 150000:
                    loaded = True
                    break
            except Exception:
                pass
            time.sleep(5.0)
        print(f"game loaded: {loaded} after {int(time.time() - t_wait)}s")
        if loaded:
            time.sleep(5.0)   # let the first frames settle
        png, w, h = c.screenshot()
        (ROOT / "build" / "live_before.png").write_bytes(png)
        print("saved build/live_before.png (before inputs)")

        def read_sym(name: str, size: int) -> bytes:
            addr = main_base + syms[name]
            return bytes(c.read(addr, size))

        BASE = 0x10000000
        if "g_probe_count" in syms:
            raw = struct.unpack("<5I", read_sym("g_probe_count", 20))
            print("probe calls per site (raw):", tuple(v - BASE for v in raw))
        if "g_slot_count" in syms:
            rawslot = struct.unpack("<4I", read_sym("g_slot_count", 16))
            print("slot calls per site (raw):", tuple(v - BASE for v in rawslot))
        if "g_stamina" in syms:
            s = read_sym("g_stamina", 4)
            print("stamina (first float):", struct.unpack("<f", s)[0])

        if args.press:
            before = read_sym("g_stamina", 4) if "g_stamina" in syms else None
            # --press accepts several steps: "B:30,ZR:20,A:10"
            for n, step in enumerate(args.press.split(",")):
                btn, frames = step.split(":")
                c.input([{"buttons": btn.split("+"), "frames": int(frames)}])   # e.g. ZL+B
                print("press", btn, frames, "frames")
                if "g_stamina" in syms:
                    print("   stamina right after press:", struct.unpack("<f", read_sym("g_stamina", 4))[0])
                png0, _, _ = c.screenshot()
                (ROOT / "build" / f"live_now{n}.png").write_bytes(png0)
                time.sleep(2.5)   # let the game react before sampling counters
                if "g_slot_log_n" in syms:
                    k = struct.unpack("<I", read_sym("g_slot_log_n", 4))[0] - 0x10000000
                    print(f"   slot-function calls so far: {k}")
                png, w, h = c.screenshot()   # right after the input, before regen/timeouts
                (ROOT / "build" / f"live_step{n}.png").write_bytes(png)
                time.sleep(0.5)
            after = read_sym("g_stamina", 4) if "g_stamina" in syms else None
            if before is not None:
                print("stamina before:", struct.unpack("<f", before)[0],
                      "after:", struct.unpack("<f", after)[0])
        for i in range(args.shots):
            png, _, _ = c.screenshot()
            (ROOT / "build" / f"live_s{i}.png").write_bytes(png)
            if "g_value" in syms:
                print(f"   shot {i}: g_value {struct.unpack('<f', read_sym('g_value', 4))[0]}")
            time.sleep(args.shot_gap)
        time.sleep(args.linger)  # let the game keep running after the inputs
        png, w, h = c.screenshot()
        (ROOT / "build" / "live_last.png").write_bytes(png)
        print("saved build/live_last.png (after inputs)")
        if "g_hud_dbg" in syms:
            d = struct.unpack("<12Q", read_sym("g_hud_dbg", 96))
            names = ["mp", "frames", "bar", "ratio", "max", "trace", "root_clones",
                     "gauge_clones", "prepare_calls", "pane", "errors", "slots_bound"]
            print("hud:", {n: hex(v - 0x1000000000000000) for n, v in zip(names, d)})
        if "g_seg_ok" in syms:
            print("ring segments bound:", struct.unpack("<I", read_sym("g_seg_ok", 4))[0] - 0x10000000)
        if "g_len" in syms:
            print("gauge anim lengths ratio/max/trace:", struct.unpack("<3I", read_sym("g_len", 12)))
        if "g_pl" in syms:
            n = struct.unpack("<I", read_sym("g_pl_n", 4))[0]
            raw = read_sym("g_pl", 40 * 32)
            print("prepare calls (inst / asset):")
            for i in range(1, min(n, 40)):
                e = raw[i * 32:(i + 1) * 32]
                print("   ", e[:16].split(b"\0")[0].decode("latin1"), "/", e[16:].split(b"\0")[0].decode("latin1"))
        if "g_slot_log" in syms:
            n = struct.unpack("<I", read_sym("g_slot_log_n", 4))[0] - 0x10000000
            raw = read_sym("g_slot_log", 24 * 32)
            print(f"slot-function calls logged: {n}")
            for i in range(min(n, 24)):
                site, res, a0, a1, a2 = struct.unpack_from("<IIQQQ", raw, i * 32)
                print(f"  site {site} result {res:#x} x0={a0:#x} x1={a1:#x} x2={a2:#x}")
        if "g_fl" in syms:
            n = struct.unpack("<I", read_sym("g_fl_n", 4))[0] - 0x10000000
            raw = read_sym("g_fl", 24 * 8)
            sd = struct.unpack("<4Q", read_sym("g_stock_dbg", 32))
            print("stock item box:", [hex(v - 0x1000000000000000) for v in sd[:3]])
            print(f"stock item-box frame changes: {n}")
            for i in range(min(n, 24)):
                tag, fr = struct.unpack_from("<If", raw, i * 8)
                print(f"   {'ItemPattern' if tag == 1 else 'StockNum'} frame {fr}")
        if "g_map" in syms:
            n = struct.unpack("<I", read_sym("g_map_n", 4))[0] - 0x10000000
            raw = read_sym("g_map", 40 * 16)
            print(f"item map entries: {n}")
            for i in range(min(n, 40)):
                idx, res, pat, num = struct.unpack_from("<IIff", raw, i * 16)
                print(f"   idx {idx:2d} result {res} icon-frame {pat} count-frame {num}")
        if "g_cl_dbg" in syms:
            cd = struct.unpack("<4I", read_sym("g_cl_dbg", 16))
            print("classic: slot presses %d, item overrides %d, expired %d" %
                  (cd[0] - 0x10000000, cd[1] - 0x10000000, cd[2] - 0x10000000))
        if "g_inst_log" in syms:
            n = struct.unpack("<I", read_sym("g_inst_n", 4))[0] - 0x10000000
            raw = struct.unpack("<32I", read_sym("g_inst_log", 128))
            print(f"part instantiations: {n}; pane indices:", [raw[i % 32] for i in range(max(0, n - 32), n)])
            ch = struct.unpack("<32Q", read_sym("g_inst_child", 256))
            print("   child frame object per instantiation:", [hex(ch[i % 32]) for i in range(max(0, n - 32), n)])
        if "g_bind_dbg" in syms:
            bd = struct.unpack("<4Q", read_sym("g_bind_dbg", 32))
            print("slot0 part/pat/num/pane:", [hex(v - 0x1000000000000000) for v in bd])
        if "g_prep_dbg" in syms:
            pd = struct.unpack("<20Q", read_sym("g_prep_dbg", 160))
            for k in range(5):
                print(f"   prepare part {k}: handle {pd[k*4]:#x} config {pd[k*4+1]:#x} h+28 {pd[k*4+2]:#x} h+38 {pd[k*4+3]:#x}")
        if "g_sub_dbg" in syms:
            sd = struct.unpack("<16Q", read_sym("g_sub_dbg", 128))
            nm = ["ItemPattern", "Type", "StockNum", "ItemChange", "State", "IsInvalid", "Select", "PART"]
            for i in range(2):
                print(f"sub item {i}:", {nm[k]: hex(sd[i * 8 + k] - 0x1000000000000000) for k in range(8)})
        if "g_slot_dbg" in syms:
            sd = struct.unpack("<4Q", read_sym("g_slot_dbg", 32))
            print("slot instances seen by prepare (asset ptr):", [hex(v - 0x1000000000000000) for v in sd])
            bd = struct.unpack("<4Q", read_sym("g_bind_dbg", 32))
            print("slot0 part/pat/num/pane:", [hex(v - 0x1000000000000000) for v in bd])
        if "g_hc_seen" in syms:
            seen = struct.unpack("<Q", read_sym("g_hc_seen", 8))[0] - 0x100000000
            cnt = struct.unpack("<I", read_sym("g_hc_count", 4))[0]
            print(f"hero_core: buttons seen at site 3 = {seen:#x}, sample count = {cnt:#x}")
        if "g_wrap_entry" in syms:
            w_in = struct.unpack("<5I", read_sym("g_wrap_entry", 20))
            w_sl = struct.unpack("<4I", read_sym("g_slot_entry", 16))
            print("wrapper entries input 0..4 (raw - base):", tuple(v - BASE for v in w_in))
            print("wrapper entries slot 0..3 (raw - base):", tuple(v - BASE for v in w_sl))
    finally:
        log = LOG.read_text(errors="replace") if LOG.exists() else ""
        print("Critical:", log.count("<Critical>"), " Backtrace:", log.count("Backtrace"))
        frames = re.findall(r"present #(\d+)", log)
        if frames:
            print("last frame:", frames[-1])
        if not args.keep and proc.poll() is None:
            proc.kill()
            print("emulator closed automatically")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

