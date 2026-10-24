# 0003: Sim harness — adopt `gf180-sram`'s by pinned reference; sky130 binding layer written here

**Status**: Proposed, pending ratification of `spec/sram-compiler.md`.
**Settles**: the harness adopt-or-record decision that #4 defers to #8.

## Decision

Adopt, by pinned reference, `gf180-sram`'s harness at commit
`74ba8a621c9edab9b7a75ecb19ca7ea6771588da`: `sim/lib/run_corner_sweep.sh`,
`sim/lib/run_mc_campaign.py`, `sim/lib/snm_extract.py`,
`sim/lib/mint_sim_envelope.py`, `sim/lib/env_provenance.py`,
`sim/lib/render_signoff_table.py` and `sim/lib/pdk_env.sh`. They are listed in
`reuse.lock.json` as `fetched`, with the sha256 of each at that commit.

The record formats (append-only record tree, envelope fields, signoff table)
are taken unchanged. A change to a record format is made in `gf180-sram`, the
master, not diverged here.

## What this does not decide

The scripts read the gf180 PDK in several places. Reading their headers, three
bind to it: `pdk_env.sh` (the `GF180_*` resolver), `run_corner_sweep.sh` (the
3 × 3 × 3 axes and gf180 `.lib` section names) and `run_mc_campaign.py` (the
gf180 mismatch switch). This record does not claim to have audited every line
of the others.

So the sky130 binding is a layer to be written, not a fork of the master:
the sky130 PDK resolver (#4), the 45-corner axes and `.lib` sections from
decision `0001`, and the sky130 mismatch mechanism. Whether sky130's models
expose an equivalent per-instance mismatch switch is `TBD-measured` and is
settled at harness bring-up in #4.

If the binding cannot be a thin layer over the pinned scripts, the outcome is
a vendored copy under `sim/harness/common/` with a recorded divergence
(`"diverged"` in `reuse.lock.json`) and a finding filed on `gf180-sram`. Making
the PDK parameters of the master scripts configurable is gf180-sram's change to
make; this repo asks for it there rather than editing a copy.

## Why adopt rather than record a separate harness

`REUSE.md` (`2AMLogic/2am`) names the sim harness mechanics as PDK-independent
material with one master, and the fleet audit found harness copies that
drifted apart with no upstream. Designing a second harness here would repeat
that. The record formats are what downstream tools read, so they must not
vary by PDK.

## Not adopted

Execution runs on this repo's own host rules: multi-corner and Monte Carlo
requests go through `klt sim` to the batch fleet, not through a locally
launched copy of `run_corner_sweep.sh` looping over ngspice. The pinned
scripts are the reference for what a record contains, not the launcher on the
dispatch host.
