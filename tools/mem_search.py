"""Launch the game to gameplay and search guest memory for byte patterns.

Usage: python tools/mem_search.py "PaSelectItem" "GaugeRatio" ...
Prints hit addresses and the printable strings around each hit.
"""
import os, re, subprocess, sys, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, wait_for_status


def strings_near(c, addr, before=0x100, after=0x300):
    b = bytes(c.read(addr - before, before + after))
    return [s.decode() for s in re.findall(rb"[A-Za-z0-9_\-\.]{4,48}", b)]


def main():
    pats = sys.argv[1:]
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
        for pat in pats:
            raw = pat[:-1].encode() if pat.endswith("*") else pat.encode() + b"\0"   # "abc*" = prefix
            hits, done = c.search(raw, regions="all", max_hits=6, total_ms=90000)
            print("==", pat, "->", [hex(h) for h in hits], "complete" if done else "partial")
            for addr in hits[:3]:
                seen = []
                for s in strings_near(c, addr, 0x40, 0x1800):
                    if s not in seen:
                        seen.append(s)
                print(f"  {addr:#x}:", " ".join(seen)[:1500])
    finally:
        p.kill()


main()

