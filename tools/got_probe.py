"""Read the five import stubs and their GOT slots from a running emulator."""
import os, re, struct, subprocess, sys, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, LOG, PORT, log_addr, wait_for_status

STUBS = [0x3C427F0, 0x3C42810, 0x3C42820, 0x3C42800, 0x3C42830]

def main():
    env = dict(os.environ, EDEN_NX2_DEBUG_SERVER=f"127.0.0.1:{PORT}")
    p = subprocess.Popen([str(FRITCHII / "lichii.exe"), "-g", str(GAME)], cwd=str(FRITCHII), env=env)
    try:
        from lib.winmove import move_to_secondary
        move_to_secondary(p.pid)
        c = DebugClient(port=PORT, timeout=10)
        wait_for_status(c)
        time.sleep(float(sys.argv[1]) if len(sys.argv) > 1 else 40)
        mb = log_addr("main"); sb = log_addr("subsdk9")
        print("main", hex(mb), "sub", sb and hex(sb))
        for s in STUBS:
            code = struct.unpack("<4I", bytes(c.read(mb + s, 16)))
            # adrp x16,#imm ; ldr x17,[x16,#off]
            w0, w1 = code[0], code[1]
            immlo = (w0 >> 29) & 3; immhi = (w0 >> 5) & 0x7FFFF
            imm = ((immhi << 2) | immlo) << 12
            if imm & (1 << 32): imm -= 1 << 33
            page = ((s & ~0xFFF) + imm)
            off = ((w1 >> 10) & 0xFFF) * 8
            got = page + off
            val = struct.unpack("<Q", bytes(c.read(mb + got, 8)))[0]
            print(f"stub {s:#x} got {got:#x} val {val:#x} (rel main {val-mb:#x}, rel sub {sb and val-sb:#x})")
    finally:
        p.kill()

main()

