#!/usr/bin/env bash
# sim/smoke/run.sh -- toolchain smoke: one ngspice inverter (DC op + short
# transient, tt corner, single local run) and one Yosys synthesis against
# sky130_fd_sc_hd, on the pinned PDK. Writes an append-only record to
# sim/smoke/records/<UTC timestamp>-<git sha>.md. Sizes nothing, draws no cell.
#
# Usage: sim/smoke/run.sh        (from anywhere inside the repo)
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo"

for t in ngspice yosys sha256sum; do
  command -v "$t" >/dev/null || { echo "run.sh: TOOL_MISSING: $t not on PATH" >&2; exit 1; }
done
# shellcheck source=../env.sh
source sim/env.sh || { echo "run.sh: PDK environment refused (see env.sh error above)" >&2; exit 1; }

build=sim/build/smoke
mkdir -p "$build" sim/smoke/records
deck_hash="$(sha256sum sim/smoke/inverter.sp.in | cut -d' ' -f1)"
ys_hash="$(sha256sum sim/smoke/synth.ys.in sim/smoke/placeholder.v | sha256sum | cut -d' ' -f1)"
sed "s|@MODEL_FILE@|$SKY130_MODEL_FILE|" sim/smoke/inverter.sp.in > "$build/inverter.sp"
sed -e "s|@STD_LIB@|$SKY130_STD_LIB|g" -e "s|@OUT@|$build/smoke_top.synth.v|" \
    sim/smoke/synth.ys.in > "$build/synth.ys"

ngspice -b -o "$build/ngspice.out" "$build/inverter.sp" || true
yosys -q -l "$build/yosys.out" -s "$build/synth.ys"

grep -q '^SMOKE_PASS' "$build/ngspice.out" || { echo "run.sh: SMOKE_FAIL (ngspice), see $build/ngspice.out" >&2; exit 1; }
[[ -s "$build/smoke_top.synth.v" ]] || { echo "run.sh: SMOKE_FAIL (yosys produced no netlist)" >&2; exit 1; }

sp_ver="$(ngspice -v 2>&1 | grep -m1 -o 'ngspice-[0-9.]*')"
ys_ver="$(yosys -V)"
sha="$(git rev-parse --short HEAD)"
ts="$(date -u +%Y%m%dT%H%M%SZ)"
rec="sim/smoke/records/$ts-$sha.md"
[[ ! -e "$rec" ]] || { echo "run.sh: record $rec exists; records are append-only" >&2; exit 1; }

{
  echo "# Smoke record $ts ($sha)"
  echo
  echo "- simulator: $sp_ver"
  echo "- synthesis: $ys_ver"
  echo "- PDK: $PDK, open_pdks revision $SKY130_PDK_VERSION (pin: $SKY130_PDK_PIN)"
  echo "- ngspice deck: sim/smoke/inverter.sp.in sha256 $deck_hash"
  echo "- yosys inputs (synth.ys.in + placeholder.v) combined sha256 $ys_hash"
  echo "- corner: tt, 25 C, 1.8 V; single local run"
  echo "- result: PASS"
  echo
  echo '## ngspice'
  echo '```'
  grep -E '^(SMOKE_|t_fall|t_rise)' "$build/ngspice.out"
  echo '```'
  echo
  echo '## yosys (sky130_fd_sc_hd, tt_025C_1v80)'
  echo '```'
  sed -n '/^ *[0-9]\+ \+[0-9.]\+ cells$/,/Chip area/p' "$build/yosys.out" | sed 's/[[:space:]]*$//'
  echo '```'
} > "$rec"
echo "run.sh: PASS; record written to $rec"
