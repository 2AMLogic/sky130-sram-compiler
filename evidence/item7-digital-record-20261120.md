# T1 item 7 (digital): SDF-annotated functional re-run of the routed `sram_ctrl` — record of 2026-11-20

Post-layout leg of T1 item 7 for the digital partition: the committed cocotb
control bench (`rtl/tb/cocotb/`, unmodified) re-run against the post-route
gate-level netlist `layout/control/sram_ctrl_routed.v` through
`klt functional-verification` with post-route SDF timing back-annotated
(`options.sdf`). The manifest cites both annotated runs for `7.digital`:
`evidence/item7-digital.json` (tt, passes) and
`evidence/item7-digital-ss-n40C-1v28.json` (the worst-setup corner, a measured
functional **failure** under annotated timing; see below). Each report's
`environment.sdf.annotated` is `true`. With both cited, `klt signoff` grades
7.digital `unmet / check_failed` and the block total is **14 of 22** (the
tt-only citation gave 15/22). Not cited, same flow, same bench:
- `evidence/item7-digital-unannotated.json` — the negative control: the same
  request minus `options.sdf`. It passes at (library-placeholder) zero delay
  with `environment.sdf: null`, and `klt signoff` grades exactly that
  `not_post_layout` (verified live: pointing the manifest's `7.digital` at
  this report re-grades the item `unmet / not_post_layout`; pointing it at
  the failing ss report grades `unmet / check_failed`). The annotated `true`
  is load-bearing, not a formality.

Reproduce (needs the pinned `klt 0.9.0` with the `functional-verification`
extra, `iverilog` 13.0 and the PDK pinned in `sim/pdk.json`):

```console
layout/control/run_pnr.sh                 # writes sdf/sram_ctrl.tt_025C_1v80.sdf (+ DEF, SPEF)
layout/control/sdf/run_sta_sdf.sh         # writes sdf/sram_ctrl.ss_n40C_1v28.sdf
layout/control/sdf/run_functional_sdf.sh  # rewrites the three evidence reports
```

The requests are committed as `layout/control/sdf/*.request.json.in`
templates (the `@SKY130_VARIANT_DIR@` placeholder exists because
`klt functional-verification` names PDK cell-model sources as concrete paths
and has no `--pdk` flag; a host-absolute path in a committed request would
not be checkout-free). `options.sdf.scope` is `dut`: the bench's `tb_top`
wraps the netlist as its `dut` instance and a P&R-written SDF is rooted at
the netlist module.

## SDF provenance and corners

- `sdf/sram_ctrl.tt_025C_1v80.sdf` — written by the place-and-route flow
  itself (`post_route_spef` + `post_route_sdf` in
  `layout/control/place-and-route.request.json`), i.e. at the corner the P&R
  request names. The regenerated `place-and-route.response.json` now carries
  `spef_sta`: SPEF annotation complete on the design side (260/260 design
  nets), SPEF-fed worst slack **+7.9195 ns**, 0 setup and 0 hold violations
  at 10 ns. The committed `control.gds` is byte-identical to the previous
  run (verified before the rewrite), so item 2 evidence is unchanged.
- `sdf/sram_ctrl.ss_n40C_1v28.sdf` — written by `klt sta` (`sdf: true`) on
  the **same** committed routed DEF (`sram_ctrl.def`) and SPEF
  (`sram_ctrl.spef`); `ss_n40C_1v28` is the worst-setup corner the P&R
  response reports (in-flow `setup_slack_ns` −7.6925). On the SPEF-fed STA
  session at 10 ns it reports worst slack **−8.90752 ns** with **78 setup
  violations** (0 hold).

Corners **run**: `tt_025C_1v80`, `ss_n40C_1v28`. Corners **not run**: the
other 14 corners of the P&R response's corner table (all `ff_*`, `ss_*`
except `ss_n40C_1v28`, and `tt_100C_1v80`), including the second-worst
setup corner `ss_n40C_1v35` (−1.93279 ns in-flow). No corner was chosen
because it passes: the worst-setup corner was run and its failure is
recorded below.

## Clock period

