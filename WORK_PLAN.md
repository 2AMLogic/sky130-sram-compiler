# Work Plan

Roadmap generated from the current GitHub label state by the Loom Guide role.
The region between the markers is machine-generated and overwritten wholesale;
do not edit it by hand.

<!-- guide:plan-body:start -->
## Operator Attention: Merge-Risk-Hold Pileup

Judge-approved PRs under a hold (`loom:blocked` or `loom:operator`) — only a human merge decision is missing.

- **#146**: chore(loom): resync installed Loom to v0.19.1302

## Very Important

`loom:very-important` (one counts per workspace); every stage takes these first.

- **#8**: Write spec/sram-compiler.md, inheritance table and ratification request

## Important

`loom:important`; taken before unlabelled work.

- **#40**: Follow-on from PR #39: sram_ctrl P&R timing closure (placeholder 10 ns clock, negative setup slack)

## Ready

Human-approved issues ready for implementation (`loom:issue`).

- **#129**: Record writers interleave scratch-report reads with evidence writes, so a bad report orphans the earlier gzips
- **#155**: Use save_gz_json in make_column_record.py instead of an inline gzip writer

## In Progress

Issues currently being built (`loom:building`).

- **#145**: verification/hygiene/test_pdk_resolution.py is a fifth PDK-free suite that #88's ACs do not enumerate (and its docstring names the wrong unwired precedent)
- **#151**: A record can be stamped with a commit that cannot reproduce it: git_short_sha never checks the tree is clean
- **#159**: check_reproduce_coverage.py: git ls-files enumeration mangles paths containing whitespace

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

- **#164**: test: wire the PDK-resolution suite into hygiene CI and re-attest item 10

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#146**: chore(loom): resync installed Loom to v0.19.1302

## Proposed

Issues carrying `loom:curated`.

- **#8**: Write spec/sram-compiler.md, inheritance table and ratification request *(curated)*
- **#29**: T1 item 9 (testbenches shipped): array access/write benches, control cocotb bench and --attest 9 *(curated)*
- **#129**: Record writers interleave scratch-report reads with evidence writes, so a bad report orphans the earlier gzips *(curated)*
- **#145**: verification/hygiene/test_pdk_resolution.py is a fifth PDK-free suite that #88's ACs do not enumerate (and its docstring names the wrong unwired precedent) *(curated)*
- **#151**: A record can be stamped with a commit that cannot reproduce it: git_short_sha never checks the tree is clean *(curated)*
- **#159**: check_reproduce_coverage.py: git ls-files enumeration mangles paths containing whitespace *(curated)*

## Proposed (Architect / Hermit)

_None._

## Epics

_None._

## Backlog Balance

| Bucket | Count |
|------|-------|
| Operator merge-risk holds | 1 |
| Very important | 1 |
| Important | 1 |
| Ready (`loom:issue`) | 2 |
| In Progress (`loom:building`) | 3 |
| PRs awaiting review | 1 |
| Approved PRs awaiting merge | 1 |
| Curated | 6 |
| Architect / Hermit proposals | 0 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
