"""Find which key of the debug server's input steps drives the left stick (reads g_st_dbg run frames)."""
import os, struct, subprocess, sys, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, log_addr, wait_for_status, symbols

KEYS = ["left_stick", "stick", "lstick", "ls", "l_stick", "leftStick", "axes", "lx"]


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
        def rd():
            return struct.unpack("<4I", bytes(c.read(mb + syms["g_st_dbg"], 16)))
        for k in KEYS:
            val = [1.0, 0.0] if k not in ("lx",) else 1.0
            before = rd()
            try:
                c.input([{"buttons": [], k: val, "frames": 30}])
                res = "ok"
            except Exception as e:
                res = str(e)[:80]
            after = rd()
            print(k, res, "run frames +", after[2] - before[2], "stamina?")
            time.sleep(1.0)
    finally:
        p.kill()


if __name__ == "__main__":
    main()
