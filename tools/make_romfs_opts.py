"""Developer step: build the small romfs files of the optional features from the user's own game dump (not from other
mods). Output: app/payload/romfs_opts/<option>/<romfs path>.

no_heart_drop: DropGlobalParam.HpActor (the actor dropped as "a heart") is pointed at the green rupee instead.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, r"F:\project\oot\vendor\devtool\oot-remake-devtool-main")
import byml  # noqa: E402

ROMFS = Path(r"F:\switch2\hookshott\romfs")
OUT = ROOT / "app" / "payload" / "romfs_opts"
DROP = "GameParameter/DropGlobalParam/Default.game__drop__DropGlobalParam.bgyml"
RUPEE = "Work/Actor/Obj_Rupee_Green.engine__actor__ActorParam.gyml"


def no_heart_drop():
    """Same size as vanilla: only the string index of HpActor changes (the rupee path is already in the string table)."""
    import struct
    raw = bytearray((ROMFS / DROP).read_bytes())
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
