"""Sample the action-state name string at player+0x244 while injecting actions.

Usage: python tools/action_names.py [exp,...]   (experiments in EXPERIMENTS below)
Prints the sequence of distinct names seen per experiment.
"""
import os, struct, subprocess, sys, threading, time
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
from lichii import DebugClient
sys.path.insert(0, os.path.dirname(__file__))
from live_check import FRITCHII, GAME, PORT, log_addr, wait_for_status, symbols

NAME_OFF = 0x244
EXPERIMENTS = {
    "roll": [{"buttons": ["A"], "frames": 8, "left_stick": [0.0, 1.0]}],
    "jump": [{"buttons": ["X"], "frames": 8}],
    "attack": [{"buttons": ["Y"], "frames": 8}],
    "sprint": [{"buttons": ["A"], "frames": 120, "left_stick": [0.0, 1.0]}],
    "run": [{"buttons": [], "frames": 90, "left_stick": [0.0, 1.0]}],
    "a_idle": [{"buttons": ["A"], "frames": 8}],
    "backflip": [{"buttons": ["A"], "frames": 8, "left_stick": [0.0, -1.0]}],
    "side": [{"buttons": ["A"], "frames": 8, "left_stick": [1.0, 0.0]}],
    "zl": [{"buttons": ["ZL"], "frames": 60}],
    "zl_y": [{"buttons": ["ZL", "Y"], "frames": 10}],
    "r": [{"buttons": ["R"], "frames": 60}],
    "l": [{"buttons": ["L"], "frames": 60}],
    "b": [{"buttons": ["B"], "frames": 20}],
    "zr": [{"buttons": ["ZR"], "frames": 30}],
    "roll2": [{"buttons": [], "frames": 40, "left_stick": [0.0, 1.0]}, {"buttons": ["A"], "frames": 6, "left_stick": [0.0, 1.0]}],
    "sprint2": [{"buttons": [], "frames": 30, "left_stick": [0.0, 1.0]}, {"buttons": ["A"], "frames": 100, "left_stick": [0.0, 1.0]}],
    "back2": [{"buttons": [], "frames": 30, "left_stick": [0.0, -1.0]}, {"buttons": ["A"], "frames": 6, "left_stick": [0.0, -1.0]}],
    "side2": [{"buttons": ["ZL"], "frames": 30, "left_stick": [1.0, 0.0]}, {"buttons": ["ZL", "A"], "frames": 6, "left_stick": [1.0, 0.0]}],
    "zl_r": [{"buttons": ["ZL", "R"], "frames": 40}],
    "zl_zr": [{"buttons": ["ZL", "ZR"], "frames": 40}],
    "zl_b": [{"buttons": ["ZL", "B"], "frames": 40}],
    "zl_l": [{"buttons": ["ZL", "L"], "frames": 40}],
    "zl_a": [{"buttons": ["ZL", "A"], "frames": 20}],
    "r_zr": [{"buttons": ["R"], "frames": 6}, {"buttons": [], "frames": 10}, {"buttons": ["ZR"], "frames": 50}],
    "r_zr_r": [{"buttons": ["R"], "frames": 6}, {"buttons": [], "frames": 10}, {"buttons": ["R"], "frames": 6}, {"buttons": [], "frames": 10}, {"buttons": ["ZR"], "frames": 50}],
    "l_zr": [{"buttons": ["L"], "frames": 6}, {"buttons": [], "frames": 10}, {"buttons": ["ZR"], "frames": 50}],
    "zl_r_zr": [{"buttons": ["ZL", "R"], "frames": 6}, {"buttons": ["ZL"], "frames": 10}, {"buttons": ["ZL", "ZR"], "frames": 50}],
    "back_zl": [{"buttons": ["ZL"], "frames": 700, "left_stick": [0.0, -1.0]}, {"buttons": ["ZL"], "frames": 700}],
    "zl_backjump": [{"buttons": ["ZL"], "frames": 40, "left_stick": [0.0, -1.0]}, {"buttons": ["ZL", "X"], "frames": 8, "left_stick": [0.0, -1.0]}],
    "zl_sidejump": [{"buttons": ["ZL"], "frames": 40, "left_stick": [1.0, 0.0]}, {"buttons": ["ZL", "X"], "frames": 8, "left_stick": [1.0, 0.0]}],
    "zr_long": [{"buttons": ["ZR"], "frames": 150}],
    "zr_tap": [{"buttons": ["ZR"], "frames": 6}],
    "zl_zr_long": [{"buttons": ["ZL"], "frames": 20}, {"buttons": ["ZL", "ZR"], "frames": 150}],
    "l_long": [{"buttons": ["L"], "frames": 100}],
    "x_hold": [{"buttons": ["X"], "frames": 60}],
    "y_hold": [{"buttons": ["Y"], "frames": 70}],
    "a_hold": [{"buttons": ["A"], "frames": 70}],
}


def name_at(c, pl):
    try:
        b = bytes(c.read(pl + NAME_OFF, 40))
    except Exception:
        return '<timeout>'
    return b.split(b"\0")[0].decode("latin1")


def main():
    names = sys.argv[1].split(",") if len(sys.argv) > 1 else list(EXPERIMENTS)
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
        print("player component", hex(pl), "idle name:", name_at(c, pl))
        c2 = DebugClient(port=PORT, timeout=10)
        for name in names:
            steps = EXPERIMENTS[name]
            seq = []
            done = threading.Event()

            def run():
                try:
                    c.input(steps)
                finally:
                    done.set()

            t = threading.Thread(target=run); t.start()
            t0 = time.time()
            while not done.is_set() and time.time() - t0 < 40:
                n = name_at(c2, pl)
                if not seq or seq[-1][1] != n:
                    seq.append((round(time.time() - t0, 2), n))
            t.join()
            for _ in range(8):
                n = name_at(c2, pl)
                if not seq or seq[-1][1] != n:
                    seq.append((round(time.time() - t0, 2), n))
                time.sleep(0.15)
            print(f"== {name}: " + "  ".join(f"{t_}s:{n}" for t_, n in seq))
            time.sleep(3)
    finally:
        p.kill()


if __name__ == "__main__":
    main()
