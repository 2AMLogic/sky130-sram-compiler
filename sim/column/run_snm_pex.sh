#!/usr/bin/env bash
# Provisional single-corner (tt, 1.8 V, 25 C) hold/read SNM comparison on the LVS-clean
# decoupled half-cell column top (`sram_snm_halfcell_col64`, #228) via the signoff-pinned
# `klt pex --measure-command` path (#210, input to #207 / ROADMAP item 7 analog).
#
# Usage: sim/column/run_snm_pex.sh [--report PATH] [--klt CMD] <outdir>
#   <outdir>: scratch directory (outside repo or under gitignored sim/build/). Each run
#             allocates its own unique child `<outdir>/snm-pex.XXXXXX`.
#   --report PATH: copy the accepted `klt pex` JSON report to PATH (gzipped if PATH ends
#                  in `.gz`; fails exit 1 if the copy fails).
#   --klt CMD: override the klt launcher; default `uvx --from klayout-tools==0.9.0 klt`.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KLT="uvx --from klayout-tools==0.9.0 klt"
report=""

usage() { sed -n '2,12p' "${BASH_SOURCE[0]}"; exit 2; }
while [ $# -gt 0 ]; do
  case "$1" in
    --report) [ $# -ge 2 ] || usage; report=$2; shift 2 ;;
    --klt) [ $# -ge 2 ] || usage; KLT=$2; shift 2 ;;
    -h|--help) usage ;;
    --*) echo "run_snm_pex.sh: usage: unknown option $1" >&2; exit 2 ;;
    *) break ;;
  esac
done

[ $# -eq 1 ] || usage
O=$1

read -r -a KLT_ARR <<< "$KLT"
[ "${#KLT_ARR[@]}" -gt 0 ] || { echo "run_snm_pex.sh: TOOL_MISSING: empty --klt command" >&2; exit 1; }
for t in python3 uv /usr/bin/time ngspice "${KLT_ARR[0]}"; do
  command -v "$t" >/dev/null || { echo "run_snm_pex.sh: TOOL_MISSING: $t not on PATH" >&2; exit 1; }
done
timeout 300 "${KLT_ARR[@]}" --version >/dev/null 2>&1 \
  || { echo "run_snm_pex.sh: TOOL_MISSING: '$KLT --version' failed" >&2; exit 1; }

[ -z "$report" ] || report="$(realpath -m "$report")"
mkdir -p "$O" || { echo "run_snm_pex.sh: cannot create outdir $O" >&2; exit 1; }
O="$(realpath "$O")"

cd "$repo"
# shellcheck source=../env.sh
source sim/env.sh >/dev/null || { echo "run_snm_pex.sh: PDK environment refused" >&2; exit 1; }
python3 -I design/macro/lvs/make_snm_ref.py --check >/dev/null
python3 -I sim/column/lib/make_column_tb.py --check >/dev/null
sim/bitcell/lib/fetch_pinned.sh >/dev/null

scratch="$(mktemp -d "$O/snm-pex.XXXXXX")"
gds="$scratch/sram_snm_halfcell_col64.gds"
uv run --no-project --with klayout python -I design/compiler/gen_layout.py \
  --snm-halfcell -o "$gds" --report > "$scratch/layout.json"

pins="BL0,BLB0,IN,OUT,PCHB,VDD,VSS,$(seq -s, -f 'WL%g' 0 63)"
measure_cmd="python3 -I sim/column/lib/snm_pex.py --measure-snm-dut --klt '$KLT'"

set +e
/usr/bin/time -v -o "$scratch/time.v" -- "${KLT_ARR[@]}" pex "$gds" \
  --top sram_snm_halfcell_col64 \
  --deck sky130 \
  --pdk sky130A \
  --pdk-root "$PDK_ROOT" \
  --pins "$pins" \
  --rename-declared-pins \
  --device-only-leg \
  --reference-netlist design/macro/lvs/sram_snm_halfcell_col64.spice \
  --measure-command "$measure_cmd" \
  --measure-timeout-s 660 \
  --backend local \
  --outdir "$scratch/klt-outdir" \
  -o "$scratch/extracted.spice" \
  --envelope-out "$scratch/report.json" \
  --format json > "$scratch/stdout.json" 2> "$scratch/stderr"
rc=$?
set -e

if [ "$rc" -ne 0 ]; then
  echo "run_snm_pex.sh: klt pex exited $rc (scratch preserved at $scratch)" >&2
  tail -n 10 "$scratch/stderr" >&2 || true
  exit "$rc"
fi

# Validate that hold_eye_snm and read_eye_snm both have finite numeric schematic and extracted values.
python3 -I - "$scratch/report.json" "$scratch/time.v" <<'PY'
import json, math, sys

rep = json.load(open(sys.argv[1]))
if rep.get("status") != "pass":
    sys.exit(f"run_snm_pex.sh: report status={rep.get('status')!r}, expected 'pass'")
by_row = {d["spec_row"]: d for d in rep.get("delta", [])}
for key in ("hold_eye_snm", "read_eye_snm"):
    if key not in by_row:
        sys.exit(f"run_snm_pex.sh: missing delta row {key}")
    d = by_row[key]
    for field in ("schematic_value", "extracted_value", "device_only_value"):
        v = d.get(field)
        if not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            sys.exit(f"run_snm_pex.sh: invalid {key}.{field}={v!r}")
    delta_mv = (d["extracted_value"] - d["schematic_value"]) * 1e3
    print(f"run_snm_pex.sh: {key} sch={d['schematic_value']:.6f}V ext={d['extracted_value']:.6f}V "
          f"dev={d['device_only_value']:.6f}V delta={delta_mv:+.3f}mV ({d['delta_pct']:+.3f}%)")

elapsed = rss = None
for ln in open(sys.argv[2]):
    if "Elapsed (wall clock) time" in ln:
        elapsed = ln.split("):")[-1].strip()
    elif "Maximum resident set size" in ln:
        rss = int(ln.rsplit(":", 1)[1])
print(f"run_snm_pex.sh: wall={elapsed} peak_rss={rss}kB klt={rep['provenance']['klt_version']}")
PY

if [ -n "$report" ]; then
  if [[ "$report" == *.gz ]]; then
    gzip -n -c "$scratch/report.json" > "$report"
  else
    cp "$scratch/report.json" "$report"
  fi
fi

echo "run_snm_pex.sh: accepted; scratch $scratch"
