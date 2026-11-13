"""Dump the panes (name, pos, scale, raw floats) of our bound stamina gauge part."""
import os, struct, subprocess, sys, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, log_addr, wait_for_status, symbols


def rd(c, a, n): return bytes(c.read(a, n))
def q(c, a): return struct.unpack("<Q", rd(c, a, 8))[0]
def w(c, a): return struct.unpack("<I", rd(c, a, 4))[0]


def main():
    syms = symbols()
    env = dict(os.environ, EDEN_NX2_DEBUG_SERVER=f"127.0.0.1:{PORT}")
    p = subprocess.Popen([str(FRITCHII / "lichii.exe"), "-g", str(GAME)], cwd=str(FRITCHII), env=env)
    try:
        from lib.winmove import move_to_secondary
        move_to_secondary(p.pid)
        c = DebugClient(port=PORT, timeout=10)
        wait_for_status(c)
        time.sleep(35)
        for _ in range(4):
            c.input([{"buttons": ["A"], "frames": 20}]); time.sleep(6)
        time.sleep(40)
        mb = log_addr("main")
        M = 0x1000000000000000
        bar = struct.unpack("<12Q", rd(c, mb + syms["g_hud_dbg"], 96))[2] - M
        pane = struct.unpack("<12Q", rd(c, mb + syms["g_hud_dbg"], 96))[9] - M
        r = rd(c, pane, 0xB0)
        print("PART PANE @", hex(pane), "flags", hex(struct.unpack_from("<I", r, 0)[0]),
              "floats 0x40..0x7C:", " ".join(f"{x:.2f}" for x in struct.unpack_from("<16f", r, 0x40)))
        mp = struct.unpack("<12Q", rd(c, mb + syms["g_hud_dbg"], 96))[0] - M
        parent = q(c, q(c, mp + 0x18) + 0x28)
        play = q(c, parent + 0x80); proot = q(c, play + 0xF8)
        for tname, toff in (("common panes", 0x20), ("parts", 0xC0)):
            cnt = w(c, proot + toff + 24); nms = q(c, proot + toff)
            print(tname, cnt, ":", ", ".join(
                f"{i}:" + rd(c, q(c, nms + i * 8), 40).split(b"\0")[0].decode("latin1") for i in range(cnt)))
        lay = q(c, bar + 0x80); arr = q(c, lay + 0x100); root = q(c, lay + 0xF8)
        n = w(c, root + 0x38); names = q(c, root + 0x20)
        print("bar", hex(bar), "panes", n)
        for i in range(n):
            nm = rd(c, q(c, names + i * 8), 40).split(b"\0")[0].decode("latin1")
            r = rd(c, arr + i * 0xB0, 0xB0)
            fl = struct.unpack_from("<I", r, 0)[0]
            sc = struct.unpack_from("<2f", r, 0x60)
            ps = struct.unpack_from("<2f", r, 0x6C)
            sz = struct.unpack_from("<2f", r, 0x74)
            if i in (1, 8, 11, 12, 17):
                fl_ = struct.unpack_from("<44f", r, 0)
                print("      floats 0x40..0x7C:", " ".join(f"{x:.2f}" for x in fl_[16:32]))
            print(f"{i:2d} {nm:28s} flags {fl:#010x} scale {sc[0]:8.3f} {sc[1]:8.3f} pos {ps[0]:9.2f} {ps[1]:9.2f} f74 {sz[0]:9.2f} {sz[1]:9.2f}")
    finally:
        p.kill()


if __name__ == "__main__":
    main()
