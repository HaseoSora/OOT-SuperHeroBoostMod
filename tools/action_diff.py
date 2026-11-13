"""Find Link's action-state fields: sample the player component while injecting actions.

Usage: python tools/action_diff.py [size_hex] [exp,...]   (needs g_link_player published by core/player.c)
Prints, per experiment, the 4-byte words that differ from the idle baseline (idle noise removed).
"""
import os, struct, subprocess, sys, threading, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, log_addr, wait_for_status, symbols

EXPERIMENTS = {
    "roll": [{"buttons": ["A"], "frames": 8, "left_stick": [0.0, 1.0]}],
    "jump": [{"buttons": ["X"], "frames": 8}],
    "sprint": [{"buttons": ["A"], "frames": 150, "left_stick": [0.0, 1.0]}],
    "attack": [{"buttons": ["Y"], "frames": 8}],
    "sling": [{"buttons": ["ZR"], "frames": 90}],
    "run": [{"buttons": [], "frames": 150, "left_stick": [0.0, 1.0]}],
}


def words(b):
    return struct.unpack("<%dI" % (len(b) // 4), b)


def main():
    size = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x2000
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else list(EXPERIMENTS)
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
        pl = struct.unpack("<Q", bytes(c.read(mb + syms["g_link_player"], 8)))[0]
        print("player component", hex(pl))
        c2 = DebugClient(port=PORT, timeout=10)
        # idle baseline with noise detection
        base = [words(bytes(c2.read(pl, size))) for _ in range(4)]
        noise = {i for i in range(len(base[0])) if len({s[i] for s in base}) > 1}
        print("idle noise words:", len(noise))
        for name in names:
            steps = EXPERIMENTS[name]
            snaps = []
            done = threading.Event()

            def run():
                try:
                    c.input(steps)
                finally:
                    done.set()

            t = threading.Thread(target=run); t.start()
            t0 = time.time()
            while not done.is_set() and time.time() - t0 < 6:
                snaps.append((time.time() - t0, words(bytes(c2.read(pl, size)))))
            t.join()
            for _ in range(6):
                snaps.append((time.time() - t0, words(bytes(c2.read(pl, size)))))
                time.sleep(0.15)
            after = snaps[-1][1]
            out = []
            for i in range(len(base[0])):
                if i in noise:
                    continue
                vals = [s[1][i] for s in snaps]
                if any(v != base[0][i] for v in vals):
                    out.append((i * 4, base[0][i], sorted(set(vals))[:6], after[i]))
            print(f"== {name}: {len(snaps)} samples, {len(out)} changed words")
            for off, b, vs, a in out[:60]:
                print(f"   +{off:#06x} base {b:#x} seen {[hex(v) for v in vs]} end {a:#x}")
            time.sleep(4)
    finally:
        p.kill()


if __name__ == "__main__":
    main()
