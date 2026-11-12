"""Disassemble a range of the stock main text (main-relative addresses).

Usage: python tools/disasm.py 0x1211c00 0x80
"""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from lib import nso

BIN = r"F:\project\oot\tools\llvm-mingw\llvm-mingw-20261104-ucrt-x86_64\bin"
STOCK = r"F:\project\oot\data\stock-exefs\main"
_cache = {}


def text():
    if "t" not in _cache:
        _cache["t"] = nso.text_bytes(open(STOCK, "rb").read())
    return _cache["t"]


def disasm(addr: int, size: int) -> str:
    t = text()
    with tempfile.TemporaryDirectory() as d:
        b = os.path.join(d, "x.bin"); o = os.path.join(d, "x.o")
        open(b, "wb").write(t[addr:addr + size])
        subprocess.run([BIN + r"\llvm-objcopy.exe", "-I", "binary", "-O", "elf64-littleaarch64",
                        "--rename-section", ".data=.text,code,alloc,load,readonly", b, o], check=True)
        out = subprocess.run([BIN + r"\llvm-objdump.exe", "-d", f"--adjust-vma={addr:#x}", o],
                             capture_output=True, text=True).stdout
    lines = [l for l in out.splitlines() if l.startswith(" ")]
    return "\n".join(l.replace("\t", "  ") for l in lines)


if __name__ == "__main__":
    print(disasm(int(sys.argv[1], 0), int(sys.argv[2], 0)))
