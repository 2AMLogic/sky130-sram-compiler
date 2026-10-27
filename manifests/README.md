# Block manifest and tier-verdict record

This directory holds this block's `klt signoff` input and its committed
output: the machine-readable replacement for a hand-read gap-to-T1 checklist
([evidence tiers](https://github.com/2AMLogic/klayout-tools/blob/main/docs/design-evidence-tiers.md),
item 10).

## Files

- **`sky130-sram-compiler.json`** — the block manifest. `kind: mixed-signal`
  (analog bitcell and periphery, synthesized control logic). The `evidence`
  map is empty: no artifact is cited yet, so every item grades `unmet`. The
  `partition_boundary` entries are placeholders until the target spec
  ([#2](https://github.com/2AMLogic/sky130-sram-compiler/issues/2)) fixes
  what the two partitions cover. Evidence is added one item at a time, each
  citation pinning the `content_hash` of what it cites.
- **`design-evidence-tiers.md`** — the T1-T4 checklist the grader parses.
  Vendored **byte-identical** from
  [`2AMLogic/klayout-tools@44cc42323184`](https://github.com/2AMLogic/klayout-tools/blob/44cc42323184a2f3a440b89789bf174488a6b1e4/docs/design-evidence-tiers.md)
  (`docs/design-evidence-tiers.md`, 2026-10-17). Upstream is MIT-licensed;
  this repo's Apache-2.0 `LICENSE` does not relicense the vendored copy.
  When upstream moves, re-vendor the file, update the commit above, and
  regenerate the record in the same PR.
- **`sky130-sram-compiler.signoff.json`** — **the verdict of record**:
  committed output of the command below. Never hand-edit it.

## Regenerate

```console
pip install 'klayout-tools>=0.8.0'       # --attest (item 1 evidence) needs >= 0.8.0; the committed
                                        # record was rendered by a 0.8.1 dev build
klt signoff --manifest manifests/sky130-sram-compiler.json \
            --tiers-doc manifests/design-evidence-tiers.md \
            --format json > manifests/sky130-sram-compiler.signoff.json
```

`klt signoff --manifest` exits `3` when at least one T1 item is `unmet` (a
valid, clean run) and `0` when every item is `met`. Any change that affects
the verdict (new evidence, a manifest edit, a vendored-doc bump, a `klt` pin
bump) regenerates and commits the record in the same PR.

## Freshness is CI-enforced

[`.github/workflows/signoff.yml`](../.github/workflows/signoff.yml) pins
`klayout-tools==0.7.0`, runs the grader (exit 0 or 3 accepted, anything else
fails), then runs the same command with
`--check manifests/sky130-sram-compiler.signoff.json`. `--check` re-grades
and compares to the committed record, ignoring the `build` block (two
legitimate installs of one pin can differ there) instead of byte-comparing.
A manifest change without a regenerated record fails the build.

## Current verdict

**Not-T1: 0 of 22 rows met** (11 T1 items, rendered once per partition). No
evidence is cited; each row's `reason` is in the record.
