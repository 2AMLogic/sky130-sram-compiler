# Block manifest and tier-verdict record

This directory holds this block's `klt signoff` input and its committed
output: the machine-readable replacement for a hand-read gap-to-T1 checklist
([evidence tiers](https://github.com/2AMLogic/klayout-tools/blob/main/docs/design-evidence-tiers.md),
item 10).

## Files

- **`sky130-sram-compiler.json`** — the block manifest. `kind: mixed-signal`
  (analog bitcell and periphery, synthesized control logic). The `evidence`
  map cites 14 keys (`<item>.<partition>`, one key for a whole-block item), each pinning the `content_hash` of what it cites:
  - **1.analog / 1.digital** — `design/compiler/evidence/item1.json` (from `design/compiler/inventory.json`) and
    `evidence/item1-digital.json` (from `rtl/inventory.json`), both `klt signoff --attest 1`. The analog inventory's
    `sources` includes the shared `design/sky130_pdk.py` (the layer table and PDK drawing rules all four generators
    import), so a change to it makes this row `stale_evidence` rather than silently leaving the `.sch`/`.spice` it
    determines unattested. **Item 1 is the one item whose `content_hash` is not its inventory's own sha256**: under the
    pinned klt 0.9.0 `--attest 1` binds the *whole input set* — every source, every `derived` file and the inventory —
    through `provenance.input.paths`, and the hash to cite here is that set's combined digest
    (`provenance.input.content_hash`, 33 members for the analog partition), which is what makes editing any member
    grade the row stale. The analog envelope is `design/compiler/evidence/item1.json` (52/52 checks under
    klt 0.9.0), and it binds the shared PDK module; `evidence/item1-digital.json` does not bind it, so a
    change to it cannot grade the digital row stale. Items 9 and 10 bind their inventory
    alone, so for those the cited hash *is* the inventory's sha256. Item 2 pins an inventory too (below) but is
    anchored to its `--input` stream, so its cited hash is that stream's — never the inventory's or the envelope's.
  - **2.analog / 2.digital** — `design/compiler/evidence/item2.json` (the committed 256 x 32 GDS bound by hash, written by
    `klt signoff --attest 2 --input layout/sram_256x32_m4.gds --inventory design/compiler/item2-inventory.json`; the
    inventory declares the three `gen_layout.py` regeneration commands as `local_only` audit checks, so `--attest` runs
    them and `--attest --check` carries their committed outcome — command in `layout/README.md`) and
    `evidence/item2-digital.json` (the same command over `layout/control/control.gds` — the routed `sram_ctrl` stream
    `layout/control/run_pnr.sh` writes — with `--inventory layout/control/item2-inventory.json`, whose one `local_only`
    check is `run_pnr.sh --check`: it reruns the flow twice and requires both streams byte-identical to each other and
    to the committed GDS, with the response at the route stage, `power.pdn` true and a tapcell master).
  - **3.analog / 3.digital** — the unmodified `klt drc --deck sky130` envelopes `design/compiler/evidence/item3.json` and
    `evidence/item3-digital.json`, written by `verification/drc/make_record.py` (record in `verification/drc/records/`).
  - **4.analog / 4.digital** — the `klt lvs` envelopes `design/macro/evidence/lvs-sram_256x32_m4.json` and
    `design/control/evidence/lvs-sram_ctrl.json`, written by `design/macro/lvs/run_lvs.sh` and `design/control/lvs/run_lvs.sh`
    (`--report`).
  - **7.digital** — `evidence/item7-digital.json`, the `klt functional-verification` report of the SDF-annotated re-run of the routed
    control (`layout/control/sdf/run_functional_sdf.sh`; SDFs from `layout/control/run_pnr.sh`'s `post_route_sdf` and
    `layout/control/sdf/run_sta_sdf.sh`). Its `environment.sdf.annotated` is `true` (#206). The citation is an
    array of both annotated runs: that report (tt, 5/5) and `evidence/item7-digital-ss-n40C-1v28.json` (worst-setup corner,
    1/5, a recorded functional failure under annotated timing), so the item grades `unmet / check_failed` until timing closes (#40).
    `evidence/item7-digital-unannotated.json` (negative control — grades `not_post_layout`) is not cited; the
    dated record is `evidence/item7-digital-record-20261120.md`.
  - **9.analog / 9.digital** — `evidence/item9.json` (one envelope for both partitions), `klt signoff --attest 9` over
    `sim/testbench-inventory.json`.
  - **10** — `manifests/sky130-sram-compiler.item10.attest.json`, `klt signoff --attest 10` over `hygiene-inventory.json`
    (all partitions).
  - **11.analog / 11.digital** — the `klt erc` supply reports `layout/erc/erc_macro.json` and `layout/erc/erc_control.json`
    (written by `layout/erc/run_erc.sh --write`), each cited together with its LVS envelope above; the digital entry also
    cites `layout/control/place-and-route.response.json` (from `layout/control/run_pnr.sh`).

  Items 5, 6, 8 and item 7's analog row are the uncited ones and grade `unmet`; they need the ratified spec
  ([#2](https://github.com/2AMLogic/sky130-sram-compiler/issues/2)). `partition_boundary.digital` is set (like the analog
  one, #26): it declares `sram_ctrl` (`rtl/sram_ctrl.v`) and `sram_behav` (`rtl/sram_behav.v`) with their ports. Evidence is
  added one item at a time. A PR that adds or changes an `evidence` key updates this bullet in the same PR.
- **`design-evidence-tiers.md`** — the T1-T4 checklist the grader parses.
  Vendored **byte-identical** from
  [`2AMLogic/klayout-tools@44cc42323184`](https://github.com/2AMLogic/klayout-tools/blob/44cc42323184a2f3a440b89789bf174488a6b1e4/docs/design-evidence-tiers.md)
  (`docs/design-evidence-tiers.md`, 2026-10-17). Upstream is MIT-licensed;
  this repo's Apache-2.0 `LICENSE` does not relicense the vendored copy.
  When upstream moves, re-vendor the file, update the commit above, and
  regenerate the record in the same PR.
- **`hygiene-inventory.json`** / **`sky130-sram-compiler.item10.attest.json`** — the item 10
  (repo hygiene) inventory and its `klt signoff --attest 10` envelope; CI
  (`hygiene.yml`) re-checks it with `--check`. Regenerate with
  `uvx --from klayout-tools==0.8.0 klt signoff --attest 10 --inventory manifests/hygiene-inventory.json -o manifests/sky130-sram-compiler.item10.attest.json`,
  then update the `content_hash` cited in the manifest (the inventory's hash).
  The pin is `0.8.0` because that is what `hygiene.yml` installs to `--check`
  this envelope, so the recorded `provenance.klt_version` names the tool that
  validates it (mixed pins across evidence files are by design: `hygiene.yml`
  pins `klayout-tools==0.8.0` for this envelope while `signoff.yml` pins
  `klayout-tools==0.9.0` for the record — not a mandate to renormalise other
  envelopes).
- **`sky130-sram-compiler.signoff.json`** — **the verdict of record**:
  committed output of the command below. Never hand-edit it.

## Regenerate

```console
pip install klayout-tools==0.9.0        # or: uvx --from klayout-tools==0.9.0 klt ...
klt signoff --manifest manifests/sky130-sram-compiler.json \
            --tiers-doc manifests/design-evidence-tiers.md \
            --format json > manifests/sky130-sram-compiler.signoff.json
```

`klt signoff --manifest` exits `3` when at least one T1 item is `unmet` (a
valid, clean run) and `0` when every item is `met`. Any change that affects
the verdict (new evidence, a manifest edit, a vendored-doc bump, a `klt` pin
bump) regenerates and commits the record in the same PR.

Editing a file in `design/compiler/inventory.json`'s `sources` or `derived` makes
item 1 stale, so **re-attest before regenerating the record** — regenerating alone
turns CI green by recording a tier regression:

```console
klt signoff --attest 1 --inventory design/compiler/inventory.json \
            -o design/compiler/evidence/item1.json
# then copy provenance.input.content_hash into the manifest's 1.analog
# content_hash (the input-set digest, see the 1.analog bullet above) and
# regenerate the record with the command above.
```

`--attest 1` runs the inventory's freshness commands, so it needs `xschem`, the
sky130 PDK (`PDK_ROOT`, `PDK`) and — the trap — **the pinned `klt` as the default
`klt` on `PATH`**. `klt signoff --attest` deliberately removes its own tool venv's
`bin` from the `PATH` it hands those commands (so a bare `python3` is the repo's
interpreter), which also removes the pinned `klt` that `design/compiler/netlists.py`
shells out to: under `uvx`/pipx the freshness checks silently run against whatever
`klt` is installed host-wide, and every netlist reads as drifted if that differs
from the pin. Expose the pinned `klt` from a directory that is *not* the venv's
`bin` (a symlink dir early on `PATH` works) or install the pin as the default
`klt`. Filed upstream as 2AMLogic/klayout-tools#5620.

## Freshness is CI-enforced

[`.github/workflows/signoff.yml`](../.github/workflows/signoff.yml) pins
`klayout-tools==0.9.0`, runs the grader (exit 0 or 3 accepted, anything else
fails), then runs the same command with
`--check manifests/sky130-sram-compiler.signoff.json`. `--check` re-grades
and compares to the committed record, ignoring the `build` block (two
legitimate installs of one pin can differ there) instead of byte-comparing.
A manifest change without a regenerated record fails the build.

## Current verdict

**Not-T1: 14 of 22 rows met** (11 T1 items, rendered once per partition): T1 item 1,
Design sources, item 2, Layout, item 3, DRC clean, item 4, LVS clean, item 9, Testbenches shipped, item 10, Repo hygiene, and item 11, Power delivery (`layout/erc/`, #34), each for
the analog and the digital partition (issues #26, #27, #28, #29, #30, #31, #32, #33), while item 7, Post-layout verification, is `unmet / check_failed` for the digital partition: the SDF-annotated functional re-run of the routed control (#206) passes at `tt_025C_1v80` (`evidence/item7-digital.json`) and fails at the worst-setup corner `ss_n40C_1v28` (`evidence/item7-digital-ss-n40C-1v28.json`), and both are cited. Item 4 grades the
`status: match` reports with `power_connectivity: match` (`design/macro/records/`, `design/control/records/`,
klt 0.9.0 for the digital one). Item 9's envelope is `evidence/item9.json` (90/90 checks under klt 0.9.0, local cold start — grew from 76 with the PEX bench pair, #209); `git log -- evidence/item9.json` is its re-attestation history. The `klt` pin is
0.9.0, which contains the klayout-tools#4366 fix for the pwell `VNB` power-connectivity artifact. Each unmet row's `reason` is in the record.
