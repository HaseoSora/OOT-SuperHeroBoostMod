"""Boot, load the save, then sample the clock text every 15 s (does the world time advance?)."""
import os, struct, subprocess, sys, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, log_addr, wait_for_status, symbols

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
        for i in range(14):
            q = lambda a: struct.unpack("<Q", bytes(c.read(a, 8)))[0]
            mgr = q(mb + 0x4E842A8)
            rec = q(mgr + 8 + 0x60 * 24 + 0x10)
            vals = [q(rec + k * 0x30 + 0x20) for k in range(6)]
            wm = q(mb + 0x4E7EAB0)
            obj = q(wm + 0x578) if wm else 0
            print(i, [hex(v) for v in vals], "obj", hex(obj), flush=True)
            c.input([{"left_stick": [0.0, 1.0], "frames": 600}])
            time.sleep(20)
    finally:
        proc.kill()
main()
