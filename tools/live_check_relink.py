"""Read-only diagnostic of the mod inside a running ReLink game.

ReLink compiles the game ahead of time, so there is no debugger to step through
guest code. What it does have is the game's memory: this tool finds the module's
SHBCFG01 block in the game process, derives the module base from it and prints

  * the configuration the module is really reading,
  * g_wrap_entry[5]: how many times each input wrapper ran (hooks.S),
  * g_code_entry[]: how many times each function-entry hook ran (frame, HUD...).

Nothing is written and the game is not touched. If the counters do not move
while the game runs, the input hooks are not being called; if they move but the
features do nothing, the problem is in what the wrapper sees (the sample buffer).

Usage:
  python tools/live_check_relink.py                 # snapshot + 3 s of deltas
  python tools/live_check_relink.py --watch 30      # one line a second for 30 s
  python tools/live_check_relink.py --pid 1234
"""
from __future__ import annotations

import argparse
import ctypes
import os
import struct
import subprocess
import sys
from ctypes import wintypes as w
from pathlib import Path

MAGIC = b"SHBCFG01"
# Offsets inside the module (build/native/module.elf, llvm-nm), link base 0x4F80000.
LINK_BASE = 0x4F80000
SYMBOLS = {
    "g_shbcfg": 0x4F91010,
    "g_wrap_entry": 0x4F92838,
    "g_code_entry": 0x4F9285C,
    "g_st_count": 0x4F92948,
    "g_st_seen": 0x4F92950,
    "g_cl_prev": 0x5459818,
    "g_dbg_btn": 0x5459848,
    "g_sprint_a": 0x54596FC,
    "g_l3_a": 0x54596F0,
    "g_player_comp": 0x4F92400,
    "g_player_life": 0x4F923E4,
    "g_alive": 0x5458E48,
    "g_ps_frame": 0x54573C8,
}
CONFIG_OFF = SYMBOLS["g_shbcfg"] - LINK_BASE          # 0x11010
K32 = ctypes.WinDLL("kernel32", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
TH32CS_SNAPPROCESS = 0x00000002
MEM_COMMIT = 0x1000
READABLE = {0x02, 0x04, 0x08, 0x20, 0x40, 0x80}       # PAGE_* read


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", w.DWORD), ("RegionSize", ctypes.c_size_t),
                ("State", w.DWORD), ("Protect", w.DWORD), ("Type", w.DWORD)]


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
                ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)), ("th32ModuleID", w.DWORD),
                ("cntThreads", w.DWORD), ("th32ParentProcessID", w.DWORD),
                ("pcPriClassBase", ctypes.c_long), ("dwFlags", w.DWORD),
                ("szExeFile", w.WCHAR * 260)]


def symbols_from_elf() -> dict[str, int]:
    """Refresh the offsets from build/native/module.elf when llvm-nm is around."""
    out = dict(SYMBOLS)
    nm = Path(os.environ.get("SHB_LLVM", r"F:\project\oot\tools\llvm-mingw\llvm-mingw-20261104-ucrt-x86_64\bin")) / "llvm-nm.exe"
    elf = Path(__file__).resolve().parent.parent / "build" / "native" / "module.elf"
    if not nm.exists() or not elf.exists():
        return out
    try:
        txt = subprocess.run([str(nm), "-n", str(elf)], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return out
    want = set(out)
    for line in txt.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] in want:
            out[parts[2]] = int(parts[0], 16)
    return out


def find_pid() -> int | None:
    snap = K32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == w.HANDLE(-1).value:
        return None
    entry = PROCESSENTRY32W()
    entry.dwSize = ctypes.sizeof(entry)
    pid = None
    try:
        ok = K32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            if entry.szExeFile.lower() == "relink-game.exe":
                pid = int(entry.th32ProcessID)
                break
            ok = K32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        K32.CloseHandle(snap)
    return pid


def read(h, addr: int, size: int) -> bytes | None:
    buf = ctypes.create_string_buffer(size)
    got = ctypes.c_size_t(0)
    if not K32.ReadProcessMemory(h, ctypes.c_void_p(addr), buf, ctypes.c_size_t(size), ctypes.byref(got)):
        return None
    return buf.raw[:got.value]


def find_magic(h, lo: int, hi: int) -> int | None:
    addr = lo
    while addr < hi:
        mbi = MBI()
        if not K32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            addr += 0x1000
            continue
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize
        if size == 0:
            break
        if base + size <= lo:
            addr = base + size
            continue
        if base >= hi:
            break
        start, end = max(base, lo), min(base + size, hi)
        if (mbi.State == MEM_COMMIT and not (mbi.Protect & 0x100)
                and (mbi.Protect & 0xFF) in READABLE):
            p = start
            while p < end:
                chunk = min(0x400000, end - p)
                data = read(h, p, chunk)
                if data:
                    i = data.find(MAGIC)
                    if i >= 0:
                        return p + i
                p += chunk
        addr = base + size
    return None


def u32_array(h, addr: int, n: int) -> list[int] | None:
    data = read(h, addr, 4 * n)
    if not data or len(data) < 4 * n:
        return None
    return list(struct.unpack("<%dI" % n, data))


