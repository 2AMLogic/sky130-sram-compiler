#!/usr/bin/env bash
# LVS of the bitcell GDS against the schematic netlist, plus a negative control.
# Usage: design/bitcell/lvs/run_lvs.sh <layout.gds> <outdir>     (outdir: scratch, outside the repo)
#
# Reference = design/bitcell/netlist/bitcell_6t.spice with the nfet bulk moved from VSS to a
# separate `vsubs` pin: the cell has no p-substrate tap (the array supplies it), so the layout's
# nfet bulk is the extracted substrate, not VSS. klt reports this as device.body_unverified.
# Negative control: the same compare with MAL's drawn width (ax.w in design/bitcell/sizing.json)
# increased by 0.1 um must NOT match. The width is read from sizing.json, never hardcoded, and the
# script exits non-zero if the XMAL line does not carry it — a resize that leaves the committed
# netlist stale cannot silently turn the control into a compare of a correct netlist.
# Exit: 0 ref `match` and ref_bad `mismatch`; 1 anchor error — the XMAL line does not carry
#       the sizing width or the perturbed width is not numeric (lvs/make_ref.py);
#       3 ref is not `match` (or wrote no report);
#       5 ref_bad is not `mismatch` (or wrote no report). 4 is unused: power_connectivity /
#       body_verification have no bitcell gating analogue (device.body_unverified is expected),
#       and the number is kept free so the three LVS runners share one convention
#       (design/macro/lvs/run_lvs.sh, design/control/lvs/run_lvs.sh).
set -euo pipefail
G=$(realpath "${1:?layout.gds}"); O=${2:?outdir}
command -v klt >/dev/null || { echo "run_lvs.sh: TOOL_MISSING: klt not on PATH" >&2; exit 1; }
mkdir -p "$O"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -I "$here/make_ref.py" "$here/../sizing.json" "$here/../netlist/bitcell_6t.spice" "$O"
for k in ref ref_bad; do
  cat > "$O/$k.request.json" <<JSON
{
  "layout": { "file": "$G", "deck": "sky130", "top": "sky130_sram_bitcell_6t" },
  "reference": { "netlist": "$k.spice", "top": "bitcell_6t", "form": "subckt-call", "deck": "sky130" }
}
JSON
  klt lvs "$O/$k.request.json" --format json > "$O/$k.lvs.json" 2>"$O/$k.err" || true
done
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
    print(f"{k:8s} status={d.get('status')} (expected {want})",
          {n: (c[n]["layout"], c[n]["reference"], c[n]["matched"]) for n in c},
          dict(d.get("category_counts", {})))
    res[k] = d
ref, bad = res.get("ref"), res.get("ref_bad")
if ref is None or ref.get("status") != "match":
    sys.exit(3)
if bad is None or bad.get("status") != "mismatch":
    sys.exit(5)
PY
