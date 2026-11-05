#!/usr/bin/env bash
# klt erc supply evidence (T1 item 11): macro, severed-rail negative controls, control block.
# Usage: layout/erc/run_erc.sh [--write] <outdir>
#   outdir: scratch, outside the repo (holds the severed GDS copies). --write also commits the
#   reports next to this script (erc_macro.json, erc_control.json, erc_macro_severed_*.json).
# Specs are generated: design/compiler/gen_erc_spec.py (uv run --no-project --with klayout python -I ...).
# klt runs from the repo root so report paths are repo-relative. Pin: klayout-tools==0.9.0.
# Negative controls cut the committed macro GDS in a copy: (a) both VSS m1/li columns of one bitcell row, (b) both VDD m2 columns of that row
# (cutting one of the two columns is bridged by the cell and reads clean: the rails are a mesh). Each must yield a blocking finding.
# Exit: 0 all as expected; 3 macro/control not clean; 4 a control produced no blocking finding.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
write=0; [ "${1:-}" = "--write" ] && { write=1; shift; }
O=${1:?outdir}; mkdir -p "$O"; O=$(realpath "$O")
cd "$repo"
KLT=(uvx --from "klayout-tools==0.9.0" klt)
GDS=layout/sram_256x32_m4.gds
uv run --no-project --with klayout python -I design/compiler/gen_erc_spec.py macro 256 32 4 --check layout/erc/erc_macro_spec.json
uv run --no-project --with klayout python -I design/compiler/gen_erc_spec.py control --check layout/erc/erc_control_spec.json
uv run --no-project --with klayout python -I - "$GDS" "$O" <<'PY'
import sys, klayout.db as db
src, out = sys.argv[1:]
x = 5.18 * 64                      # column 64 of the array; y 50.0..51.8 spans one full bitcell row
for tag, layers, box in (("vss", [(68, 20), (67, 20)], (x + 0.6, 50.0, x + 4.6, 51.8)),      # both VSS m1/li columns
                         ("vdd", [(69, 20)], (x + 1.5, 50.0, x + 3.7, 51.8))):               # both VDD m2 columns
    ly = db.Layout(); ly.read(src); top = ly.top_cell()
    top.flatten(True)              # the cell instances carry their own rail pads; cut the flat geometry
    cut = db.Region(db.Box(*[round(v * 1000) for v in box]))
    for l in layers:
        li = ly.layer(*l)
        r = db.Region(top.shapes(li)) - cut
        top.shapes(li).clear(); top.shapes(li).insert(r)
    ly.write(f"{out}/severed_{tag}.gds")
PY
run() { # $1 gds $2 spec $3 report
  "${KLT[@]}" erc "$1" "$2" --findings-only --omit-antenna-tables --format json > "$3" 2> "$3.err" || true
}
run "$GDS" layout/erc/erc_macro_spec.json "$O/erc_macro.json"
run layout/control/control.gds layout/erc/erc_control_spec.json "$O/erc_control.json"
run "$O/severed_vss.gds" layout/erc/erc_macro_spec.json "$O/erc_macro_severed_vss.json"
run "$O/severed_vdd.gds" layout/erc/erc_macro_spec.json "$O/erc_macro_severed_vdd.json"
[ "$write" = 0 ] || cp "$O"/erc_macro.json "$O"/erc_control.json "$O"/erc_macro_severed_vss.json "$O"/erc_macro_severed_vdd.json layout/erc/
python3 -I - "$O" <<'PY'
import json, sys
o = sys.argv[1]
def load(k): return json.load(open(f"{o}/{k}.json"))
rc = 0
for k, want_clean in (("erc_macro", True), ("erc_control", True), ("erc_macro_severed_vss", False), ("erc_macro_severed_vdd", False)):
    d = load(k)
    fs = sorted({f["rule"] for f in d["erc_findings"]})
    print(f"{k:24s} erc_status={d['erc_status']} findings={fs} missing_tie_checked={d['erc_coverage']['missing_tie_checked']} skipped={d['erc_coverage']['skipped']}")
    if want_clean and (d["erc_status"] != "clean" or fs):
        rc = max(rc, 3)
    if not want_clean and not fs:
        rc = max(rc, 4)
sys.exit(rc)
PY
