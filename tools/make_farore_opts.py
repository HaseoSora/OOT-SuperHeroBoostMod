"""Build the Farore's Wind outdoor beta (romfs option) from the user's own game dump.

WarpEvent.bfevfl decides whether a warp point can be placed.  Its
`EventQueryIsForbidSetWarpPoint` switch has three outcomes:

  0 -> DisableSetWarpPoint          (a ForbidSetWarpPointArea covers this spot)
  1 -> DisableSetWarpPointDungeon   ("you cannot place it outside a dungeon")
  2 -> set the warp point

This patch points outcome 1 at the same event as outcome 2, so placing a point
outside a dungeon is allowed.  Outcome 0 (real forbidden areas, e.g. inside
FireTemple) stays blocked.  The file size does not change, so the resource size
table does not need to be touched.

Output: app/payload/romfs_opts/farore_outdoor/Event/EventFlow/WarpEvent.bfevfl.zs
"""
import io
import os
import sys
import zstandard
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROMFS = Path(os.environ.get("SHB_ROMFS", r"F:\switch2\Longshot\romfs"))
OUT = ROOT / "app" / "payload" / "romfs_opts"
FLOW = "Event/EventFlow/WarpEvent.bfevfl"
SET_POINT_ENTRY = "FaroreWind_SetWarpPoint"
DUNGEON_CASE = 1

sys.path.insert(0, str(ROOT / "tools"))
from lib import sarc  # noqa: E402

import evfl  # noqa: E402


def load_dict(name):
    raw = (ROMFS / "Pack" / "ZsDic.pack.zs").read_bytes()
    data = zstandard.ZstdDecompressor().decompress(raw, max_output_size=20_000_000)
    files = sarc.read_sarc(data)
    for path, (s, e) in files.items():
        if Path(path).name == name:
            return data[s:e]
    raise FileNotFoundError(name)


def main():
    data = (ROMFS / (FLOW + ".zs")).read_bytes()
    zs_dict = load_dict("zs.zsdic")
    dictionary = zstandard.ZstdCompressionDict(zs_dict)
    plain = zstandard.ZstdDecompressor(dict_data=dictionary).decompress(
        data, max_output_size=20_000_000)
    flow = evfl.EventFlow()
    flow.read(plain)
    fc = flow.flowchart

    entry = next(e for e in fc.entry_points if e.name == SET_POINT_ENTRY)
    switch_idx = entry.main_event._idx
    switch = fc.events[switch_idx].data
    if not isinstance(switch, evfl.SwitchEvent):
        raise RuntimeError(f"{SET_POINT_ENTRY} does not start with a switch")
    if not (switch.actor_query and switch.actor_query.v.v == "EventQueryIsForbidSetWarpPoint"):
        raise RuntimeError("unexpected set-point query")
    def target(k):
        return fc.events[switch.cases[k]._idx].data

    if not (isinstance(target(0), evfl.SubFlowEvent) and target(0).entry_point_name == "DisableSetWarpPoint"):
        raise RuntimeError("case 0 is not DisableSetWarpPoint")
    if not (isinstance(target(1), evfl.SubFlowEvent) and target(1).entry_point_name == "DisableSetWarpPointDungeon"):
        raise RuntimeError("case 1 is not DisableSetWarpPointDungeon")
    if isinstance(target(2), evfl.SubFlowEvent) and target(2).entry_point_name.startswith("Disable"):
        raise RuntimeError("case 2 is not the allowed branch")

    for case in (0, 1):
        old = switch.cases[case]._idx
        switch.cases[case] = switch.cases[2]
        print(f"switch {switch_idx}: case {case} {old} -> {switch.cases[2]._idx}")

    # The item-use gate asks EventQueryCanUseFaroreWind first. 1 is "cannot use it here"
    # (DisableWarp); point it at the normal "can use" branch (0) instead.
    for i, ev in enumerate(fc.events):
        d = ev.data
        if isinstance(d, evfl.SwitchEvent) and getattr(d.actor_query, "v", None) and \
           getattr(d.actor_query.v, "v", None) == "EventQueryCanUseFaroreWind":
            old = d.cases[1]._idx
            d.cases[1] = d.cases[0]
            print(f"switch {i}: canUse case 1 {old} -> {d.cases[0]._idx}")

    # The talk the flow opens before placing the point never takes input when the item is used
    # outside a dungeon (the message window is drawn but its choices are dead: no cursor, no A).
    # Skip it: the switch that leads to it goes straight to its "place here" branch.
    def qn(d):
        try:
            v = d.actor_query.v
            return getattr(v, "v", v)
        except Exception:
            return None

    def act(d):
        try:
            return d.actor_action.v.v
        except Exception:
            return None

    accept = None
    for i, ev in enumerate(fc.events):
        d = ev.data
        if isinstance(d, evfl.SwitchEvent) and qn(d) == "EventQueryTalkChoice2" and len(d.cases) == 2:
            t = fc.events[d.cases[0]._idx].data
            if isinstance(t, evfl.SwitchEvent) and qn(t) == "EventQueryCameraCheckOcclusionToTarget":
                accept = d.cases[0]._idx
    if accept is None:
        raise RuntimeError("place-here branch not found")
    print("place-here branch:", accept)

    for i, ev in enumerate(fc.events):
        d = ev.data
        if isinstance(d, evfl.SwitchEvent) and qn(d) == "EventQueryIsGameDataBool" and \
           d.params and str(d.params.data.get("GameDataName", "")).startswith("WarpPoint_FaoreWind"):
            for k in list(d.cases):
                t = fc.events[d.cases[k]._idx].data
                if isinstance(t, evfl.ActionEvent) and act(t) == "EventTalk":
                    old = d.cases[k]._idx
                    d.cases[k] = evfl.util.make_rindex(fc.events[accept])
                    print(f"switch {i}: skip talk case {k} {old} -> {accept}")

    buf = io.BytesIO()
    if not flow.write(buf):
        raise RuntimeError("evfl write failed")
    out = buf.getvalue()
    if len(out) != len(plain):
        raise RuntimeError(f"flow size changed: {len(plain)} -> {len(out)}")

    dst = OUT / "farore_outdoor" / (FLOW + ".zs")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(zstandard.ZstdCompressor(dict_data=dictionary).compress(out))
    print("wrote", dst)


if __name__ == "__main__":
    main()
