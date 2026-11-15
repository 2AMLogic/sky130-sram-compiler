# Work Plan

Roadmap generated from the current GitHub label state by the Loom Guide role.
The region between the markers is machine-generated and overwritten wholesale;
do not edit it by hand.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

_None._

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#8**: Write spec/sram-compiler.md, inheritance table and ratification request

## Important

`loom:important`; taken before unlabelled work.

- **#40**: Follow-on from PR #39: sram_ctrl P&R timing closure (placeholder 10 ns clock, negative setup slack)

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#75**: design/bitcell/gen_schematic.py has no --check mode, so the generated bitcell_6t.sch has no regeneration gate
- **#80**: make_column_tb.py --check is not run by CI, so column bench/request drift is unguarded

## In Progress

Issues currently being built (`loom:building`).

- **#73**: README: bring the status line, Reproduce table and repo layout up to the tree
- **#74**: Narrow gen_layout.build()'s locals() return to the two fields callers actually use
- **#76**: Declare the write-trip LADDER length once: make_tb.py and record_common.py each define LADDER = 33
- **#78**: design/bitcell/lvs/run_lvs.sh computes an expected-status table it never checks: a desynced negative control reports match and exits 0
- **#82**: Remove two unused imports: point_key in make_controls_record.py (free) and math in sram_compile.py (needs an item 1+2 re-attestation)

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#90**: chore: drop unused point_key import from make_controls_record.py
- **#96**: fix(lvs): gate bitcell LVS on its expected-status table, derive the control width from sizing.json

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#77**: docs: add the nine missing Reproduce rows and resync the status line and repo layout
- **#87**: refactor(sim): declare the write-trip ladder length once and reject a wrong-length ladder loudly
- **#92**: refactor(compiler): name build()'s geometry return instead of locals()

## Proposed

Issues carrying `loom:curated`.

- **#8**: Write spec/sram-compiler.md, inheritance table and ratification request *(curated)*
- **#29**: T1 item 9 (testbenches shipped): array access/write benches, control cocotb bench and --attest 9 *(curated)*
- **#67**: bitcell GDS is not byte-reproducible: gen_bitcell.py writes klayout timestamps into the GDS header *(curated)*
- **#73**: README: bring the status line, Reproduce table and repo layout up to the tree *(curated)*
- **#74**: Narrow gen_layout.build()'s locals() return to the two fields callers actually use *(curated)*
- **#80**: make_column_tb.py --check is not run by CI, so column bench/request drift is unguarded *(curated)*

## Proposed (Architect / Hermit)

- **#89**: Remove the unused PROCESS/TEMPS/VDDS imports in both testbench generators, and the stale noqa: F401 hiding them *(hermit)*
- **#93**: Remove five more unused names the pyflakes pass finds: POLY_DIFF, NW_P, gen_erc_spec's gl, allw, an empty f-string *(hermit)*
- **#94**: Marker run_checks.sh: three-deck loop duplicates run_drc.sh, klt stderr discarded, and the README's control is never asserted *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 1 |
| Ready (`loom:issue`) | 2 |
| In Progress (`loom:building`) | 5 |
| PRs awaiting review | 2 |
| Approved PRs awaiting merge | 3 |
| Curated | 6 |
| Architect / Hermit proposals | 3 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
