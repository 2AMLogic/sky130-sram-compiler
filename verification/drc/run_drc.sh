#!/usr/bin/env bash
# T1 item 3 (DRC clean) runs for the 256 x 32 reference instance. Single-unit local runs, one at a time.
# Usage: verification/drc/run_drc.sh <outdir>      (scratch dir, outside the repo)
# Writes into <outdir>: analog/{curated,lydrc,mr}.json (design/bitcell/run_drc.sh, the three-deck pattern),
# digital/curated.json, scan*.json (areaid.ce scan + its positive control), seam/curated.json, times.txt.
# Run from anywhere: it cd's to the repo root so report `file` paths are repo-relative.
set -eu
O=${1:?outdir}; mkdir -p "$O"
cd "$(cd "$(dirname "$0")/../.." && pwd)"
KLT_PY=${KLT_PY:-$(head -1 "$(command -v klt)" | sed 's/^#!//')}
AG=layout/sram_256x32_m4.gds; DG=layout/control/control.gds
NEG=verification/drc/neg_probe.gds
# stale-stream guard: the streams must be the committed ones this run claims to check
echo "ca10c045b447a8ce3bdb55f8922e2dfb954826dd8a9583ca0d39629d5b9e555c  $AG" | sha256sum -c -
(cd layout/control && sha256sum -c control.gds.sha256)
: > "$O/times.txt"
t() { local s=$SECONDS; "$@"; echo "$* : $((SECONDS - s)) s" >> "$O/times.txt"; }
# Timed, gated `klt drc`: tk <report.json> <stderr.err> <klt drc args...>. The
# three_deck_drc.sh exit-code contract applies here too: 0 clean, 3 violations and
# 4 coverage_unknown are normal outcomes, so the run continues and the times line is
# logged; any other exit is a deck/klt failure and aborts the run with that code --
# never `|| true`, which would leave an empty or partial report for make_record.py
# to copy over the committed evidence before failing to parse it (#183).
tk() {
  local json=$1 err=$2; shift 2
  local s=$SECONDS rc=0
  klt drc "$@" > "$json" 2> "$err" || rc=$?
  case $rc in
    0|3|4) echo "klt drc $* : $((SECONDS - s)) s" >> "$O/times.txt";;
    *) echo "run_drc: klt drc FAILED (exit $rc) on $* -- see $err" >&2; exit "$rc";;
  esac
}
mkdir -p "$O/analog" "$O/digital" "$O/seam"
# graded reports: curated deck, with the known-bad fixture as in-report negative control
CUR=(--deck sky130 --negative-control "$NEG" --negative-control-categories met1.width.1 --format json)
t design/bitcell/run_drc.sh "$AG" "$O/analog" > "$O/analog/summary.txt"
tk "$O/analog/curated-graded.json" "$O/analog/curated-graded.err" "$AG" "${CUR[@]}"
tk "$O/digital/curated.json" "$O/digital/curated.err" "$DG" "${CUR[@]}"
# areaid.ce scan, with a positive control proving the scan can see a marker
$KLT_PY -I verification/drc/probe.py scan "$AG" > "$O/scan-macro.json"
$KLT_PY -I verification/drc/probe.py scan "$DG" > "$O/scan-control.json"
$KLT_PY -I verification/drc/probe.py marker-probe "$O/marker_probe.gds"
$KLT_PY -I verification/drc/probe.py scan "$O/marker_probe.gds" > "$O/scan-positive-control.json"
# seam control: slivers straddling the array/periphery seams must be flagged by the same deck
$KLT_PY -I verification/drc/probe.py seam-probe "$AG" "$O/seam/macro_seam_probe.gds"
tk "$O/seam/curated.json" "$O/seam/curated.err" "$O/seam/macro_seam_probe.gds" --deck sky130 --format json
cat "$O/analog/summary.txt"; cat "$O/times.txt"
