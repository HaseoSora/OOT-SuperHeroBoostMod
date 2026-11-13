"""Dump HUD pane records (0xB0 each) behind the captured magic-gauge controller."""
import os, struct, subprocess, sys, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, log_addr, wait_for_status, symbols

def rd(c, a, n): return bytes(c.read(a, n))
def q(c, a): return struct.unpack("<Q", rd(c, a, 8))[0]

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
        time.sleep(30)
        mb = log_addr("main")
        d = struct.unpack("<8Q", rd(c, mb + syms["g_hud_dbg"], 64))
        M = 0x1000000000000000
        mp, bar = d[0] - M, d[2] - M
        owner = q(c, mp + 0x18); parent = q(c, owner + 0x28)
        lay = q(c, parent + 0x80); arr = q(c, lay + 0x100)
        print("mp", hex(mp), "bar", hex(bar), "parent", hex(parent), "arr", hex(arr))
        def dump(name, a, n):
            b = rd(c, a, n)
            print(f"-- {name} @ {a:#x}")
            for o in range(0, n, 16):
                w = struct.unpack_from("<4I", b, o)
                f = struct.unpack_from("<4f", b, o)
                print(f"+{o:03x}: " + " ".join(f"{x:08x}" for x in w) + "   " +
                      " ".join(f"{x:9.3g}" for x in f))
        from lib.cityhash import city_hash64
        root = q(c, lay + 0xF8)
        print("root", hex(root), "magic", rd(c, root, 4), "asset", rd(c, q(c, root + 0x18), 24))
        for off, label in ((0x20, "common"), (0xC0, "parts")):
            names, descs, hashes = q(c, root + off), q(c, root + off + 8), q(c, root + off + 16)
            cnt = struct.unpack("<I", rd(c, root + off + 24, 4))[0]
            print(f"-- {label}: count {cnt}")
            for i in range(cnt):
                nm = rd(c, q(c, names + i * 8), 40).split(b"\0")[0]
                hv = q(c, hashes + i * 8)
                ok = "OK" if city_hash64(nm) == hv else f"MISMATCH calc {city_hash64(nm):#x}"
                print(f"{i:2d} {nm.decode(errors='replace'):28s} hash {hv:#018x} {ok}")
        for off, label, idxs, size in ((0x20, "common", (8, 18, 33, 34, 35), 68),
                                       (0xC0, "parts", (1, 4, 7, 8, 9), 88)):
            descs = q(c, root + off + 8)
            for i in idxs:
                try:
                    d = rd(c, q(c, descs + i * 8), size)
                except Exception as e:
                    print(label, i, "ERR", e); continue
                words = struct.unpack("<%dI" % (size // 4), d)
                print(f"desc {label}[{i}]:", " ".join(f"{x:08x}" for x in words))
        # children list that find_part walks: sentinel layout+0x128, first entry at layout+0x130
        sent = lay + 0x128
        p = q(c, lay + 0x130)
        n = 0
        print("-- registered children (find_part list):")
        while p != sent and n < 80:
            try:
                nm = rd(c, q(c, p + 0x148), 40).split(b"\0")[0].decode(errors="replace")
            except Exception as e:
                nm = f"<err {e}>"
            print(f"  {n:2d} entry {p:#x} name {nm}")
            p = q(c, p + 8)
            n += 1
        # child layout of our gauge part: panes, names and transforms
        cl = q(c, bar + 0x80)
        print("-- child layout", hex(cl))
        croot = q(c, cl + 0xF8)
        cnt = struct.unpack("<H", rd(c, cl + 0x13C, 2))[0]
        cnames = q(c, croot + 0x20)
        carr = q(c, cl + 0x100)
        print("child root asset", rd(c, q(c, croot + 0x18), 24).split(b"\0")[0], "panes", cnt)
        for i in range(cnt):
            nm = rd(c, q(c, cnames + i * 8), 40).split(b"\0")[0].decode(errors="replace")
            rec = rd(c, carr + i * 0xB0, 0xB0)
            flags = struct.unpack_from("<I", rec, 0)[0]
            sx, sy = struct.unpack_from("<ff", rec, 0x60)
            px, py = struct.unpack_from("<ff", rec, 0x6C)
            print(f"  c{i:2d} {nm:24s} flags={flags:#010x} scale=({sx:.2f},{sy:.2f}) pos=({px:.1f},{py:.1f}) a8={struct.unpack_from('<I',rec,0xA8)[0]:#010x}")
        for i in (6, 11, 13, 17, 19):
            rec = rd(c, carr + i * 0xB0, 0xB0)
            print(f"-- child pane c{i} record")
            for o in range(0, 0xB0, 16):
                w4 = struct.unpack_from("<4I", rec, o); f4 = struct.unpack_from("<4f", rec, o)
                print(f"   +{o:02x}: " + " ".join(f"{x:08x}" for x in w4) + "  " + " ".join(f"{x:9.3g}" for x in f4))
        dump("root header", root, 0x230)
        dump("mp", mp, 0x40)
        dump("owner", owner, 0x60)
        dump("bar", bar, 0xC0)
        for i in range(30, 40):
            rec = rd(c, arr + i * 0xB0, 0xB0)
            flags = struct.unpack_from("<I", rec, 0)[0]
            sx, sy = struct.unpack_from("<ff", rec, 0x60)
            px, py = struct.unpack_from("<ff", rec, 0x6C)
            print(f"{i:2d} flags={flags:#010x} scale=({sx:.2f},{sy:.2f}) pos=({px:.1f},{py:.1f})")
        print("bar bytes:", rd(c, bar, 0x60).hex())
        png, w, h = c.screenshot()
        open(os.path.join(os.path.dirname(__file__), "..", "build", "pane_dump.png"), "wb").write(png)
    finally:
        p.kill()

main()

