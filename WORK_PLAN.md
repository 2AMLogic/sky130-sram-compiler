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
- **#71**: Regenerate the six over-limit sim/column batch requests and correct the stale fleet note
- **#72**: Produce the T1 item 2 analog envelope with `klt signoff --attest 2` and retire attest_layout.py

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#72**: Produce the T1 item 2 analog envelope with `klt signoff --attest 2` and retire attest_layout.py
- **#74**: Narrow gen_layout.build()'s locals() return to the two fields callers actually use
- **#75**: design/bitcell/gen_schematic.py has no --check mode, so the generated bitcell_6t.sch has no regeneration gate
- **#76**: Declare the write-trip LADDER length once: make_tb.py and record_common.py each define LADDER = 33
- **#78**: design/bitcell/lvs/run_lvs.sh computes an expected-status table it never checks: a desynced negative control reports match and exits 0
- **#82**: Remove two unused imports: point_key in make_controls_record.py (free) and math in sram_compile.py (needs an item 1+2 re-attestation)

## In Progress

Issues currently being built (`loom:building`).

- **#71**: Regenerate the six over-limit sim/column batch requests and correct the stale fleet note
- **#73**: README: bring the status line, Reproduce table and repo layout up to the tree

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#77**: docs: add the nine missing Reproduce rows and resync the status line and repo layout
- **#81**: fix: derive sim/column batch unit caps from timeout_s and bound shard concurrency

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

_None._

## Proposed

Issues carrying `loom:curated`.

- **#8**: Write spec/sram-compiler.md, inheritance table and ratification request *(curated)*
- **#29**: T1 item 9 (testbenches shipped): array access/write benches, control cocotb bench and --attest 9 *(curated)*
- **#67**: bitcell GDS is not byte-reproducible: gen_bitcell.py writes klayout timestamps into the GDS header *(curated)*
- **#71**: Regenerate the six over-limit sim/column batch requests and correct the stale fleet note *(curated)*
- **#72**: Produce the T1 item 2 analog envelope with `klt signoff --attest 2` and retire attest_layout.py *(curated)*
- **#73**: README: bring the status line, Reproduce table and repo layout up to the tree *(curated)*
- **#74**: Narrow gen_layout.build()'s locals() return to the two fields callers actually use *(curated)*

## Proposed (Architect / Hermit)

- **#69**: Remove the dead init_drivers() helper and the ignored cells_hs parameter from the column testbench generator *(hermit)*

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 3 |
| Ready (`loom:issue`) | 6 |
| In Progress (`loom:building`) | 2 |
| PRs awaiting review | 2 |
| Approved PRs awaiting merge | 0 |
| Curated | 7 |
| Architect / Hermit proposals | 1 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
