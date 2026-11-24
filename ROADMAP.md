# Roadmap

An SRAM compiler on sky130 with a logic-rule 6T bitcell, built as a canary for
the tool surface underneath a memory compiler (see the [README](README.md)).

Status as of 2026-11-20, `main` @ `c7f09e2`. [`WORK_PLAN.md`](WORK_PLAN.md) is
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
| 7 Post-layout verification (analog) | unmet | no extracted-netlist run |
| 7 Post-layout verification (digital) | unmet (`check_failed`) | SDF-annotated cocotb re-run on the routed netlist: passes 5/5 at `tt_025C_1v80` (`evidence/item7-digital.json`), fails 4 of 5 at the worst-setup corner `ss_n40C_1v28` (`evidence/item7-digital-ss-n40C-1v28.json`); both cited, so the row grades unmet (#206; closure with #40) |
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
   item 9 is re-attested. Filed as #71; first step of #29.
3. **Bring the README status and Reproduce table up to the tree.** The status
   line still says the tree holds "the bitcell and a compiled 256 x 32
   netlist"; the Reproduce table has no row for the layout, macro DRC, LVS,
   ERC, column-bench or cocotb records; the layout lines for `verification/`
   and `layout/` do not match their contents. Done when: those three are
   corrected and item 10 is re-attested (the README is in
   `manifests/hygiene-inventory.json`). Filed as #73.

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
- **Post-layout verification** (item 7). The legs are separate. *Digital*:
  measured, not met — the cocotb bench re-ran on the routed netlist with
  post-route SDF timing at `tt_025C_1v80` (pass) and at the worst-setup corner
  `ss_n40C_1v28` (fails functionally, 1/5 pass); both reports are cited, so
  the row grades `unmet / check_failed`; closure stays with #40;
  `evidence/item7-digital*.json`, `layout/control/sdf/` (#206). Tied to the
  10 ns placeholder clock: a re-route under #40 supersedes it. *Analog*: extract-only
  capacity measured (#208) — the signoff pin `klayout-tools==0.9.0` extracts the bare
  bitcell (3.3 s, 119 MiB peak) and the full 8,192-cell macro (93.6 min, 6.2 GiB peak,
  51,226 devices / 17,259 nets) with clean exit-4 extract-only reports, and body bias
  read from the extractions: klt reports no unbiased PMOS bodies in either (that status is
  PMOS-only); macro nfet bulks are all on the drawn VSS taps, while the bare cell's 4 nfet
  bulks sit on the exported `vsubs` pin, which a consuming bench must bias itself — record
  `sim/column/records/20261121-3c2d73b.md`. The provisional one-corner comparison landed
  (#209): the column benches re-ran on an LVS-matched bench slice (4 columns + periphery,
  DRC-clean, 543/543 nets and 1575/1575 devices by LVS with a biting negative control,
  `layout/sram_col_slice.gds`) against the flat generated schematic DUT — both legs
  simulated, every ladder and the WEN-off control held on each side, and the write
  completion transition moved from a 0.35–0.40 ns to a 0.45–0.50 ns bounding pulse width
  at tt/1.8 V/25 °C (read access unshifted at the 50 ps ladder resolution; sense
  differential −5 %) — record `sim/column/records/20261123-69ff7430.md`. Remaining
  simulation work: the post-layout corner grids and Monte Carlo on the extracted slice
  (the pre-layout grids are the committed `klt sim` requests); item 7 stays uncited.
  The DC SNM fixture's
  layout top now exists (#228): `gen_layout.py --snm-halfcell`, a 64-row column with a decoupled
  half-cell in row 0, DRC/LVS clean, extract-only accepted in 1 s; it measures nothing —
  the extracted hold/read SNM is #210; record `design/macro/records/20261124-snm-halfcell-col64.md`.
  Unblocked by the pre-layout grids (#29) and the spec.
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
- **Tracker state today:** Now 1 is drawable only as review-fix work on
  PR #12; Now 2 and 3 are filed as #71 and #73.

## Not planned

- Competing with OpenRAM or reusing its cells; the foundry SRAM bitcell is a comparison case only.
- A relaxed-rule region or an `areaid.ce` marker in the macro.
- Redesigning the margin definitions or the Monte Carlo method (taken from `gf180-sram` by pinned reference).
- Relaxing a spec row to make a result pass, or hand-written `ngspice` loops.
