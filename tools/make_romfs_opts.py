"""Developer step: build the small romfs files of the optional features from the user's own game dump (not from other
mods). Output: app/payload/romfs_opts/<option>/<romfs path>.

no_heart_drop: DropGlobalParam.HpActor (the actor dropped as "a heart") is pointed at the green rupee instead.

The file is game data, so it is generated from the developer's own dump and is not part of the repository. The app
installs it when present; otherwise it installs the rest and shows a note.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEVTOOL = Path(os.environ.get("SHB_DEVTOOL", r"F:\project\oot\vendor\devtool\oot-remake-devtool-main"))
ROMFS = Path(os.environ.get("SHB_ROMFS", r"F:\switch2\Longshot\romfs"))
OUT = ROOT / "app" / "payload" / "romfs_opts"
DROP = "GameParameter/DropGlobalParam/Default.game__drop__DropGlobalParam.bgyml"
RUPEE = "Work/Actor/Obj_Rupee_Green.engine__actor__ActorParam.gyml"


def no_heart_drop():
    """Same size as vanilla: only the string index of HpActor changes (the rupee path is already in the string table)."""
    sys.path.insert(0, str(DEVTOOL))
    try:
        import byml  # noqa: E402
    except ImportError:
        print("romfs options: byml reader not found (set SHB_DEVTOOL); keeping the existing payload file")
        return
    src = ROMFS / DROP
    if not src.exists():
        print("romfs options: game dump not found (set SHB_ROMFS); keeping the existing payload file")
        return
    import struct
    raw = bytearray(src.read_bytes())
    b = byml.Byml(bytes(raw))
    slot = [o for p, t, v, o in b.flat() if p == "DropLotteryMasterData/HpActor"][0]
    assert b.strs[b._u("I", slot)[0]].endswith("Obj_Heart.engine__actor__ActorParam.gyml")
    struct.pack_into(b.e + "I", raw, slot, b.strs.index(RUPEE))
    chk = {p: v for p, t, v, o in byml.Byml(bytes(raw)).flat()}
    ref = {p: v for p, t, v, o in b.flat()}
    assert [k for k in set(chk) | set(ref) if chk.get(k) != ref.get(k)] == ["DropLotteryMasterData/HpActor"]
    dst = OUT / "no_heart_drop" / DROP
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(bytes(raw))
    print("wrote", dst, len(raw))


if __name__ == "__main__":
    no_heart_drop()
