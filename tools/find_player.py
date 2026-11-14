"""Find objects whose first qword is the player-type vtable (main+0x4B4C460) and print their resource names."""
import os, struct, subprocess, sys, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, log_addr, wait_for_status


def rd(c, a, n): return bytes(c.read(a, n))
def q(c, a): return struct.unpack("<Q", rd(c, a, 8))[0]


def main():
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
        vt = mb + 0x4B4C460
        print("main", hex(mb), "vtable", hex(vt))
        hits, complete = c.search(struct.pack("<Q", vt), regions="heap", max_hits=64, total_ms=20000)
        print(len(hits), "hits, complete", complete)
        P = None
        for h in hits[:64]:
            a = h if isinstance(h, int) else h.get("addr", h)
            if rd(c, q(c, a + 0x10) + 0x58, 7) == b"Player\0":
                P = a
                break
        print("the player player-type object", hex(P) if P else None)
        if P:
            mvp = P + 0x1D50
            for label, val in (("movement ptr", mvp), ("player obj ptr", P)):
                h2, _ = c.search(struct.pack("<Q", val), regions="heap", max_hits=16, total_ms=20000)
                print(label, hex(val), "referenced at", [hex(x if isinstance(x, int) else x.get("addr")) for x in h2])
                for x in h2:
                    xa = x if isinstance(x, int) else x.get("addr")
                    h3, _ = c.search(struct.pack("<Q", xa - (0x320 if label == "movement ptr" else 0)), regions="heap", max_hits=8, total_ms=10000)
                    print("   table candidate", hex(xa - (0x320 if label == "movement ptr" else 0)), "referenced at", [hex(y if isinstance(y, int) else y.get("addr")) for y in h3])
        for h in hits[:0]:
            a = h if isinstance(h, int) else h.get("addr", h)
            try:
                res = q(c, a + 0x10)
                nm = rd(c, res + 0x58, 24).split(b"\0")[0].decode("latin1") if res else ""
            except Exception as e:
                nm = f"<{str(e)[:30]}>"
            print(f"  {a:#x}  res+0x58 = {nm!r}")
    finally:
        p.kill()


if __name__ == "__main__":
    main()
