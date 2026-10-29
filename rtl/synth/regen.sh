#!/usr/bin/env bash
# rtl/synth/regen.sh -- regenerate (or --check) the committed gate-level
# netlist rtl/synth/sram_ctrl_256x32_synth.v from rtl/sram_ctrl.v with
# `klt synthesize` against sky130_fd_sc_hd on the PDK pinned in sim/pdk.json.
#
# Usage: rtl/synth/regen.sh            rewrite the committed netlist
#        rtl/synth/regen.sh --check    synthesize twice into scratch, require
#                                      both runs byte-identical to the
#                                      committed netlist (exit 3 on drift)
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo"
mode="${1:-write}"
committed=rtl/synth/sram_ctrl_256x32_synth.v
scratch=sim/build/synth

for t in klt yosys; do
  command -v "$t" >/dev/null || { echo "regen.sh: TOOL_MISSING: $t not on PATH" >&2; exit 1; }
done
# shellcheck source=../../sim/env.sh
source sim/env.sh >/dev/null || { echo "regen.sh: PDK environment refused (see env.sh error above)" >&2; exit 1; }

run_once() { # $1 = tag; leaves the netlist at $scratch/$1.v
  rm -rf "$scratch/run"
  klt synthesize rtl/synth/request.json --pdk "$PDK" --pdk-root "$PDK_ROOT" --format json \
    > "$scratch/$1.report.json"
  cp "$scratch/run/sram_ctrl_synth.v" "$scratch/$1.v"
}

mkdir -p "$scratch"
run_once a
run_once b
cmp "$scratch/a.v" "$scratch/b.v" || { echo "regen.sh: NONDETERMINISTIC synthesis output" >&2; exit 1; }

case "$mode" in
  write)   cp "$scratch/a.v" "$committed"; echo "regen.sh: wrote $committed" ;;
  --check) cmp "$scratch/a.v" "$committed" || { echo "regen.sh: $committed is stale; run rtl/synth/regen.sh" >&2; exit 3; }
           echo "regen.sh: $committed is current" ;;
  *) echo "usage: $0 [--check]" >&2; exit 2 ;;
esac
