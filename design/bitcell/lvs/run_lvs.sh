#!/usr/bin/env bash
# LVS of the bitcell GDS against the schematic netlist, plus a negative control.
# Usage: design/bitcell/lvs/run_lvs.sh <layout.gds> <outdir>     (outdir: scratch, outside the repo)
#
# Reference = design/bitcell/netlist/bitcell_6t.spice with the nfet bulk moved from VSS to a
# separate `vsubs` pin: the cell has no p-substrate tap (the array supplies it), so the layout's
# nfet bulk is the extracted substrate, not VSS. klt reports this as device.body_unverified.
# Negative control: the same compare with MAL's W changed 0.42 -> 0.52 must NOT match.
set -euo pipefail
G=$(realpath "${1:?layout.gds}"); O=${2:?outdir}; mkdir -p "$O"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -I - "$here/../netlist/bitcell_6t.spice" "$O" <<'PY'
import re, sys
src, out = sys.argv[1], sys.argv[2]
good, bad = [], []
for ln in open(src).read().splitlines():
    if ln.startswith(".subckt"):
        ln += " vsubs"
    m = re.match(r"^(X\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(sky130_fd_pr__nfet_01v8)(.*)$", ln)
    if m:
        ln = f"{m.group(1)} {m.group(2)} {m.group(3)} {m.group(4)} vsubs {m.group(6)}{m.group(7)}"
    good.append(ln)
    bad.append(ln.replace("XMAL BL WL Q vsubs sky130_fd_pr__nfet_01v8 L=0.15 W=0.42",
                          "XMAL BL WL Q vsubs sky130_fd_pr__nfet_01v8 L=0.15 W=0.52") if ln.startswith("XMAL") else ln)
open(f"{out}/ref.spice", "w").write("\n".join(good) + "\n")
open(f"{out}/ref_bad.spice", "w").write("\n".join(bad) + "\n")
PY
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
for k, want in (("ref", "match"), ("ref_bad", "mismatch")):
    d = json.load(open(f"{sys.argv[1]}/{k}.lvs.json"))
    c = d.get("counts", {})
    print(f"{k:8s} status={d.get('status')} (expected {want})",
          {n: (c[n]["layout"], c[n]["reference"], c[n]["matched"]) for n in c},
          dict(d.get("category_counts", {})))
PY
