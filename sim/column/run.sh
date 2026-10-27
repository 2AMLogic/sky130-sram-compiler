#!/usr/bin/env bash
# sim/column/run.sh -- cold start for the column (bit-slice) benches, analog partition of T1 item 9.
#
# Checks the generated benches against the compiled macro, then runs each bench ONCE at a single corner
# (tt, 1.8 V, 25 C) locally with `klt sim --backend local` and asserts it shows what it is built to detect
# (lib/check_probe.py). Multi-corner and Monte Carlo grids are NOT run here: they are the committed
# requests/<bench>.request.json, submitted with `klt sim` to the batch fleet (see README.md).
#
# Usage: sim/column/run.sh [bench ...]     (default: every bench; one ngspice at a time)
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo"
for t in klt ngspice python3; do
  command -v "$t" >/dev/null || { echo "run.sh: TOOL_MISSING: $t not on PATH" >&2; exit 1; }
done
# shellcheck source=../env.sh
source sim/env.sh >/dev/null || { echo "run.sh: PDK environment refused (see env.sh error above)" >&2; exit 1; }
python3 -I sim/column/lib/make_column_tb.py --check
benches=("$@")
[[ ${#benches[@]} -gt 0 ]] || benches=(col_read_snm col_hold_snm col_read0 col_read1 col_write0 col_write1 col_write0_nowen)
out="$repo/sim/build/column-probe"
mkdir -p "$out"
for b in "${benches[@]}"; do
  rm -rf "$out/$b"
  ( cd sim/column/requests && klt sim "$b.probe.request.json" --backend local -o "$out/$b" --format json > "$out/$b.json" 2> "$out/$b.err" ) \
    || { echo "run.sh: $b: klt sim failed (see $out/$b.err)" >&2; exit 1; }
  python3 -I sim/column/lib/check_probe.py "$b" "$out/$b.json"
done
echo "run.sh: ${#benches[@]} column bench probe(s) as expected"
