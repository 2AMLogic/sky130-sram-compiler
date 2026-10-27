#!/usr/bin/env bash
# LVS of the analog macro GDS against its item-1 netlist, plus a negative control on the full macro.
# Usage: design/macro/lvs/run_lvs.sh [--report PATH] [<layout.gds> <outdir> [<reference.spice> <top>]]
#   defaults: layout/sram_256x32_m4.gds, outdir required, design/compiler/macro/sram_256x32_m4.spice,
#   top sram_256x32_m4. Run from anywhere; klt runs from the repo root so the report's layout and
#   reference paths are repo-relative and `klt lvs --check` can re-hash them. outdir: scratch, outside
#   the repo. --report PATH copies the positive-compare report (the item-4 evidence) to PATH.
#
# Reference = the item-1 macro netlist as committed, with its real VDD/VSS pins: no `vsubs`
# workaround (compare design/bitcell/lvs/run_lvs.sh). The macro carries the p-substrate straps the
# bare bitcell lacks, so every nfet bulk is compared against a drawn tie and `body_verification`
# must read `verified`. Options `combine_devices`, `flatten_layout`, `flatten_reference`: the layout
# is extracted flat, the reference is the hierarchical sram_compile.py output (the same options the
# layout/records/20261027-ca10c045.md checks used).
# Negative control: the same compare with ONE bitcell instance (the last one, bottom-right corner of
# the array) wired to row 0's wordline WL0 instead of its own, in the reference (a BL/BLB swap would
# not do: the 6T cell is symmetric under it). It must report `mismatch`; it is the full macro, not the bitcell.
# Exit: 0 positive `match`, power_connectivity not `mismatch`, body verified, control `mismatch`;
#       3 positive compare is not `match`; 4 power or body verdict fails; 5 the control matched.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
report=""
if [ "${1:-}" = "--report" ]; then report=$2; shift 2; fi
G=${1:-layout/sram_256x32_m4.gds}; O=${2:?outdir}
REF=${3:-design/compiler/macro/sram_256x32_m4.spice}; TOP=${4:-sram_256x32_m4}
command -v klt >/dev/null || { echo "run_lvs.sh: TOOL_MISSING: klt not on PATH" >&2; exit 1; }
cd "$repo"
mkdir -p "$O"
O=$(realpath "$O")
python3 -I - "$REF" "$O" <<'PY'
import re, sys
src, out = sys.argv[1], sys.argv[2]
lines = open(src).read().splitlines()
bad, done = [], False
for ln in reversed(lines):
    m = re.match(r"^(XC\d+_\d+) (BL\d+) (BLB\d+) (WL\d+) (\S+) (\S+) bitcell_6t$", ln)
    if m and not done:
        ln = f"{m.group(1)} {m.group(2)} {m.group(3)} WL0 {m.group(5)} {m.group(6)} bitcell_6t"
        done = True
    bad.append(ln)
if not done:
    sys.exit("run_lvs.sh: no bitcell instance found to perturb")
open(f"{out}/ref_bad.spice", "w").write("\n".join(reversed(bad)) + "\n")
PY
req() { # $1 = reference netlist path
  cat <<JSON
{
  "layout": { "file": "$G", "deck": "sky130", "top": "$TOP" },
  "reference": { "netlist": "$1", "top": "$TOP", "form": "subckt-call", "deck": "sky130" },
  "options": { "combine_devices": true, "flatten_layout": true, "flatten_reference": true }
}
JSON
}
req "$REF" | klt lvs - --format json > "$O/ref.lvs.json" 2> "$O/ref.err" || true
req "$O/ref_bad.spice" | klt lvs - --format json > "$O/ref_bad.lvs.json" 2> "$O/ref_bad.err" || true
[ -z "$report" ] || cp "$O/ref.lvs.json" "$report"
python3 -I - "$O" <<'PY'
import json, sys
o = sys.argv[1]
res = {}
for k, want in (("ref", "match"), ("ref_bad", "mismatch")):
    try:
        d = json.load(open(f"{o}/{k}.lvs.json"))
    except Exception as e:  # klt wrote no report: show why
        print(f"{k:8s} NO REPORT ({e}); see {o}/{k}.err")
        res[k] = None
        continue
    c = d.get("counts", {})
    print(f"{k:8s} engine={d.get('engine')} status={d.get('status')} (expected {want})",
          {n: (c[n]["layout"], c[n]["reference"], c[n]["matched"]) for n in c},
          dict(d.get("category_counts", {})))
    pc, bv = d.get("power_connectivity", {}), d.get("body_verification", {})
    print(f"{'':8s} power_connectivity={pc.get('status')} body_verification={bv.get('status')}")
    res[k] = d
ref, bad = res.get("ref"), res.get("ref_bad")
if ref is None or ref.get("status") != "match":
    sys.exit(3)
if ref["power_connectivity"]["status"] == "mismatch" or ref["body_verification"]["status"] != "verified":
    sys.exit(4)
if bad is None or bad.get("status") != "mismatch":
    sys.exit(5)
PY
