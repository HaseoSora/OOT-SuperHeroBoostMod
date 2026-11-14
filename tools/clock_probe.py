"""Boot, load the save, then sample the two clock sources once a second while the player runs."""
import os, struct, subprocess, sys, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, log_addr, wait_for_status, symbols
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
    time.sleep(45)
    mb = log_addr("main")
    c.input([{"left_stick": [0.0, 1.0], "frames": 1800}])
    t0 = time.time()
    for i in range(50):
        g, w = struct.unpack("<II", bytes(c.read(mb + syms["g_clk_dbg"], 8)))
        print(f"{time.time()-t0:5.1f}s gd={g} ({g//3600}:{g//60%60:02d}:{g%60:02d}) wo={w}", flush=True)
        time.sleep(1)
finally:
    proc.kill()
