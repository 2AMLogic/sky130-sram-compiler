#!/usr/bin/env bash
# The three sky130 DRC deck invocations, in one place: every runner that runs
# curated + lydrc + mr calls this instead of restating the flags.
# Usage: three_deck_drc.sh <layout.gds> <outdir> [name-prefix]
#   writes <outdir>/<name-prefix>{curated,lydrc,mr}.{json,err}
# Callers:
#   design/bitcell/run_drc.sh <gds> <outdir>     -> prefix ""      (flat names)
#   verification/marker/run_checks.sh <outdir>   -> prefix "<case>." (case-prefixed names)
# Single source of the deck flags -- above all the sky130A_mr.drc
# --deck-var feol=true --deck-var beol=true --deck-var thr=1 trio, without which
# the mr deck silently checks nothing (verification/marker/records/2026-10-17-f22b400.md).
# PDK resolution (for the mr deck file), in order: PDK, SKY130_VARIANT_DIR,
# ~/.ciel/sky130A -- so both runners' overrides keep working and both runners see
# the same deck. stderr is kept per deck in <name-prefix><deck>.err, never discarded.
# klt drc exit codes (docs/cli/drc.md contract): 0 clean, 3 violations, and
# 4 coverage_unknown (expected on zero-finding klayout-engine runs) are normal
# outcomes here; any other exit is a deck/klt failure and aborts the run with
# that exit code. Interpreting the counts is the caller's job (this script prints
# nothing): summarize.py asserts the stripped-marker mr control for run_checks.sh.
set -eu
G=${1:?layout.gds}; O=${2:?outdir}; PRE=${3:-}
command -v klt >/dev/null || { echo "three_deck_drc: klt not on PATH" >&2; exit 1; }
PDK=${PDK:-${SKY130_VARIANT_DIR:-$HOME/.ciel/sky130A}}
MR=$PDK/libs.tech/klayout/drc/sky130A_mr.drc
[ -f "$MR" ] || { echo "three_deck_drc: mr deck not found at $MR (wrong PDK? override with PDK=)" >&2; exit 1; }
mkdir -p "$O"
run_deck() {  # run_deck <deck-name> <klt drc args...>
  local name=$1
  shift
  local out="$O/$PRE$name"
  local rc=0
  klt drc "$G" "$@" --format json > "$out.json" 2> "$out.err" || rc=$?
  case $rc in
    0|3|4) ;;
    *) echo "three_deck_drc: $name deck FAILED (exit $rc) on $G -- see $out.err" >&2; return "$rc";;
  esac
}
run_deck curated --deck sky130
run_deck lydrc --engine klayout --pdk sky130A
run_deck mr --engine klayout --deck-file "$MR" \
  --deck-var feol=true --deck-var beol=true --deck-var thr=1
