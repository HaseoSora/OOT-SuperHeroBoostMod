"""Dump the printable strings stored inside the player's player component (idle, then guarding) to find state-name fields."""
import os, re, struct, subprocess, sys, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, log_addr, wait_for_status, symbols

def strings(b, base):
    return {base + m.start(): m.group().decode() for m in re.finditer(rb"[A-Za-z_][A-Za-z0-9_]{3,30}", b)}

syms = symbols()
env = dict(os.environ, EDEN_NX2_DEBUG_SERVER=f"127.0.0.1:{PORT}")
p = subprocess.Popen([str(FRITCHII / "lichii.exe"), "-g", str(GAME)], cwd=str(FRITCHII), env=env)
try:
    c = DebugClient(port=PORT, timeout=10); wait_for_status(c)
    time.sleep(35)
    for _ in range(4):
        c.input([{"buttons": ["A"], "frames": 20}]); time.sleep(6)
    time.sleep(45)
    mb = log_addr("main")
    pl = struct.unpack("<Q", bytes(c.read(mb + syms["g_player_comp"], 8)))[0]
    def dump():
        out = {}
        for off in range(0, 0xC00, 0x200):
            out.update(strings(bytes(c.read(pl + off, 0x200)), off))
        return out
    idle = dump()
    import threading
    t = threading.Thread(target=lambda: c.input([{"buttons": ["ZL", "R"], "frames": 240}])); t.start()
    time.sleep(2.5)
    c2 = DebugClient(port=PORT, timeout=10)
    out = {}
    for off in range(0, 0xC00, 0x200):
        out.update(strings(bytes(c2.read(pl + off, 0x200)), off))
    t.join()
    print("IDLE:", {hex(k): v for k, v in sorted(idle.items())})
    print("GUARD:", {hex(k): v for k, v in sorted(out.items())})
finally:
    p.kill()
