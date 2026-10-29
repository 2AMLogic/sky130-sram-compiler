#!/usr/bin/env bash
# rtl/tb/run.sh -- Icarus smoke benches for sram_ctrl and sram_behav.
# PDK-free. Runs the min (16 words), reference (256 x 32) and max (1024 words)
# address widths. Exits non-zero on any failure.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
build="$here/../../sim/build/rtl-tb"
mkdir -p "$build"
fail=0
for cfg in "16 8" "256 32" "1024 64"; do
  read -r words bits <<<"$cfg"
  for tb in sram_behav sram_ctrl; do
    out="$build/${tb}_${words}x${bits}.vvp"
    iverilog -g2005-sv -Wall -Wno-timescale -P "tb_$tb.WORDS=$words" -P "tb_$tb.BITS=$bits" \
      -o "$out" "$here/tb_$tb.v" "$here/../$tb.v"
    res="$(vvp -n "$out")"; echo "$res" | grep -E 'TB_|FAIL' || true
    echo "$res" | grep -q '^TB_PASS' || fail=1
  done
done
exit "$fail"
