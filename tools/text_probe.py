"""Live probe: text-pane descriptors and pane records of PlayerStatus_00 (for the clock / rupee panes)."""
import os, struct, subprocess, sys, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, log_addr, wait_for_status, symbols

def rd(c, a, n): return bytes(c.read(a, n))
def q(c, a): return struct.unpack("<Q", rd(c, a, 8))[0]
def hexdump(b, base=0):
    for o in range(0, len(b), 16):
        w = struct.unpack_from("<%dI" % (min(16, len(b) - o) // 4), b, o)
        print(f"  +{base+o:03x}: " + " ".join(f"{x:08x}" for x in w))

def main():
    syms = symbols()
    env = dict(os.environ, EDEN_NX2_DEBUG_SERVER=f"127.0.0.1:{PORT}")
    proc = subprocess.Popen([str(FRITCHII / "lichii.exe"), "-g", str(GAME)], cwd=str(FRITCHII), env=env)
    try:
        from lib.winmove import move_to_secondary
        move_to_secondary(proc.pid)
        c = DebugClient(port=PORT, timeout=10)
        wait_for_status(c)
        time.sleep(35)
        for _ in range(4):
            c.input([{"buttons": ["A"], "frames": 20}]); time.sleep(6)
        time.sleep(30)
        mb = log_addr("main")
        d = struct.unpack("<8Q", rd(c, mb + syms["g_hud_dbg"], 64))
        M = 0x1000000000000000
        mp = d[0] - M
        owner = q(c, mp + 0x18); parent = q(c, owner + 0x28)
        lay = q(c, parent + 0x80); arr = q(c, lay + 0x100); root = q(c, lay + 0xF8)
        ncommon = struct.unpack("<I", rd(c, root + 0x38, 4))[0]
        print("layout", hex(lay), "arr", hex(arr), "root", hex(root), "common", ncommon,
              "panecount@+0x13c", struct.unpack("<H", rd(c, lay + 0x13C, 2))[0])
        names = q(c, root + 0x20)
        print("root header counts:", {hex(o): struct.unpack('<I', rd(c, root + o, 4))[0] for o in (0x38, 0x58, 0x78, 0x98, 0xB8, 0xD8, 0xF8 - 0x0, 0x138)})
        for tab in (0x40, 0x60, 0x80, 0xA0, 0xE0):
            cnt = struct.unpack("<I", rd(c, root + tab + 24, 4))[0]
            print(f"-- table +{tab:#x}: count {cnt}")
            if not 0 < cnt < 64: continue
            tn, td = q(c, root + tab), q(c, root + tab + 8)
            for i in range(cnt):
                nm = rd(c, q(c, tn + i * 8), 40).split(b"\0")[0].decode(errors="replace")
                dp = q(c, td + i * 8)
                print(f"   [{i}] {nm} desc@{dp:#x}")
                if tab == 0x60 and i in (4, 5):
                    dd = rd(c, dp, 0x88)
                    for off in (0x00, 0x20, 0x48, 0x50, 0x58, 0x60):
                        pp = struct.unpack_from("<Q", dd, off)[0]
                        try:
                            raw = rd(c, pp, 0x30)
                            print(f"      +{off:#x} -> {pp:#x} {raw.split(bytes(1))[0][:30]!r}")
                            hexdump(raw)
                        except Exception as e: print("      err", e)
                if tab == 0x40 and i in (6, 7, 8):
                    print("      comb desc"); hexdump(rd(c, dp, 0x88))
                if tab == 0x80:
                    dd = rd(c, dp, 0xA8)
                    for off in (0x00, 0x10, 0x18):
                        pp = struct.unpack_from("<Q", dd, off)[0]
                        try: sv = rd(c, pp, 40).split(b"\0")[0]
                        except Exception as e: sv = repr(e)
                        print(f"      +{off:#x} -> {pp:#x} {sv!r}")
        # panes whose names look like text / the common desc of the first 40
        cn, cd = q(c, root + 0x20), q(c, root + 0x28)
        for i in range(ncommon):
            nm = rd(c, q(c, cn + i * 8), 40).split(b"\0")[0].decode(errors="replace")
            dp = q(c, cd + i * 8)
            rec = rd(c, arr + i * 0xB0, 0xB0)
            flags = struct.unpack_from("<I", rec, 0)[0]
            print(f"pane {i:2d} {nm:26s} flags={flags:#010x} +8={struct.unpack_from('<Q',rec,8)[0]:#x} pos=({struct.unpack_from('<f',rec,0x6c)[0]:.0f},{struct.unpack_from('<f',rec,0x70)[0]:.0f}) desc[0x40..0x44]={rd(c,dp+0x38,8).hex()}")
        for nm in ("T_ShortCut_00", "T_Assign_01"):
            i = next((k for k in range(ncommon) if rd(c, q(c, cn + k * 8), 40).split(b"\0")[0].decode(errors="replace") == nm), None)
            if i is None: continue
            dp = q(c, cd + i * 8)
            print("== common desc", nm, i); hexdump(rd(c, dp, 0x44))
            rec = rd(c, arr + i * 0xB0, 0xB0)
            print("== record"); hexdump(rec)
            o8 = struct.unpack_from("<Q", rec, 8)[0]
            if o8 > 0x10000:
                print("== rec+8 object"); hexdump(rd(c, o8, 0x80))
        # tail of the root header (pools / counts)
        print("== root +0x100..0x230"); hexdump(rd(c, root + 0x100, 0x130), 0x100)
        png, w, h = c.screenshot()
        open(os.path.join(os.path.dirname(__file__), "..", "build", "text_probe.png"), "wb").write(png)
    finally:
        proc.kill()

main()
