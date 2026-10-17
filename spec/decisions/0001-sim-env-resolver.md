# 0001: sim environment resolver and gf180-sram harness reuse

Status: recorded (issue #4). Not a spec change.

## Context

`gf180-sram` is master for the margin definitions, corner and Monte Carlo
methodology and the sim harness (`sim/lib/pdk_env.sh`, `run_corner_sweep.sh`,
`env_provenance.py`, `mint_sim_envelope.py`). Its `pdk_env.sh` is gf180-specific
(`GF180_*` variables, `sm141064.ngspice`, `design.ngspice`). Whether to adopt
that harness is decided in #2 ("Inherit from `gf180-sram`").

## Decision

- Adopt-or-record for the harness itself: **deferred to #2**, unchanged here.
  No `reuse.lock.json` entry is written, since nothing is pinned or taken yet.
- For toolchain bring-up, `sim/env.sh` is a local sky130 PDK resolver written
  from `gf180-sram`'s resolution order and variable naming (read at
  `gf180-sram` main `d0bacc0`, 2026-10-17). It is not a copy.
- Records identify the PDK by variant and open_pdks revision only, matching the
  identity-not-location rule in `env_provenance.py`.

## Replacement contract

When #2 adopts the harness, `sim/env.sh` may be replaced by a sky130 port of
`pdk_env.sh` provided it keeps: the `sim/pdk.json` pin check with a named
`PDK_REVISION_MISMATCH` refusal, the exported `*_VARIANT_DIR`, `*_MODEL_FILE`
and `*_PDK_VERSION` variables, and the smoke record fields (simulator version,
PDK revision, deck hash).
