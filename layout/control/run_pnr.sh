#!/usr/bin/env bash
# layout/control/run_pnr.sh -- regenerate (or --check) the committed routed
# control block layout/control/control.gds, its sha256, and the P&R response
# place-and-route.response.json from the committed gate-level netlist
# rtl/synth/sram_ctrl_256x32_synth.v with `klt place-and-route` against
# sky130_fd_sc_hd on the PDK pinned in sim/pdk.json.
#
# Usage: layout/control/run_pnr.sh            rewrite the committed outputs
#        layout/control/run_pnr.sh --check    run the flow twice into scratch,
#                                             require both GDS byte-identical
#                                             to each other and to the
#                                             committed GDS (exit 3 on drift)
#
# Runs klt from the repo root on purpose: the `openroad` wrapper on PATH is a
# container that mounts only its working directory, and the netlist lives
# outside layout/control/.
set -euo pipefail

repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo"
mode="${1:-write}"
dir=layout/control
request=$dir/place-and-route.request.json
flow_out=$dir/.klt/place-and-route
scratch=sim/build/pnr

for t in klt openroad jq sha256sum; do
  command -v "$t" >/dev/null || { echo "run_pnr.sh: TOOL_MISSING: $t not on PATH" >&2; exit 1; }
done
# shellcheck source=../../sim/env.sh
source sim/env.sh >/dev/null || { echo "run_pnr.sh: PDK environment refused (see env.sh error above)" >&2; exit 1; }

run_once() { # $1 = tag; leaves $scratch/$1.gds and $scratch/$1.response.json
  klt place-and-route "$request" --pdk "$PDK" --pdk-root "$PDK_ROOT" --format json \
    > "$scratch/$1.response.json"
  jq -e '.status == "ok" and .stage_reached == "route" and .power.pdn == true
         and (.power.tapcell_master | type == "string")' \
    "$scratch/$1.response.json" >/dev/null \
    || { echo "run_pnr.sh: P&R did not reach route with power.pdn true and a tapcell master" >&2; exit 1; }
  cp "$flow_out/sram_ctrl.gds" "$scratch/$1.gds"
}

mkdir -p "$scratch"
run_once a
run_once b
cmp "$scratch/a.gds" "$scratch/b.gds" || { echo "run_pnr.sh: NONDETERMINISTIC P&R output" >&2; exit 1; }

case "$mode" in
  write)
    cp "$scratch/a.gds" $dir/control.gds
    cp "$scratch/a.response.json" $dir/place-and-route.response.json
    (cd $dir && sha256sum control.gds > control.gds.sha256)
    echo "run_pnr.sh: wrote $dir/control.gds, control.gds.sha256, place-and-route.response.json" ;;
  --check)
    cmp "$scratch/a.gds" $dir/control.gds \
      || { echo "run_pnr.sh: $dir/control.gds is stale; run $dir/run_pnr.sh" >&2; exit 3; }
    (cd $dir && sha256sum -c control.gds.sha256 >/dev/null) \
      || { echo "run_pnr.sh: control.gds.sha256 does not match control.gds" >&2; exit 3; }
    echo "run_pnr.sh: $dir/control.gds is current" ;;
  *) echo "usage: $0 [--check]" >&2; exit 2 ;;
esac
