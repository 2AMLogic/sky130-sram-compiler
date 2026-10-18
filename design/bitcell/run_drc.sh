#!/usr/bin/env bash
# Run the three sky130 DRC paths over a bitcell GDS and print rule counts.
# Usage: design/bitcell/run_drc.sh <layout.gds> <outdir>     (outdir: scratch, outside the repo)
# Decks (see verification/marker/records/2026-10-17-f22b400.md for why all three):
#   curated   klt --deck sky130        marker-blind
#   lydrc     PDK sky130A.lydrc        marker-aware for a few well/implant rules only
#   mr        PDK sky130A_mr.drc       the only deck that switches rule sets on areaid.ce (81/2);
#             with no marker drawn it applies the strict (logic) rules everywhere.
# klt reports `coverage_unknown` (exit 4) on zero-finding klayout-engine runs:
# "0" means no violation reported, not proven clean -- run with a known-bad layout as control.
set -u
G=${1:?layout.gds}; O=${2:?outdir}; mkdir -p "$O"
PDK=${SKY130_VARIANT_DIR:-$HOME/.ciel/sky130A}
MR=$PDK/libs.tech/klayout/drc/sky130A_mr.drc
klt drc "$G" --deck sky130 --format json > "$O/curated.json" 2>"$O/curated.err"
klt drc "$G" --engine klayout --pdk sky130A --format json > "$O/lydrc.json" 2>"$O/lydrc.err"
klt drc "$G" --engine klayout --deck-file "$MR" --deck-var feol=true --deck-var beol=true \
  --deck-var thr=1 --format json > "$O/mr.json" 2>"$O/mr.err"
python3 -I - "$O" <<'PY'
import collections, json, sys
for eng in ("curated", "lydrc", "mr"):
    d = json.load(open(f"{sys.argv[1]}/{eng}.json"))
    c = collections.Counter(v["rule"] for v in d["violations"])
    print(f"{eng:8s} {d['status']:18s} total={sum(c.values()):3d} {dict(sorted(c.items()))}")
PY
