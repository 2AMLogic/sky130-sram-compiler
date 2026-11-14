# Roadmap

An SRAM compiler on sky130 with a logic-rule 6T bitcell, built as a canary for
the tool surface underneath a memory compiler (see the [README](README.md)).

Status as of 2026-11-13, `main` @ `7d0e3fa`. [`WORK_PLAN.md`](WORK_PLAN.md) is
the generated snapshot of label state; the graded verdict is
[`manifests/sky130-sram-compiler.signoff.json`](manifests/sky130-sram-compiler.signoff.json),
never this file.

## Where it stands

Verdict of record: **not T1, 14 of 22 rows met** (11 T1 items, one row per
partition; block kind `mixed-signal`). All evidence is for the 256 x 32
reference instance (`sram_256x32_m4`, 64 rows x 128 columns) and its control
block `sram_ctrl`.

| T1 item | State | Evidence |
|---|---|---|
| 1 Design sources | met, both partitions | `design/compiler/evidence/item1.json`, `evidence/item1-digital.json` (#26, #27) |
| 2 Layout | met, both | `layout/sram_256x32_m4.gds` + LEF, `layout/control/control.gds` (#30, #31) |
| 3 DRC clean | met, both | `verification/drc/records/20261027-f91b6eb.md` (#32) |
| 4 LVS clean | met, both | `design/macro/records/`, `design/control/records/`, `power_connectivity: match` (#33) |
| 5 Corner verification vs a ratified spec | unmet | no ratified spec (#2, #8) |
| 6 Monte Carlo for statistical rows | unmet | bitcell MC exists (`sim/bitcell/records/`) but grades against no spec |
| 7 Post-layout verification | unmet | no extracted-netlist run |
| 8 Characterization report | unmet | follows 5 to 7 |
| 9 Testbenches shipped | met, both | `evidence/item9.json` over `sim/testbench-inventory.json` (#29 part 1, #51) |
| 10 Repo hygiene | met | `manifests/sky130-sram-compiler.item10.attest.json` (#28) |
| 11 Power delivery | met, both | `layout/erc/` with severed-rail controls (#34) |

Also in tree, ahead of the spec: the SRAM-marker deck study
(`verification/marker/`, #6); the bitcell with DRC, LVS, PVT corners and an
n=60 write-trip Monte Carlo with determinism and negative controls plus a
`klt yield` report (`design/bitcell/`, `sim/bitcell/records/`, #7, #14, #19);
column benches and a cocotb control bench that run locally at one corner
(`sim/column/`, `rtl/tb/cocotb/`).

What is **not** there: `spec/` holds one decision record and no spec, so the
README's maturity ladder still reads "pre-spec" although first-instance
DRC/LVS evidence exists provisionally. Tracker issue #5 still shows its
2026-10-17 table and is superseded by the signoff record.

## Now

Startable today; none depends on the ratified spec.

1. **Reconcile the draft spec in PR #12 with the landed evidence** (#8).
   The PR (`spec/sram-compiler.md`, three decision records, `reuse.lock.json`)
   has carried `loom:changes-requested` since 2026-10-22 and now conflicts with
   `main`. Done when: the branch is rebased or superseded, the #6/#7 findings
   are folded in with their stated limits, the SNM-extractor pin and the
   write-pulse contract each have a decision record, and the PR is back at
   `loom:review-requested`. This is drafting; ratification stays with the
   reviewers and the operator (see Blocked).
2. **Regenerate the six over-limit column requests.** `col_read_snm` and
   `col_hold_snm` set `batch.max_units_per_job` 15 and the four `col_mc_*`
   requests set 36 at `options.timeout_s` 300; a klt 0.8.0 client refused 15 as
   over the 11-unit limit (builder note on #29). `sim/column/README.md` "Fleet
   notes" still names a 0.7.0 client. Done when: `make_column_tb.py --check`
   passes with every request at or under the limit, the note is corrected, and
   item 9 is re-attested. No issue yet (seed 1); first step of #29.
3. **Move the item 2 analog envelope to `klt signoff --attest 2`.**
   `design/compiler/attest_layout.py` exists only because the producer was
   missing (klayout-tools#4221, now closed); klt 0.9.0, the pin in
   `signoff.yml`, has `--attest 2`. Done when: `design/compiler/evidence/item2.json`
   is written by klt, the manifest and signoff record are regenerated, and the
   workaround script and its README mentions are removed. No issue yet (seed 2).
4. **Bring the README status and Reproduce table up to the tree.** The status
   line still says the tree holds "the bitcell and a compiled 256 x 32
   netlist"; the Reproduce table has no row for the layout, macro DRC, LVS,
   ERC, column-bench or cocotb records; the layout lines for `verification/`
   and `layout/` do not match their contents. Done when: those three are
   corrected and item 10 is re-attested (the README is in
   `manifests/hygiene-inventory.json`). No issue yet (seed 3).

## Next

- **Run the 11 column grids and commit the records** (#29, remaining scope).
  Done when `sim/column/corners/` and `sim/column/records/` hold a report and
  a dated record per bench, negative controls included. Unblocked by Now 2
  and a client version the batch runner accepts; tool gap
  klayout-tools#4675 (open).
- **Close item 5 and item 6 for the bitcell and column rows.** Done when the
  signoff record grades both `met`. Blocked on the ratified spec (#8): a
  corner verdict against a draft is provisional.
- **Control-block timing** (#40). Place-and-route used a placeholder 10 ns
  clock and reports negative setup slack at two low-voltage `ss` corners
  (`layout/control/place-and-route.response.json`). Done when the clock target
  comes from the spec, `layout/control/run_pnr.sh` is re-run, and the corners
  in question are either in the ratified PVT set and closed or recorded as
  outside it. Blocked on #8.
- **Post-layout verification** (item 7). Done when the column benches re-run
  on a `klt pex` netlist of the macro and the record sits beside the
  pre-layout one. `sim/column/README.md` lists wire parasitics as not
  modelled. Unblocked by the pre-layout grids (#29) and the spec.
- **Characterization report** (item 8). Done when one aggregated report is cited in the manifest; follows items 5 to 7.
- **Second reference instance, 64 x 32.** Done when GDS, LEF, DRC and LVS
  records exist for it from the same compiler path. Blocked on the
  legal-combinations decision record in PR #12, which fixes its mux.

## Later

- **1024 x 32 and the row limit.** `gen_layout.py` refuses more than 64 rows,
  and 1024 words needs at least 128. Question first: is the limit the decoder
  lane scheme, the tap-strap plan, or only untested?
- **Liberty and behavioural-model views per instance.** Question first: can
  timing arcs be generated from the column benches and control timing without
  per-instance hand work (open question in #2)?
- **Compiler-range claim.** Question first: what evidence does the spec
  require for sizes other than the reference instances (#2)?
- **1RW1R (stretch)** and the last two ladder rungs: after the views exist.

## Blocked and waiting

- **Spec ratification** (#8, `loom:operator`; tracker #2). Two reviews, then
  the operator. Gates items 5 to 8, #40 and every instance beyond 256 x 32.
  Agents draft (Now 1) and do not ratify.
- **Column grids** (#29, `loom:blocked`): runner/client version handling in
  `klt sim` batch, klayout-tools#4675, open as read today.
- **Tracker state today:** no issue carries `loom:issue`. Now 1 is drawable
  only as review-fix work on PR #12; Now 2 to 4 need their issues filed.

## Not planned

- Competing with OpenRAM or reusing its cells; the foundry SRAM bitcell is a comparison case only.
- A relaxed-rule region or an `areaid.ce` marker in the macro.
- Redesigning the margin definitions or the Monte Carlo method (taken from `gf180-sram` by pinned reference).
- Relaxing a spec row to make a result pass, or hand-written `ngspice` loops.
