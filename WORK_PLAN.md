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

- **#8**: Write spec/sram-compiler.md, inheritance table and ratification request *(held)*

## Important

`loom:important`; taken before unlabelled work.

- **#40**: Follow-on from PR #39: sram_ctrl P&R timing closure (placeholder 10 ns clock, negative setup slack) *(held)*

## Ready

Human-approved issues ready for implementation (`loom:issue`).

_None._

## In Progress

Issues currently being built (`loom:building`).

- **#185**: Gate klt erc exit codes in run_erc.sh and validate reports before the --write copy
- **#186**: git_short_sha's untracked-file half of the dirty check can be silenced by a user git config

## PRs Awaiting Review

PRs waiting on Judge (`loom:review-requested`).

_None._

## Approved (Awaiting Merge)

PRs that passed review and are queued for Champion auto-merge (`loom:pr`).

- **#188**: fix: gate layout/erc klt erc exits and validate envelopes before the --write copy

## Proposed

Issues carrying `loom:curated`.

- **#8**: Write spec/sram-compiler.md, inheritance table and ratification request *(curated)* *(held)*
- **#29**: T1 item 9 (testbenches shipped): array access/write benches, control cocotb bench and --attest 9 *(curated)* *(held)*
- **#186**: git_short_sha's untracked-file half of the dirty check can be silenced by a user git config *(curated)*

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
| Ready (`loom:issue`) | 0 |
| In Progress (`loom:building`) | 2 |
| PRs awaiting review | 0 |
| Approved PRs awaiting merge | 1 |
| Curated | 3 |
| Architect / Hermit proposals | 0 |
| Active epics | 0 |
<!-- guide:plan-body:end -->
