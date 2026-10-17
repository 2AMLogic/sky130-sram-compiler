#!/usr/bin/env bash
# Re-run every marker case. Usage: run_checks.sh <outdir>   (scratch dir, outside the repo)
# Needs: klt (with its klayout engine / standalone `klayout`), a sky130A PDK under ~/.ciel (override with PDK=).
set -u
OUT=${1:?outdir}; mkdir -p "$OUT"
KLT_PY=${KLT_PY:-$(head -1 "$(command -v klt)" | sed 's/^#!//')}
PDK=${PDK:-$(ls -d "$HOME"/.ciel/ciel/sky130/versions/*/sky130A | head -1)}
HERE=$(cd "$(dirname "$0")" && pwd)
"$KLT_PY" -I "$HERE/build_cases.py" "$PDK" "$OUT"
MR=$PDK/libs.tech/klayout/drc/sky130A_mr.drc
for g in "$OUT"/*.gds; do
  f=$(basename "$g" .gds)
  klt drc "$g" --deck sky130 --format json > "$OUT/$f.curated.json" 2>/dev/null
  klt drc "$g" --engine klayout --pdk sky130A --format json > "$OUT/$f.lydrc.json" 2>/dev/null
  klt drc "$g" --engine klayout --deck-file "$MR" --deck-var feol=true --deck-var beol=true \
    --deck-var thr=1 --format json > "$OUT/$f.mr.json" 2>/dev/null
done
"$KLT_PY" -I "$HERE/summarize.py" "$OUT"
