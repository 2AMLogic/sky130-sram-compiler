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

- **#99**: Bitcell LVS negative-control anchor corrupts the control netlist for integer-valued ax.w (regex built from an unescaped :g-formatted float)
- **#104**: Fold the repeated gzip-JSON write and sha256 helpers into record_common

## In Progress

Issues currently being built (`loom:building`).

- **#67**: bitcell GDS is not byte-reproducible: gen_bitcell.py writes klayout timestamps into the GDS header
- **#88**: Wire the PDK-free test suites into the hygiene CI inventory (needs an item-10 re-attestation)
- **#91**: Write-MC record prose hardcodes the ladder step (/32) while the data now derives from tb_common.LADDER
- **#105**: No test asserts any generator's --check actually exits non-zero on drift
- **#108**: Marker study: counts have drifted from the 2026-10-17 record on the current klt pin — new dated record needed
- **#116**: Consolidate the duplicated provenance guard in verification/drc and guard design/bitcell make_record
- **#119**: T1 item 9 grades analog 'met' while sim/testbench-inventory.json omits every bitcell testbench but one

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#110**: fix: derive the write-trip ladder prose in the record generators from tb_common.LADDER
- **#123**: docs(marker): add 2026-11-15 re-run record with per-deck drift attribution

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#121**: refactor: consolidate record provenance lookups onto record_common

## Proposed

Issues carrying `loom:curated`.

- **#8**: Write spec/sram-compiler.md, inheritance table and ratification request *(curated)*
- **#29**: T1 item 9 (testbenches shipped): array access/write benches, control cocotb bench and --attest 9 *(curated)*
- **#67**: bitcell GDS is not byte-reproducible: gen_bitcell.py writes klayout timestamps into the GDS header *(curated)*
- **#88**: Wire the PDK-free test suites into the hygiene CI inventory (needs an item-10 re-attestation) *(curated)*
- **#91**: Write-MC record prose hardcodes the ladder step (/32) while the data now derives from tb_common.LADDER *(curated)*
- **#95**: make_record.py bakes a failed DRC/LVS compare into an append-only record: check the runners' returncodes *(curated)*
- **#99**: Bitcell LVS negative-control anchor corrupts the control netlist for integer-valued ax.w (regex built from an unescaped :g-formatted float) *(curated)*
- **#104**: Fold the repeated gzip-JSON write and sha256 helpers into record_common *(curated)*
- **#105**: No test asserts any generator's --check actually exits non-zero on drift *(curated)*
- **#108**: Marker study: counts have drifted from the 2026-10-17 record on the current klt pin — new dated record needed *(curated)*
- **#114**: make_column_record.py writes evidence before resolving the sha, so a provenance failure leaves orphaned gzips (needs item-9 re-attestation) *(curated)*
- **#119**: T1 item 9 grades analog 'met' while sim/testbench-inventory.json omits every bitcell testbench but one *(curated)*

## Proposed (Architect / Hermit)

_None._

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 0 |
| Very important | 1 |
| Important | 1 |
| Ready (`loom:issue`) | 2 |
| In Progress (`loom:building`) | 7 |
| PRs awaiting review | 2 |
| Approved PRs awaiting merge | 1 |
| Curated | 12 |
| Architect / Hermit proposals | 0 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