def describe_config(raw: bytes) -> str:
    """Field offsets from core/config.h (magic at 0, f = magic+16)."""
    u8 = lambda o: raw[o]
    u16 = lambda o: struct.unpack_from("<H", raw, o)[0]
    i16 = lambda o: struct.unpack_from("<h", raw, o)[0]
    styles = {0: "Switch", 1: "Xbox", 2: "PlayStation"}
    parts = [
        f"stamina={u8(16)} preset={u8(17)}",
        f"costs(j/a/s/b/sh/r)={u8(18)}{u8(19)}{u8(20)}{u8(21)}{u8(22)}{u8(23)}",
        f"combat_only={u8(24)}",
        f"enemy_hp={u16(26)} dmg={u16(28)}",
        f"hud(rupees/clock/24h/collect)={u8(30)}{u8(31)}{u8(32)}{u8(33)}",
        f"sprint={u16(34)}",
        f"songbook={u8(36)} mapping={u8(37)} style={styles.get(u8(38), u8(38))} "
        f"bm_simple={u8(39)} bm_l={u8(40)}",
        f"quick(boots/mask)={u8(41)}{u8(42)}",
        f"stamina_bar={u8(52)} hud_flags={u8(53)} hud_mode={u8(54)} plates={u8(59)} map_hearts={u8(60)}",
        f"hud_y={i16(62)} hud_x={[i16(44 + 2 * k) for k in range(4)]}",
        f"manual_shield={u8(70)} target_r3={u8(71)} sprint_l3={u8(72)}",
    ]
    return "  ".join(parts)


def snapshot(h, base: int) -> tuple[list[int], list[int], bytes]:
    wrap = u32_array(h, base + SYMBOLS["g_wrap_entry"] - LINK_BASE, 5) or [0] * 5
    code = u32_array(h, base + SYMBOLS["g_code_entry"] - LINK_BASE, 24) or [0] * 24
    cfg = read(h, base + CONFIG_OFF, 0x4C) or b""
    return wrap, code, cfg


def read_int(h, addr: int, n: int):
    data = read(h, addr, n)
    if not data or len(data) < n:
        return None
    return int.from_bytes(data, "little")


def extra_state(h, base: int) -> dict:
    """The debug globals the features keep (what they see, not just how often)."""
    def at(name):
        return base + SYMBOLS[name] - LINK_BASE
    btns = read(h, at("g_dbg_btn"), 16)
    return {
        "st_count": read_int(h, at("g_st_count"), 4),
        "st_seen": (lambda v: hex(v) if v is not None else None)(read_int(h, at("g_st_seen"), 8)),
        "cl_prev": (lambda v: hex(v) if v is not None else None)(read_int(h, at("g_cl_prev"), 8)),
        "dbg_btn": list(struct.unpack("<4I", btns)) if btns and len(btns) == 16 else None,
        "sprint_a": read_int(h, at("g_sprint_a"), 4),
        "l3_a": read_int(h, at("g_l3_a"), 4),
        "player_comp": (lambda v: hex(v) if v is not None else None)(read_int(h, at("g_player_comp"), 8)),
        "player_life": read_int(h, at("g_player_life"), 8),
        "alive": read_int(h, at("g_alive"), 4),
        "ps_frame": (lambda v: hex(v) if v is not None else None)(read_int(h, at("g_ps_frame"), 8)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", type=int)
    ap.add_argument("--watch", type=int, default=0, help="print every second for N seconds")
    ap.add_argument("--delay", type=float, default=3.0, help="seconds between the two snapshots")
    ap.add_argument("--lo", default="0x100080000000",
                    help="host address of the guest image window (A64_HOST_BASE + 0x80000000)")
    ap.add_argument("--hi", default="0x100090000000")
    a = ap.parse_args()

    if os.name != "nt":
        print("This tool reads a Windows process (ReLink is a Windows build).")
        return 2
    pid = a.pid or find_pid()
    if not pid:
        print("relink-game.exe is not running: open the game and run this again.")
        return 1
    h = K32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not h:
        print(f"cannot open relink-game.exe (pid {pid}): {ctypes.get_last_error()}")
        return 1
    syms = symbols_from_elf()
    print(f"pid {pid}  symbols: g_shbcfg {syms['g_shbcfg']:#x} "
          f"g_wrap_entry {syms['g_wrap_entry']:#x} g_code_entry {syms['g_code_entry']:#x}")
    try:
        at = find_magic(h, int(a.lo, 0), int(a.hi, 0))
        if at is None:
            print("SHBCFG01 not found: the mod is not in this build (or the game has not loaded yet).")
            return 1
        base = at - (syms["g_shbcfg"] - LINK_BASE)
        print(f"module config at {at:#x} -> module base {base:#x}")
        wrap, code, cfg = snapshot(h, base)
        if len(cfg) < 0x4C or cfg[:8] != MAGIC:
            print("config block is not readable")
            return 1
        print("config:", describe_config(cfg))
        print("g_wrap_entry:", wrap)
        print("g_code_entry:", {i: v for i, v in enumerate(code) if v})
        print("state:", extra_state(h, base))

        if a.watch:
            prev = (wrap, code)
            for _ in range(a.watch):
                import time
                time.sleep(1)
                wrap, code, _ = snapshot(h, base)
                dw = [b - x for b, x in zip(wrap, prev[0])]
                dc = {i: code[i] - prev[1][i] for i in range(len(code)) if code[i] != prev[1][i]}
                print(f"  wrap {wrap}  +{dw}   code +{dc}")
                print(f"  state {extra_state(h, base)}")
                prev = (wrap, code)
        else:
            import time
            time.sleep(max(0.0, a.delay))
            wrap2, code2, _ = snapshot(h, base)
            dw = [b - x for b, x in zip(wrap2, wrap)]
            dc = {i: code2[i] - code[i] for i in range(len(code2)) if code2[i] != code[i]}
            print(f"after {a.delay:.1f} s -> g_wrap_entry {wrap2}  (+{dw})   g_code_entry +{dc}")
            if not any(dw):
                print("the input wrappers did not run: the five call sites are not reaching hook_input*.")
            if not dc:
                print("the function-entry hooks (frame/HUD) did not run either.")
    finally:
        K32.CloseHandle(h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
