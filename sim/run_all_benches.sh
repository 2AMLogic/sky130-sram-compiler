#!/usr/bin/env bash
# sim/run_all_benches.sh -- cold start for every testbench of T1 item 9 (see sim/testbench-inventory.json).
# digital: cocotb control bench (RTL, synthesized netlist, seeded-fault controls) + the Icarus smoke benches;
# analog:  column benches, one local single-corner probe each (about 15 minutes in total).
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo"
rtl/tb/run.sh >/dev/null && echo "run_all_benches: rtl/tb/run.sh ok"
rtl/tb/cocotb/run.sh both
sim/column/run.sh
