#!/usr/bin/env bash
# Gate-level LVS of the routed control block layout/control/control.gds, plus a negative control.
# Usage: design/control/lvs/run_lvs.sh [--report PATH] <outdir>     (outdir: scratch, outside the repo)
#
# Runs `klt place-and-route` once from the repo root (about a minute; same request and flags as
# layout/control/run_pnr.sh, which proves the flow is deterministic) to obtain the post-route
# gate-level netlist, requires the GDS it produced to be byte-identical to the committed
# layout/control/control.gds, then runs `klt lvs` with reference.form gate-level-verilog (the only
# form for which power_connectivity runs), standard cells abstracted as pin-only black boxes
# (layout.abstract_cells + the PDK LEF):
#   post  layout vs the post-route netlist (the evidence report, --report PATH)
#   synth layout vs the item-1 synthesized netlist rtl/synth/sram_ctrl_256x32_synth.v. Reported, not
#         gating: P&R resizes and re-buffers after synthesis (see the record), so this is expected
#         NOT to match; the cell census difference is printed.
#   neg   post-route netlist with one NAND2 input rewired (.B(ce) -> .B(we)); must report mismatch
#   flat  `klt extract` of the same GDS, transistor level: bulk net of every nfet / pfet. Classifies
#         a power_connectivity VNB finding as an abstraction artifact or a real substrate break.
# Exit: 0 post `match`, power_connectivity not `mismatch`, control `mismatch`;
#       3 post is not `match`; 4 power_connectivity `mismatch` (item 4 not satisfied); 5 control matched;
#       6 the P&R GDS differs from the committed one.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
report=""
if [ "${1:-}" = "--report" ]; then report=$2; shift 2; fi
O=${1:?outdir}
cd "$repo"
for t in klt openroad python3; do
  command -v "$t" >/dev/null || { echo "run_lvs.sh: TOOL_MISSING: $t not on PATH" >&2; exit 1; }
done
# shellcheck source=../../../sim/env.sh
source sim/env.sh >/dev/null || { echo "run_lvs.sh: PDK environment refused (see env.sh error above)" >&2; exit 1; }
mkdir -p "$O"
O=$(realpath "$O")
LEF=$PDK_ROOT/$PDK/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
flow=layout/control/.klt/place-and-route
klt place-and-route layout/control/place-and-route.request.json --pdk "$PDK" --pdk-root "$PDK_ROOT" \
  --format json > "$O/pnr.json" 2> "$O/pnr.err"
cmp -s "$flow/sram_ctrl.gds" layout/control/control.gds || {
  echo "run_lvs.sh: P&R GDS differs from the committed layout/control/control.gds" >&2; exit 6; }
cp "$flow/sram_ctrl.v" "$O/routed.v"
python3 -I - "$O" <<'PY'
import re, sys, collections
o = sys.argv[1]
src = open(f"{o}/routed.v").read()
bad = src.replace("sky130_fd_sc_hd__nand2_1 _099_ (.A(ph[0]),\n    .B(ce),", "sky130_fd_sc_hd__nand2_1 _099_ (.A(ph[0]),\n    .B(we),", 1)
if bad == src:
    sys.exit("run_lvs.sh: negative-control anchor (nand2_1 _099_) not found in the routed netlist")
open(f"{o}/routed_bad.v", "w").write(bad)
def census(p):
    return collections.Counter(re.findall(r"^\s*(sky130_fd_sc_hd__\w+)\s+\S+\s*\(", open(p).read(), re.M))
s, r = census("rtl/synth/sram_ctrl_256x32_synth.v"), census(f"{o}/routed.v")
with open(f"{o}/census.txt", "w") as f:
    for k in sorted(set(s) | set(r)):
        if s[k] != r[k]:
            f.write(f"{k} synth={s[k]} routed={r[k]}\n")
    f.write(f"total synth={sum(s.values())} routed={sum(r.values())}\n")
PY
req() { # $1 = reference netlist, repo-relative or absolute
  cat <<JSON
{
  "layout": { "file": "layout/control/control.gds", "deck": "sky130", "top": "sram_ctrl",
              "abstract_cells": ["sky130_fd_sc_hd__*"], "abstract_cell_lef": ["$LEF"] },
  "reference": { "netlist": "$1", "top": "sram_ctrl", "form": "gate-level-verilog",
                 "library": "sky130_fd_sc_hd", "pdk": "$PDK", "pdk_root": "$PDK_ROOT", "deck": "sky130" }
}
JSON
}
# The evidence report cites the committed copy of the post-route netlist so `klt lvs --check` can re-hash it.
cmp -s "$O/routed.v" layout/control/sram_ctrl_routed.v || {
  echo "run_lvs.sh: layout/control/sram_ctrl_routed.v is stale or missing (copy $O/routed.v there)" >&2; exit 6; }
req layout/control/sram_ctrl_routed.v | klt lvs - --format json > "$O/post.lvs.json" 2> "$O/post.err" || true
req rtl/synth/sram_ctrl_256x32_synth.v | klt lvs - --format json > "$O/synth.lvs.json" 2> "$O/synth.err" || true
req "$O/routed_bad.v" | klt lvs - --format json > "$O/neg.lvs.json" 2> "$O/neg.err" || true
klt extract --deck sky130 --top sram_ctrl -o "$O/flat.spice" --format json layout/control/control.gds \
  > "$O/flat.json" 2> "$O/flat.err" || true
[ -z "$report" ] || cp "$O/post.lvs.json" "$report"
echo "cell census, synthesized -> post-route (differences only):"; cat "$O/census.txt"
python3 -I - "$O" <<'PY'
import collections, json, sys
o = sys.argv[1]
res = {}
for k, want in (("post", "match"), ("synth", "(not gating)"), ("neg", "mismatch")):
    try:
        d = json.load(open(f"{o}/{k}.lvs.json"))
    except Exception as e:
        print(f"{k:6s} NO REPORT ({e}); see {o}/{k}.err")
        res[k] = None
        continue
    c = d.get("counts", {})
    pc, bv = d.get("power_connectivity", {}), d.get("body_verification", {})
    print(f"{k:6s} engine={d.get('engine')} status={d.get('status')} (expected {want})",
          {n: (c[n]["layout"], c[n]["reference"], c[n]["matched"]) for n in c if n != "devices"},
          dict(d.get("category_counts", {})))
    print(f"{'':6s} power_connectivity={pc.get('status')} findings={[(f['rule'], f['pin']) for f in pc.get('findings', [])]}"
          f" body_verification={bv.get('status')}")
    res[k] = d
bulk = collections.Counter()
try:
    for ln in open(f"{o}/flat.spice").read().replace("\n+", " ").splitlines():
        if ln.startswith("M"):
            p = ln.split()
            bulk[(p[5], p[4])] += 1
except OSError:
    pass
print("flat transistor-level extraction, (device class, bulk net) -> count:", dict(bulk))
post, neg = res.get("post"), res.get("neg")
if post is None or post.get("status") != "match":
    sys.exit(3)
if post["power_connectivity"]["status"] == "mismatch":
    print("power_connectivity is `mismatch`: T1 item 4 (digital) is NOT satisfied")
    sys.exit(4)
if neg is None or neg.get("status") != "mismatch":
    sys.exit(5)
PY
