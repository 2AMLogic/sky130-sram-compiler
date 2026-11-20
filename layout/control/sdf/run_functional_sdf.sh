#!/usr/bin/env bash
# layout/control/sdf/run_functional_sdf.sh -- T1 item 7 (digital): re-run the
# committed cocotb control bench (rtl/tb/cocotb/, unmodified) against the
# post-route gate-level netlist layout/control/sram_ctrl_routed.v through
# `klt functional-verification` with the post-route SDF back-annotated
# (options.sdf), and rewrite the committed reports under evidence/:
#
#   fv-sdf-tt.request.json.in         tt_025C_1v80 SDF (the P&R corner;
#                                     evidence/item7-digital.json, the file
#                                     the manifest cites for 7.digital)
#   fv-sdf-ss.request.json.in         ss_n40C_1v28 SDF, the worst-setup corner
#                                     the P&R response reports
#                                     (evidence/item7-digital-ss-n40C-1v28.json)
#   fv-zero-delay-tt.request.json.in  negative control: the same request minus
#                                     options.sdf -- it passes at zero delay
#                                     with environment.sdf null, which klt
#                                     signoff grades not_post_layout, showing
#                                     the annotated: true evidence is
#                                     load-bearing (evidence/item7-digital-unannotated.json)
#
# The bench clock stays the placeholder 10 ns (#40): every result this script
# writes is tied to that period and to the committed routed netlist; a re-route
# under #40 regenerates the SDFs and this evidence.
#
# The templates are committed with an @SKY130_VARIANT_DIR@ placeholder because
# klt functional-verification has no --pdk flag: the sky130_fd_sc_hd Verilog
# models must be named as concrete source paths, and a committed request with
# a host-absolute path would not be checkout-free. Each run materializes its
# request (sed) into layout/control/sdf/.fv-*.request.json (gitignored) so the
# request's own relative paths (netlist, SDF, bench) resolve as committed.
#
# Usage: layout/control/sdf/run_functional_sdf.sh    (rewrites the evidence)
# Needs the pinned klt (klayout-tools 0.9.0 with the functional-verification
# extra), iverilog >= 13.0 and the PDK pinned in sim/pdk.json.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$repo"
dir=layout/control/sdf
scratch=sim/build/fv-sdf

for t in klt iverilog jq; do
  command -v "$t" >/dev/null || { echo "run_functional_sdf.sh: TOOL_MISSING: $t not on PATH" >&2; exit 1; }
done
# shellcheck source=../../../sim/env.sh
source sim/env.sh >/dev/null || { echo "run_functional_sdf.sh: PDK environment refused (see env.sh error above)" >&2; exit 1; }

run() { # $1 = template stem, $2 = evidence output, $3 = annotated | control
  local tmpl="$dir/$1.request.json.in" out="$2" mode="$3"
  [[ -f "$tmpl" ]] || { echo "run_functional_sdf.sh: missing template $tmpl" >&2; exit 1; }
  sed "s|@SKY130_VARIANT_DIR@|$SKY130_VARIANT_DIR|g" "$tmpl" > "$dir/.fv-$1.request.json"
  mkdir -p "$scratch"
  local rc=0
  klt functional-verification "$dir/.fv-$1.request.json" -o "$scratch/out-$1" --format json \
    > "$out.tmp" || rc=$?
  # exit 0 = all pass, 3 = ran clean with failing tests (a recordable outcome,
  # issue #206); anything else means the run itself failed and no report was
  # written.
  if [[ $rc -ne 0 && $rc -ne 3 ]] || ! jq -e 'has("status")' "$out.tmp" >/dev/null 2>&1; then
    echo "run_functional_sdf.sh: $1: klt functional-verification exited $rc without a report" >&2
    rm -f "$out.tmp"
    exit 1
  fi
  # The annotation mode must match the request's role before the committed
  # report is replaced: a corner report is only evidence if environment.sdf.annotated
  # is true, and the zero-delay control only if environment.sdf is null. A swapped
  # or mis-templated request is rejected, never moved into evidence/. An annotated
  # run with failing tests is still valid evidence (exit 3 above).
  if [[ "$mode" == annotated ]]; then
    jq -e '.environment.sdf.annotated == true' "$out.tmp" >/dev/null \
      || { echo "run_functional_sdf.sh: $1: expected an annotated report (environment.sdf.annotated == true)" >&2; rm -f "$out.tmp"; exit 1; }
  else
    jq -e '.environment.sdf == null' "$out.tmp" >/dev/null \
      || { echo "run_functional_sdf.sh: $1: expected the zero-delay control (environment.sdf == null)" >&2; rm -f "$out.tmp"; exit 1; }
  fi
  mv "$out.tmp" "$out"
  echo "run_functional_sdf.sh: $1 -> $out: $(jq -r '"\(.status) \(.passed_count)/\(.test_count) tests"' "$out")"
}

run fv-sdf-tt          evidence/item7-digital.json annotated
run fv-sdf-ss          evidence/item7-digital-ss-n40C-1v28.json annotated
run fv-zero-delay-tt   evidence/item7-digital-unannotated.json control
