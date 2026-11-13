import os, subprocess, sys, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, wait_for_status, LOG
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
    time.sleep(90)
    c.input([{"left_stick": [0.0, 1.0], "frames": 900}])
    time.sleep(40)
finally:
    proc.kill()
lines = [l for l in open(LOG, errors="ignore") if "timekeeper" in l or "IPS" in l]
print("".join(lines[:6])); print("...") ; print("".join(lines[-12:]))
