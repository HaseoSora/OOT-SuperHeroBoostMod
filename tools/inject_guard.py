"""Pipeline test: write the state name 'GuardHit' into the player's player component (as if a shield hit happened) and check
that the module charges stamina for it. Does not prove the game's real block state name, only the cost path."""
import os, struct, subprocess, sys, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient, HostMemory
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, log_addr, wait_for_status, symbols
name = sys.argv[1] if len(sys.argv) > 1 else "GuardHit"
syms = symbols()
env = dict(os.environ, EDEN_NX2_DEBUG_SERVER=f"127.0.0.1:{PORT}")
p = subprocess.Popen([str(FRITCHII / "lichii.exe"), "-g", str(GAME)], cwd=str(FRITCHII), env=env)
try:
    c = DebugClient(port=PORT, timeout=10); wait_for_status(c)
    time.sleep(35)
    for _ in range(4):
        c.input([{"buttons": ["A"], "frames": 20}]); time.sleep(6)
    time.sleep(80)
    mb = log_addr("main")
    hm = HostMemory(p.pid); hm.calibrate(c, [mb])
    pl = struct.unpack("<Q", bytes(c.read(mb + syms["g_player_comp"], 8)))[0]
    print("pl", hex(pl), "arena", hex(hm.arena), "mb", hex(mb)); print(hm.hread(hm.arena+pl+0x244,16))
    def f(n): return struct.unpack("<f", bytes(c.read(mb + syms[n], 4)))[0]
    def u(n): return struct.unpack("<I", bytes(c.read(mb + syms[n], 4)))[0]
    print("stamina before", f("g_stamina"), "guard costed", u("g_st_guard"))
    low = 1e9
    for i in range(6):
        hm.write(pl + 0x244, name.encode() + b"\0")
        time.sleep(0.05)
        low = min(low, f("g_stamina"))
        time.sleep(0.4)
    print("lowest stamina", low, "guard costed", u("g_st_guard"), "events guard", u("g_ev") if False else struct.unpack("<5I", bytes(c.read(mb + syms["g_ev"], 20))))
finally:
    p.kill()
