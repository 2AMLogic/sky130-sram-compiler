#!/usr/bin/env bash
# rtl/tb/cocotb/run.sh -- cold-start wrapper for the cocotb control bench.
# Creates a pinned venv under sim/build/ (never a host-wide install), sources
# the PDK pin check (the synthesized netlist needs the sky130_fd_sc_hd models)
# and runs the bench against the RTL and the synthesized netlist.
# Usage: rtl/tb/cocotb/run.sh [rtl|synth|mutants|both]
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$repo"
COCOTB_VERSION=2.1.0
venv=sim/build/venv-cocotb
for t in python3 iverilog vvp; do
  command -v "$t" >/dev/null || { echo "run.sh: TOOL_MISSING: $t not on PATH" >&2; exit 1; }
done
if [[ ! -x $venv/bin/python ]] || ! "$venv/bin/python" -c "import cocotb,sys; sys.exit(cocotb.__version__ != '$COCOTB_VERSION')" 2>/dev/null; then
  python3 -m venv "$venv"
  "$venv/bin/pip" install -q "cocotb==$COCOTB_VERSION"
fi
# shellcheck source=../../../sim/env.sh
source sim/env.sh >/dev/null || { echo "run.sh: PDK environment refused (see env.sh error above)" >&2; exit 1; }
exec "$venv/bin/python" -I rtl/tb/cocotb/run.py "${1:-both}"
