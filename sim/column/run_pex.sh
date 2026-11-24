#!/usr/bin/env bash
# sim/column/run_pex.sh -- provisional single-corner schematic-vs-extracted (PEX) comparison of the
# column benches (#209): LVS-match the bench-slice layout to the generated schematic DUT, then run
# `klt pex` over the five transient probe requests (tt, 1.8 V, 25 C, local backend) and assert each
# leg still shows the behaviour its bench exists to detect (lib/check_probe.py, via
# lib/check_pex_probe.py, once per side).
#
# The matched pair: layout/sram_col_slice.gds (design/compiler/gen_layout.py --bench-slice) and the
# flat schematic DUT sim/column/tb/pex/sram_col_slice.spice (sim/column/lib/make_column_tb.py) -- the
# same bit slice, one .include to swap. klt runs under the signoff pin (uvx --from klayout-tools==0.9.0),
# never the host build; PDK_ROOT/PDK come from sim/env.sh. Per-side execution is asserted from the
# report's own testbenches[].sides blocks (#219 caveat), never from this script's summary line.
#
# Usage: sim/column/run_pex.sh [bench ...]   (default: the five transient benches)
#   Writes sim/build/column-pex/<bench>/<...> (scratch; committed evidence is records/, append-only).
# Exit: 0 everything matched and every ladder check passed on both legs; 1 anything failed.
set -uo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo"
for t in python3 ngspice uvx; do
  command -v "$t" >/dev/null || { echo "run_pex.sh: TOOL_MISSING: $t not on PATH" >&2; exit 1; }
done
# shellcheck source=../env.sh
source sim/env.sh >/dev/null || { echo "run_pex.sh: PDK environment refused (see env.sh error above)" >&2; exit 1; }
KLT=(uvx --from klayout-tools==0.9.0 klt)
LAYOUT=layout/sram_col_slice.gds
TOP=sram_col_slice
PINS=VDD,VSS,BL0,BLB0,BL1,BLB1,BL2,BLB2,BL3,BLB3,CS0,CS1,CS2,CS3,SBL,SBLB,DOUT,DIN,WEN,SAE,PCHB,WL0,WLIN0,WLO,Q00,QB00,Q01,Q02
benches=("$@")
[[ ${#benches[@]} -gt 0 ]] || benches=(col_read0 col_read1 col_write0 col_write1 col_write0_nowen)
out="$repo/sim/build/column-pex"
mkdir -p "$out"

# 1. the generated pair is current (netlists, requests, committed GDS)
python3 -I sim/column/lib/make_column_tb.py --check || exit 1
uv run --no-project --with klayout python -I design/compiler/gen_layout.py \
    --check-bench-slice "$LAYOUT" || exit 1

# 2. LVS: the slice layout matches the schematic DUT; one perturbed cell must NOT (negative control)
lvs_req() { # $1 = reference netlist
  cat <<JSON
{
  "layout": {"file": "$LAYOUT", "deck": "sky130", "top": "$TOP"},
  "reference": {"netlist": "$1", "top": "$TOP", "form": "subckt-call", "deck": "sky130"},
  "options": {"combine_devices": true, "flatten_layout": true, "flatten_reference": true}
}
JSON
}
sed 's/^Xxc5_0.MAL bl0 wlo /Xxc5_0.MAL bl0 wl0 /' sim/column/tb/pex/sram_col_slice.spice > "$out/slice_bad.spice"
lvs_req "sim/column/tb/pex/sram_col_slice.spice" | "${KLT[@]}" lvs - --format json > "$out/lvs.json" 2> "$out/lvs.err" || true
lvs_req "$out/slice_bad.spice" | "${KLT[@]}" lvs - --format json > "$out/lvs_bad.json" 2> "$out/lvs_bad.err" || true
python3 -I - "$out" <<'PY' || exit 1
import json, sys
o = sys.argv[1]
good = json.load(open(f"{o}/lvs.json"))
bad = json.load(open(f"{o}/lvs_bad.json"))
assert good["status"] == "match", f"slice LVS: {good['status']}"
assert bad["status"] == "mismatch", f"negative control: {bad['status']}"
print(f"run_pex.sh: LVS {good['counts']['nets']['matched']}/{good['counts']['nets']['layout']} nets, "
      f"{good['counts']['devices']['matched']}/{good['counts']['devices']['layout']} devices matched; "
      f"control mismatch: yes")
PY

# 3. both legs of every requested bench, one klt pex invocation (one shared extraction)
reqs=()
for b in "${benches[@]}"; do
  reqs+=("sim/column/requests/pex/$b.probe.request.json")
done
rm -rf "$out/pex"
mkdir -p "$out/pex"
"${KLT[@]}" pex "$LAYOUT" "${reqs[@]}" --deck sky130 --pdk "$PDK" --pins "$PINS" \
    --rename-declared-pins --backend local --outdir "$out/pex/klt" -o "$out/pex/extracted.spice" \
    --format json > "$out/pex/report.json" 2> "$out/pex/stderr.log"
rc=$?
[ "$rc" -eq 0 ] || { echo "run_pex.sh: klt pex exited $rc (see $out/pex/stderr.log)" >&2; exit 1; }

# 4. every bench shows its expected behaviour on BOTH legs
fail=0
for b in "${benches[@]}"; do
  python3 -I sim/column/lib/check_pex_probe.py "$b" "$out/pex/report.json" || fail=1
done
[ "$fail" -eq 0 ] && echo "run_pex.sh: ${#benches[@]} bench(es) as expected on both legs"
exit "$fail"
