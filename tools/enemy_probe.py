"""Boot, wait for enemies, and dump the strings found in every component of the listed enemies, three times."""
import os, re, struct, subprocess, sys, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, log_addr, wait_for_status, symbols


def rd(c, a, n):
    try:
        return bytes(c.read(a, n))
    except Exception:
        return b""


def q(c, a):
    b = rd(c, a, 8)
    return struct.unpack("<Q", b)[0] if len(b) == 8 else 0


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
        time.sleep(35)
        mb = log_addr("main")
        snaps = []
        for rnd in range(3):
            raw = rd(c, mb + syms["g_el"], 8 * 16)
            names = rd(c, mb + syms["g_el_name"], 8 * 32)
            snap = {}
            for i in range(8):
                actor, comp = struct.unpack_from("<QQ", raw, i * 16)
                if not actor:
                    continue
                nm = names[i * 32:(i + 1) * 32].split(b"\0")[0].decode("latin1")
                strs = {}
                tab = rd(c, comp, 0x400)
                for j in range(0, len(tab) - 7, 8):
                    ptr = struct.unpack_from("<Q", tab, j)[0]
                    if 0x10000000 < ptr < 0x7fffffffff:
                        blob = rd(c, ptr, 0x600)
                        for m in re.finditer(rb"[A-Za-z][A-Za-z0-9_]{3,20}\x00", blob):
                            strs[(j, m.start())] = m.group()[:-1].decode()
                snap[i] = (nm, actor, strs)
            snaps.append(snap)
            time.sleep(4)
        for i in snaps[0]:
            nm, actor, s0 = snaps[0][i]
            print(f"== enemy {i} {nm} actor {actor:#x}")
            keys = set(s0)
            for sn in snaps[1:]:
                if i in sn:
                    keys |= set(sn[i][2])
            for k in sorted(keys):
                vals = [sn[i][2].get(k) for sn in snaps if i in sn]
                if len(set(vals)) > 1:
                    print(f"   comp+{k[0]:#x} obj+{k[1]:#x}: {vals}")
    finally:
        p.kill()


if __name__ == "__main__":
    main()