The placeholder **10 ns** period (#40, blocked on the ratified spec) is used
unchanged: the bench's own `Clock(dut.clk, 10, unit="ns")` drives it, and no
bench expectation, period or corner was modified for this record. Every
result here is tied to that period and to the committed routed netlist; a
re-route under #40 regenerates the SDFs and supersedes this evidence.

## Results (klt 0.9.0, Icarus 13.0, cocotb 2.1.0, `options.sdf.corner` `typ`, seed 20261120)

| Run | SDF corner | `environment.sdf` | Result |
|---|---|---|---|
| `item7-digital.json` (cited) | tt_025C_1v80 | `annotated: true`, entries `all`, partial | **pass, 5/5 tests** (`reset_state`, `write_read_walk`, `random_mix_vs_model`, `ce_ignored_while_busy`, `reset_mid_access`) |
| `item7-digital-ss-n40C-1v28.json` | ss_n40C_1v28 | `annotated: true`, entries `all`, partial | **fail, 1/5** — `reset_state` passes. Three tests fail on the assertion `ready must drop on acceptance` (`write_read_walk`, `ce_ignored_while_busy`, `reset_mid_access`; `rtl/tb/cocotb/test_sram_ctrl.py:53`) and one, `random_mix_vs_model`, on `ready must be back after the REST phase` (`:67`). Both assertions sample `ready` 1 ns after a clock edge (`:49`, `:66`); this record does not establish the cause (see below) |
| `item7-digital-unannotated.json` (control) | none | `null` | pass, 5/5 (grades `not_post_layout`) |

Both annotated runs are `partial: true` with two benign `dropped` classes,
`timingcheck` (81 — Icarus implements SDF delays but drops every
`TIMINGCHECK` section, so `$setup`/`$hold` checks run on the library's
placeholder timing) and `zero_delay_bus_port_source_interconnect` (40 —
entries whose every `min:typ:max` member is zero, removed because Icarus
cannot insert an intermodpath from a bit-selected top-level input port).
Neither class can change a simulated delay at any corner.

The ss failure is the measured outcome and no design fix is attempted here.
The cause of the assertion failures is not established by this record: the STA
result is a separate measurement, and the bench samples at 1 ns after the
edge in both assertions. The same STA session reports −8.91 ns worst slack and 78
setup violations at this period, so timing closure at `ss_n40C_1v28` (and
the second-worst `ss_n40C_1v35`) belongs to #40 once the clock target comes
from the spec. Note the grading asymmetry: Icarus models SDF delays but does
not propagate timing-check violations, so a *functional* pass understates
timing severity — `klt sta` remains the timing authority, and a functional
failure under annotation is the stronger signal.

## Upstream issues checked (issue #206 step 5)

- **[2AMLogic/klayout-tools#5002](https://github.com/2AMLogic/klayout-tools/issues/5002)** (`vvp` aborts in `vpi_scan` on a flat
  post-route SDF): **did not reproduce.** Both annotated runs completed with
  no `vvp` abort; this SDF is flat with plain instance names, and klt 0.9.0
  diagnoses mis-scoped SDF and normalizes the known-bad shapes before
  `vvp` runs (`options.sdf.scope: "dut"` matched the SDF's root `CELLTYPE`).
- **[2AMLogic/klayout-tools#5784](https://github.com/2AMLogic/klayout-tools/issues/5784)** (reports echo `options.sdf.file` as an
  absolute path): **bites.** `environment.sdf.file` in both annotated
  reports is the absolute host path of the SDF (the generated
  `$sdf_annotate` shim embeds it verbatim, so the echo is absolute by
  design). The reports are committed unedited; the manifest cites their
  `content_hash`, and everything needed to regenerate them is committed
  (requests, SDFs, bench, wrapper scripts).

## Supersession

This record, the SDFs and the three reports are tied to the committed
routed netlist and the 10 ns placeholder clock. When #40 re-runs
place-and-route against the ratified clock target, `layout/control/run_pnr.sh`,
`layout/control/sdf/run_sta_sdf.sh` and `layout/control/sdf/run_functional_sdf.sh`
regenerate all of it and the manifest citation is re-hashed in the same PR.
