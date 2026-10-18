#!/usr/bin/env python3
"""Generate the layout, run DRC / LVS / area, and write an append-only record.

Usage: design/bitcell/make_record.py <scratch-dir>      (scratch: outside the repo)
Writes design/bitcell/records/<UTC timestamp>-<git sha>.md and never overwrites one.
Needs: uv (klayout python), klt, a sky130A install at the pin (source sim/env.sh first).
"""
import datetime
import json
import os
import pathlib
import subprocess
import sys

here = pathlib.Path(__file__).resolve().parent
repo = here.parents[1]
scratch = pathlib.Path(sys.argv[1])
scratch.mkdir(parents=True, exist_ok=True)
gds = scratch / "bitcell_6t.gds"


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=repo, **kw)


info = json.loads(run(["uv", "run", "--no-project", "--with", "klayout", "python", "-I",
                       str(here / "gen_bitcell.py"), str(gds)]).stdout)
drc = run([str(here / "run_drc.sh"), str(gds), str(scratch / "drc")]).stdout.strip().splitlines()
lvs = run([str(here / "lvs/run_lvs.sh"), str(gds), str(scratch / "lvs")]).stdout.strip().splitlines()
foundry = pathlib.Path(os.environ["SKY130_VARIANT_DIR"]) / "libs.ref/sky130_sram_macros/gds/sram_1rw1r_32_256_8_sky130.gds"
fcell = "sky130_fd_bd_sram__openram_dp_cell"


def bbox(path, top):
    t = run(["klt", "stats", str(path), "--top", top, "--format", "json"]).stdout
    return json.loads(t[t.index("{"):])["bbox_um"]


mine = bbox(gds, "sky130_sram_bitcell_6t")
theirs = bbox(foundry, fcell)
a_m, a_f = mine["width"] * mine["height"], theirs["width"] * theirs["height"]
sha = run(["git", "rev-parse", "--short", "HEAD"]).stdout.strip()
sz = json.loads((here / "sizing.json").read_text())
ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
rec = here / "records" / f"{ts}-{sha}.md"
rec.parent.mkdir(exist_ok=True)
assert not rec.exists()
klt_v = run(["klt", "--version"]).stdout.strip()
L = [f"# Bitcell layout record {ts} ({sha})", "",
     "Issue: 2AMLogic/sky130-sram-compiler#7 (part of #2). Append-only: add a new dated record, never edit this one.", "",
     f"- klt: {klt_v}; klayout python in `uv run --with klayout`",
     f"- PDK: sky130A open_pdks {os.environ.get('SKY130_PDK_VERSION', '?')} (pin: {os.environ.get('SKY130_PDK_PIN', '?')})",
     f"- sizing (design/bitcell/sizing.json): PD {sz['pd']['w']}/{sz['pd']['l']}, AX {sz['ax']['w']}/{sz['ax']['l']}, PU {sz['pu']['w']}/{sz['pu']['l']} um",
     f"- layout: `gen_bitcell.py`, cell `sky130_sram_bitcell_6t`, pitch box {info['width_um']} x {info['height_um']} um, no areaid.ce (81/2) marker", "",
     "## DRC (`design/bitcell/run_drc.sh`)", "", "```"] + drc + ["```", "",
     "`curated` is `klt drc --deck sky130` (marker-blind). `lydrc` is the PDK `sky130A.lydrc`; `mr` is the PDK `sky130A_mr.drc` with "
     "`--deck-var feol=true beol=true thr=1`, the only marker-aware deck; the cell carries no marker so it applies the strict (logic) rules "
     "everywhere. `coverage_unknown` is klt's label for any zero-finding klayout-engine run: no violation reported, not proven clean. "
     "That both klayout decks really ran is shown by the marker study's stripped-marker control "
     "(`verification/marker/records/2026-10-17-f22b400.md`) and by the 8-violation first draft of this very cell (li / met1 / nsdm spacing) that they reported before it was fixed.", "",
     "## LVS (`design/bitcell/lvs/run_lvs.sh`)", "", "```"] + lvs + ["```", "",
     "Reference is the schematic netlist with the nfet bulk on a separate `vsubs` pin: the cell has no p-substrate tap (the array supplies it), "
     "so `device.body_unverified` is expected and means the bulk was compared against the extracted substrate, not a drawn tie. "
     "The second line is a negative control (MAL width 0.42 -> 0.52 in the reference) and must not match.", "",
     "## Area (`klt stats --top <cell> --format json`, bbox width x height, same command for both cells)", "",
     "| cell | bbox (um) | area (um^2) |", "|---|---|---:|",
     f"| this 6T logic-rule cell | {mine['width']:.3f} x {mine['height']:.3f} | {a_m:.3f} |",
     f"| foundry `{fcell}` (OpenRAM 1RW1R, from `sram_1rw1r_32_256_8_sky130.gds`) | {theirs['width']:.3f} x {theirs['height']:.3f} | {a_f:.3f} |", "",
     f"**Ratio this / foundry = {a_m / a_f:.3f}** (this cell is {100 * (1 - a_m / a_f):.0f} % smaller by bounding box).", "",
     "Not like-for-like: the foundry cell is the dual-port (1RW1R) cell, the only foundry bitcell in this PDK (see the marker record), "
     "against a single-port 6T here; the foundry cell is drawn to relaxed rules legal only inside the core marker. "
     "This cell also does not share contacts with mirrored neighbours and was not tiled, so its pitch is an upper bound for a drawn 6T "
     "and not a claim about an abutted array.", ""]
rec.write_text("\n".join(L))
print("wrote", rec)
