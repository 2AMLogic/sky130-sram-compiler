"""Layout probes for the T1 item 3 (DRC) run. Run with klt's python (it bundles klayout).

  probe.py scan GDS                  JSON: shapes per layer/datatype on layer 81 (areaid.*) over every cell
  probe.py neg-probe OUT             known-bad fixture: a 0.05 um wide met1 bar (curated deck must flag met1.width.1)
  probe.py marker-probe OUT          positive control for `scan`: one areaid.ce (81/2) box
  probe.py seam-probe SRC OUT        SRC plus two 0.05 um met1 slivers straddling the array/precharge and
                                     array/column-mux seams (curated deck must flag met1.width.1 at both)
"""
import json
import sys

import klayout.db as db

MET1 = (68, 20)
AREAID_CE = (81, 2)
# array top 114.17 / precharge bottom 115.04; colmux top 0.0 / array bottom 0.8 (um), from the top-cell instances
SEAMS = {"array/precharge": (100.0, 114.1, 100.05, 115.1), "colmux/array": (100.0, -0.5, 100.05, 0.9)}


def write(layout, path):
    opt = db.SaveLayoutOptions()
    opt.format = "GDS2"
    opt.gds2_write_timestamps = False
    layout.write(path, opt)


def scan(path):
    ly = db.Layout()
    ly.read(path)
    counts = {}
    for li in ly.layer_indexes():
        info = ly.get_info(li)
        if info.layer != 81:
            continue
        counts[f"{info.layer}/{info.datatype}"] = sum(c.shapes(li).size() for c in ly.each_cell())
    return {"file": path, "cells": ly.cells(), "layer_81_shapes": counts,
            "areaid_ce_shapes": counts.get("81/2", 0)}


def main(argv):
    cmd = argv[0]
    if cmd == "scan":
        print(json.dumps(scan(argv[1]), indent=2))
    elif cmd in ("neg-probe", "marker-probe"):
        ly = db.Layout()
        ly.dbu = 0.001
        top = ly.create_cell(cmd.replace("-", "_"))
        if cmd == "neg-probe":
            top.shapes(ly.layer(*MET1)).insert(db.DBox(0, 0, 0.05, 1.0))
        else:
            top.shapes(ly.layer(*AREAID_CE)).insert(db.DBox(0, 0, 1.0, 1.0))
        write(ly, argv[1])
    elif cmd == "seam-probe":
        ly = db.Layout()
        ly.read(argv[1])
        li = ly.layer(*MET1)
        for box in SEAMS.values():
            ly.top_cell().shapes(li).insert(db.DBox(*box))
        write(ly, argv[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
