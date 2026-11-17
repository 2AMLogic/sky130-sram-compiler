#!/usr/bin/env bash
# Re-run every marker case. Usage: run_checks.sh <outdir>   (scratch dir, outside the repo)
# Needs: klt (with its klayout engine / standalone `klayout`), a sky130A PDK under ~/.ciel
# (override with SKY130_VARIANT_DIR=<.../sky130A>; PDK is the variant NAME, as sim/env.sh exports).
set -eu
OUT=${1:?outdir}; mkdir -p "$OUT"
command -v klt >/dev/null || { echo "klt not on PATH" >&2; exit 1; }
KLT_PY=${KLT_PY:-$(head -1 "$(command -v klt)" | sed 's/^#!//')}
PDK_DIR=${SKY130_VARIANT_DIR:-${PDK_ROOT:-$HOME/.ciel}/${PDK:-sky130A}}
case $PDK_DIR in
  /*) ;;
  *) echo "run_checks: PDK_DIR='$PDK_DIR' is not an absolute variant dir (override with SKY130_VARIANT_DIR=<.../sky130A>)" >&2; exit 1;;
esac
HERE=$(cd "$(dirname "$0")" && pwd)
"$KLT_PY" -I "$HERE/build_cases.py" "$PDK_DIR" "$OUT"
# The three-deck invocations are design/bitcell/three_deck_drc.sh (shared with
# design/bitcell/run_drc.sh, one source for the mr deck-var trio); stderr is
# kept as <case>.<deck>.err. summarize.py prints the counts and asserts the
# stripped-marker mr control; any deck/klt failure aborts here via set -e.
for g in "$OUT"/*.gds; do
  f=$(basename "$g" .gds)
  "$HERE/../../design/bitcell/three_deck_drc.sh" "$g" "$OUT" "$f."
done
"$KLT_PY" -I "$HERE/summarize.py" "$OUT"
