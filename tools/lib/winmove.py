"""Keep the emulator window off the user's primary monitor while testing (Windows only).

move_to_secondary(pid) starts a daemon thread that looks for the process's top-level
windows and moves them onto a non-primary monitor (first one found). If there is only
one monitor nothing is moved.
"""
import ctypes
import threading
import time
from ctypes import wintypes

user32 = ctypes.windll.user32


def _monitors():
    rects = []

    @ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HANDLE, wintypes.HDC, ctypes.POINTER(wintypes.RECT),
                        wintypes.LPARAM)
    def cb(hmon, hdc, rect, data):
        r = rect.contents
        rects.append((r.left, r.top, r.right, r.bottom))
        return 1

    user32.EnumDisplayMonitors(0, 0, cb, 0)
    return rects


def _windows_of(pid):
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lp):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd):
            r = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            if r.right - r.left > 200 and r.bottom - r.top > 150:
                found.append((hwnd, r.left, r.top, r.right - r.left, r.bottom - r.top))
        return 1

    user32.EnumWindows(cb, 0)
    return found


def _run(pid, seconds):
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass
    done = set()
    t0 = time.time()
    while time.time() - t0 < seconds:
        mons = _monitors()
        if len(mons) < 2:
            return
        primary = (0, 0)
        secondary = [m for m in mons if (m[0], m[1]) != primary]
        if not secondary:
            return
        sx, sy, sr, sb = secondary[0]
        for hwnd, l, t, w, h in _windows_of(pid):
            inside = sx <= l < sr and sy <= t < sb
            if hwnd in done or inside:
                done.add(hwnd)
                continue
            user32.MoveWindow(hwnd, sx + 40, sy + 40, min(w, sr - sx - 80), min(h, sb - sy - 80), True)
            done.add(hwnd)
        time.sleep(0.4)


def move_to_secondary(pid, seconds=90):
    th = threading.Thread(target=_run, args=(pid, seconds), daemon=True)
    th.start()
    return th
