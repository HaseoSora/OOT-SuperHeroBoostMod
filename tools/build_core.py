"""Build our subsdk9 module (core + enabled features) and its main IPS.

Usage:
    python tools/build_core.py                  # default features: probe
    python tools/build_core.py --features probe

Outputs (build/native/exefs):
    subsdk9                              our module (NSO0, uncompressed)
    E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348.ips   one IPS32 for main

The toolchain (clang/lld/objcopy) is the llvm-mingw from the previous
workspace. It is only used as a compiler. The stock `main` is read only to
verify that each hook site really is the `bl` we expect; nothing is copied
from it.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hook_sites import (CODE_SITES, DISABLED_SITES, INPUT_SITES, PACIBSP,  # noqa: E402
                        SLOT_SITES, SLOT_STOCK)

ROOT = Path(__file__).resolve().parent.parent
TOOLCHAIN_BIN = Path(
    r"F:\project\oot\tools\llvm-mingw\llvm-mingw-20261104-ucrt-x86_64\bin"
)
CLANG = TOOLCHAIN_BIN / "clang.exe"
LLD = TOOLCHAIN_BIN / "ld.lld.exe"
OBJCOPY = TOOLCHAIN_BIN / "llvm-objcopy.exe"
SIZE = TOOLCHAIN_BIN / "llvm-size.exe"
NM = TOOLCHAIN_BIN / "llvm-nm.exe"

STOCK_MAIN = Path(r"F:\project\oot\data\stock-exefs\main")
MAIN_BUILD_ID = "E0F3CCFAF50065AE4EA01EB5AEB13B1A45DA3348"

BASE = 0x4F80000
OUT = ROOT / "build" / "native"
CORE_SRC = ROOT / "core"
FEATURES_SRC = ROOT / "features"
LINK_SCRIPT = CORE_SRC / "link.ld"

CFLAGS = [
    "-target", "aarch64-none-elf",
    "-ffreestanding", "-nostdlib",
    "-fno-stack-protector", "-fno-builtin",
    "-mno-outline-atomics", "-ffixed-x18",
    # The NSO has no relocations: jump tables and switch lookup tables hold link-time
    # absolute addresses that are wrong at runtime. This also turns off the lookup tables.
    "-fno-jump-tables",
    "-O2",
]

# Handler table entries per feature, per table
FEATURE_INPUT_HANDLERS = {
    "probe": ["probe_on_input"],
    "hero_core": ["hero_core_on_input"],
    "classic_slots": ["classic_slots_on_input"],
}
FEATURE_SLOT_HANDLERS = {
    "classic_slots": ["classic_slots_on_call"],
}


FEATURE_SLOT_PRE = {
    "classic_slots": ["classic_slots_pre"],
}


def run(args: list[str]) -> str:
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stdout.write(r.stdout)
        sys.stderr.write(r.stderr)
        raise SystemExit(f"command failed: {Path(args[0]).name}")
    return r.stdout


def section_info(elf: Path) -> dict[str, tuple[int, int]]:
    """Return {section: (size, address)} from llvm-size -A."""
    info: dict[str, tuple[int, int]] = {}
    for line in run([str(SIZE), "-A", str(elf)]).splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0].startswith("."):
            info[parts[0]] = (int(parts[1], 0), int(parts[-1], 0))
    return info


def symbol_table(elf: Path) -> dict[str, int]:
    syms: dict[str, int] = {}
    for line in run([str(NM), "-n", str(elf)]).splitlines():
        parts = line.split()
        if len(parts) == 3:
            syms[parts[2]] = int(parts[0], 16)
    return syms


def dump_section(elf: Path, name: str, scratch: Path) -> bytes:
    if scratch.exists():
        scratch.unlink()
    run([str(OBJCOPY), f"--dump-section={name}={scratch}", str(elf)])
    return scratch.read_bytes() if scratch.exists() else b""


def build_nso(text: bytes, ro: bytes, data: bytes,
              ro_rel: int, data_rel: int, bss_size: int) -> bytes:
    """Uncompressed NSO0 with a 0x100 header. Layout offsets are module-relative."""
    header = bytearray(0x100)
    header[0:4] = b"NSO0"
    text_off = 0x100
    ro_off = (text_off + len(text) + 0xFF) & ~0xFF
    data_off = (ro_off + len(ro) + 0xFF) & ~0xFF
    struct.pack_into("<III", header, 0x10, text_off, 0, len(text))
    struct.pack_into("<III", header, 0x20, ro_off, ro_rel, len(ro))
    struct.pack_into("<III", header, 0x30, data_off, data_rel, len(data))
    struct.pack_into("<I", header, 0x3C, bss_size)
    # Compressed sizes equal raw sizes for an uncompressed NSO. Zero here makes
    # the loader read nothing for the segments (crash on load, seen in F0).
    struct.pack_into("<III", header, 0x60, len(text), len(ro), len(data))
    # Module id at 0x40. No hash at 0xA0 (flags == 0, nothing is checked).
    header[0x40:0x60] = hashlib.sha256(b"oot-master-mod\0" + text).digest()
    out = bytearray(header)
    out += text
    out += b"\0" * (ro_off - len(out))
    out += ro
    out += b"\0" * (data_off - len(out))
    out += data
    return bytes(out)


def encode_bl(pc: int, target: int) -> int:
    delta = target - pc
    if delta % 4:
        raise ValueError("unaligned branch")
    imm = delta >> 2
    if not -(1 << 25) <= imm < (1 << 25):
        raise ValueError("branch out of range")
    return 0x94000000 | (imm & 0x03FFFFFF)


def decode_bl(word: int, pc: int) -> int | None:
    if (word & 0xFC000000) != 0x94000000:
        return None
    imm = word & 0x03FFFFFF
    if imm & 0x02000000:
        imm -= 0x04000000
    return pc + (imm << 2)


def verify_stock_sites() -> None:
    """Check that each site in main is `bl <stock reader>` before patching.

    The stock main is compressed (ZBIC/LZ4); tools/lib/nso.py decompresses the
    text segment in memory only. Nothing is written back.
    """
    from lib import nso  # tools/lib/nso.py

    raw = STOCK_MAIN.read_bytes()
    text = nso.text_bytes(raw)
    if COMPAT:
        w = struct.unpack_from("<I", text, COMPAT_STUB[0])[0]
        if w != COMPAT_STUB[2]:
            raise SystemExit(f"stub {COMPAT_STUB[0]:#x} is {w:#x}, expected adrp x16")
    for site, name, stock in active_sites()[0] + active_sites()[1]:
        word = struct.unpack_from("<I", text, site)[0]
        target = decode_bl(word, site)
        if target != stock:
            raise SystemExit(
                f"site {site:#x} ({name}) is not bl {stock:#x} (found {target:#x})"
            )
    for site, name, _id in CODE_SITES:
        word = struct.unpack_from("<I", text, site)[0]
        if word != PACIBSP:
            raise SystemExit(f"code site {site:#x} ({name}) is {word:#x}, expected pacibsp")
    print(f"verified {len(INPUT_SITES)} input sites and {len(SLOT_SITES)} slot sites")


def write_handler_table(features: list[str], path: Path) -> None:
    input_syms: list[str] = []
    slot_syms: list[str] = []
    for feat in features:
        input_syms += FEATURE_INPUT_HANDLERS.get(feat, [])
        slot_syms += FEATURE_SLOT_HANDLERS.get(feat, [])
    # Direct calls, not a table of function pointers: the NSO has no relocations,
    # so pointers in data would hold link addresses (see core/dispatch.h).
    lines = ['#include "dispatch.h"', ""]
    for sym in input_syms + slot_syms:
        lines.append(f"extern void {sym}(u32, void *, void *, void *, u32);")
    lines.append("")
    lines.append("void mod_on_input(u32 site, void *a0, void *a1, void *a2, u32 stock_result) {")
    for sym in input_syms:
        lines.append(f"    {sym}(site, a0, a1, a2, stock_result);")
    lines.append("    (void)site; (void)a0; (void)a1; (void)a2; (void)stock_result;")
    lines.append("}")
    lines.append("")
    pre = [s for feat in features for s in FEATURE_SLOT_PRE.get(feat, [])]
    for sym in pre:
        lines.append(f"extern u64 {sym}(u32, void *, void *, u64);")
    lines.append("u64 mod_pre_slot(u32 site, void *a0, void *a1, u64 a2) {")
    for sym in pre:
        lines.append(f"    a2 = {sym}(site, a0, a1, a2);")
    lines.append("    return a2;")
    lines.append("}")
    lines.append("")
    lines.append("extern void hud_on_code(u32, void *, void *, void *, void *);")
    lines.append("void mod_on_code(u32 id, void *a0, void *a1, void *a2, void *regs) {")
    lines.append("    hud_on_code(id, a0, a1, a2, regs);")
    lines.append("}")
    lines.append("")
    lines.append("void mod_on_slot(u32 site, void *a0, void *a1, void *a2, u32 stock_result) {")
    for sym in slot_syms:
        lines.append(f"    {sym}(site, a0, a1, a2, stock_result);")
    lines.append("    (void)site; (void)a0; (void)a1; (void)a2; (void)stock_result;")
    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


COMPAT = False   # --compat: coexist with Classic Item Slots (its IPS owns the input/slot sites)
# PLT stub of the input reader used during gameplay: first instruction `adrp x16, GOT3`.
COMPAT_STUB = (0x3C42800, "hook_stub3", 0xB00083F0)


def active_sites():
    if COMPAT:
        return [], []
    return list(INPUT_SITES), list(SLOT_SITES)


def make_ips(symbols: dict[str, int]) -> bytes:
    out = bytearray(b"IPS32")
    if COMPAT:
        site, name, _w = COMPAT_STUB
        delta = symbols[name] - site
        out += struct.pack(">I", site + 0x100) + struct.pack(">H", 4)
        out += struct.pack("<I", 0x14000000 | ((delta >> 2) & 0x03FFFFFF))
    for site, name, _stock in (list(INPUT_SITES) + list(SLOT_SITES)) if not COMPAT else []:
        if site in DISABLED_SITES:
            continue  # stays the stock bl (see hook_sites.DISABLED_SITES)
        target = symbols[name]
        word = encode_bl(site, target)
        out += struct.pack(">I", site + 0x100)   # +0x100: NSO text starts at file 0x100
        out += struct.pack(">H", 4)
        out += struct.pack("<I", word)
    for site, name, _id in CODE_SITES:
        delta = symbols[name] - site
        word = 0x14000000 | ((delta >> 2) & 0x03FFFFFF)   # b <wrapper>
        out += struct.pack(">I", site + 0x100)
        out += struct.pack(">H", 4)
        out += struct.pack("<I", word)
    out += b"EEOF"
    return bytes(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", default="probe",
                    help="comma-separated feature dirs under features/")
    ap.add_argument("--compat", action="store_true",
                    help="coexist with Classic Item Slots (module placed after it, PLT-stub input hook)")
    ap.add_argument("--base", default="0x4F88000", help="module base used with --compat")
    args = ap.parse_args()
    global COMPAT, BASE, LINK_SCRIPT
    if args.compat:
        COMPAT = True
        BASE = int(args.base, 0)
        OUT.mkdir(parents=True, exist_ok=True)
        ls = (CORE_SRC / "link.ld").read_text().replace("__base = 0x4F80000;", f"__base = {BASE:#x};")
        LINK_SCRIPT = OUT / "link_compat.ld"
        LINK_SCRIPT.write_text(ls)
    features = [f for f in args.features.split(",") if f]
    for f in features:
        if not (FEATURES_SRC / f).is_dir():
            raise SystemExit(f"unknown feature: {f}")

    verify_stock_sites()

    OUT.mkdir(parents=True, exist_ok=True)
    # Hashes of our HUD part names (the engine stores a CityHash64 next to each name).
    from lib.cityhash import city_hash64
    names = [f"Pa_OotSeg_{k:03d}" for k in range(128)]
    (OUT / "hud_names.h").write_text(
        "".join(f"#define HASH_PART{i} {city_hash64(n.encode())}ull\n" for i, n in enumerate(names))
        + "".join(f"#define HASH_TXT{i} {city_hash64(n.encode())}ull\n"
                  for i, n in enumerate(("T_OotClk_00", "T_OotRup_00", "T_OotClk_01", "T_OotRup_01")))
        + f"#define HASH_NUM {city_hash64(b'Pa_OotNum_00')}ull\n"
        + "".join(f"#define HASH_PIC{i} {city_hash64(n.encode())}ull\n"
                  for i, n in enumerate(("P_OotBg_00", "P_OotBg_01", "P_OotIc_00", "P_OotIc_01"))),
        encoding="ascii")
    gen = OUT / "dispatch_gen.c"
    write_handler_table(features, gen)

    sources = sorted(CORE_SRC.glob("*.S")) + sorted(CORE_SRC.glob("*.c"))
    for f in features:
        sources += sorted((FEATURES_SRC / f).glob("*.c"))
    objs: list[str] = []
    for src in sources + [gen]:
        obj = OUT / (src.stem + ".o")
        extra = ["-DCLASSIC_PROBE"] if os.environ.get("CLASSIC_PROBE") else []
        run([str(CLANG), *CFLAGS, *extra, "-I", str(OUT), "-I", str(CORE_SRC),
             "-c", str(src), "-o", str(obj)])
        objs.append(str(obj))

    elf = OUT / "module.elf"
    run([str(LLD), "-T", str(LINK_SCRIPT), "-o", str(elf), *objs])

    sec = section_info(elf)
    _, text_addr = sec[".text"]
    if text_addr != BASE:
        raise SystemExit(f"unexpected .text address {text_addr:#x}")

    text = dump_section(elf, ".text", OUT / "text.bin")
    text += b"\0" * ((0x1000 - len(text) % 0x1000) % 0x1000)
    ro = dump_section(elf, ".rodata", OUT / "rodata.bin") if ".rodata" in sec else b""
    data = dump_section(elf, ".data", OUT / "data.bin") if ".data" in sec else b""
    data += b"\0" * ((0x1000 - len(data) % 0x1000) % 0x1000)
    ro_rel = sec[".rodata"][1] - BASE if ".rodata" in sec else 0
    data_rel = sec[".data"][1] - BASE if ".data" in sec else sec[".bss"][1] - BASE
    bss_size = sec[".bss"][0] if ".bss" in sec else 0

    syms = symbol_table(elf)
    for _, name, _ in active_sites()[0] + active_sites()[1]:
        if name not in syms:
            raise SystemExit(f"missing wrapper symbol {name}")

    exefs = OUT / "exefs"
    exefs.mkdir(exist_ok=True)
    (exefs / "subsdk9").write_bytes(build_nso(text, ro, data, ro_rel, data_rel, bss_size))
    (exefs / f"{MAIN_BUILD_ID}.ips").write_bytes(make_ips(syms))
    print(f"features={features} text={len(text):#x} ro={len(ro):#x} "
          f"data={len(data):#x} bss={bss_size:#x}")
    print(f"wrote {exefs / 'subsdk9'}")
    print(f"wrote {exefs / (MAIN_BUILD_ID + '.ips')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

