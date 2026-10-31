# sky130-sram-compiler

An SRAM compiler on [SkyWater sky130](https://github.com/google/skywater-pdk),
the 130 nm open PDK — a generator that turns a word count and a bit width
into a DRC/LVS-clean macro with its abstract and timing views, built on a
6T bitcell drawn to logic design rules — designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools), xschem + ngspice
for the bitcell and periphery, and Yosys/OpenROAD for the control logic.

**Status: specification phase, with the bitcell and a compiled 256 × 32 netlist
in tree.** Nothing here is silicon-proven; the spec below is still a draft.

**T1 status.** The evidence-tier verdict is graded by `klt signoff`, not
hand-read. The verdict of record is
[`manifests/sky130-sram-compiler.signoff.json`](manifests/sky130-sram-compiler.signoff.json);
see [`manifests/README.md`](manifests/README.md) for how it is regenerated and
how CI keeps it fresh.

**Built agent-native.** Every specification, decision record, testbench, and
line of documentation here is produced by AI agents working from a ratified
spec and an append-only evidence trail — not human-authored work that agents
merely assisted with. Verification is the product: every claim traces to a
recorded result under PVT corners. Where the agents hit friction with the
open-source tooling — most often
[klayout-tools](https://github.com/2AMLogic/klayout-tools) — that friction is
filed as a public issue against the tool itself, so the fix benefits everyone
using sky130, not just this repo.

## Why this block, stated honestly

Free SRAM macros for sky130 already exist: [OpenRAM](https://openram.org)
generates them, on the foundry's SRAM bitcells. Those bitcells are drawn to
relaxed SRAM rules that are legal only inside the PDK's SRAM core-area
marker, so a DRC deck has to switch rule sets at that marker boundary. This
repo is not trying to out-compete OpenRAM; it is a canary for the tool
surface underneath a compiler, and it makes two deliberate choices:

- **A logic-rule bitcell.** The bitcell is drawn to the ordinary logic rules,
  so the macro needs no relaxed-rule region of its own. That costs area, and
  the spec has to say how much.
- **Marker-layer rule switching as a test target.** Whether the deck applies
  the right rule set inside and outside the SRAM marker, and at the edge
  between them, is checked directly — against the foundry cell as a
  comparison case, and at the seam where periphery meets array.

The third stress is **pitch-matched periphery**: row decoders, wordline
drivers, column mux, sense amplifiers and write drivers drawn to the bitcell
pitch, generated for every size the compiler accepts. A fixed macro proves
one layout; a compiler has to prove a family.

Where OpenRAM's output is a useful reference or comparison, use it and say
so. Do not reimplement it.

## Relation to the other SRAM canaries

`gf180-sram` (a fixed 256 × 32 macro on gf180mcu, simulation-validated) and
`sg13g2-sram` (its port) are the fleet's other SRAM blocks. They are other
PDKs, so the device-level design here is new. Their PDK-independent half —
the margin definitions (read SNM, hold SNM, write margin), the corner and
Monte Carlo methodology, and the harness — has one master, `gf180-sram`, and
is taken from there by pinned reference rather than redesigned.

## Target specification (DRAFT — EE-key and market-key reviews first, then operator ratification; see issue #8)

All figures are targets.

| Parameter | Target | Fallback | Stretch |
|---|---|---|---|
| Bitcell | 6T, logic design rules only | — | — |
| Ports | 1RW, synchronous | — | 1RW1R |
| Compiler range | words 16–1024, bits 8–64, column mux 1/2/4/8 | single fixed 256 × 32 instance through the compiler path | words to 4096 |
| Reference instances | 64 × 32, 256 × 32, 1024 × 32 all DRC/LVS-clean | 256 × 32 | — |
| Supply | 1.8 V ±10% | — | — |
| Margins | read SNM, hold SNM, write margin strictly positive at every corner, with Monte Carlo | — | — |
| Views per instance | GDS, LEF, Liberty, Verilog behavioural model | GDS, LEF | — |

Maturity ladder: spec ratified → bitcell characterized across PVT →
periphery characterized → first instance DRC/LVS-clean → reference
instances DRC/LVS-clean → views generated and checked → shuttle seat →
measured silicon. **Current position: pre-spec.**

## Reproduce

Every committed result is append-only evidence; each command below either
regenerates it into a new dated record or checks that the committed bytes still
match their generator. Per-directory READMEs hold the detail.

**PDK-free (run by CI, [`hygiene.yml`](.github/workflows/hygiene.yml)).**
Needs only `python3` and `git`; the last line also needs `pip install klayout-tools==0.8.0`.

```bash
python3 -I verification/hygiene/check_formats.py          # JSON parses, Python compiles
python3 -I design/compiler/test_compiler.py               # compiler generator tests
python3 -I design/compiler/gen_schematic.py --check       # periphery schematics vs generator
python3 -I design/compiler/sram_compile.py 256 32 4 --check design/compiler/macro/sram_256x32_m4.spice
python3 -I sim/bitcell/lib/make_tb.py --check             # bitcell testbenches + klt sim requests
klt signoff --attest 10 --inventory manifests/hygiene-inventory.json \
    --check manifests/sky130-sram-compiler.item10.attest.json   # this section's own attestation
```

**Needs the PDK and/or simulators** (sky130A at the revision pinned in
[`sim/pdk.json`](sim/pdk.json), `ngspice`, `yosys`, `klt`, standalone `klayout`,
`xschem`). Not run in CI.

| Record | Command | Writes | Detail |
|---|---|---|---|
| Toolchain smoke (inverter, Yosys) | `source sim/env.sh && sim/smoke/run.sh` | `sim/smoke/records/` | [`sim/README.md`](sim/README.md) |
| SRAM-marker deck behaviour | `verification/marker/run_checks.sh <scratch>` | `verification/marker/records/` | [`verification/marker/README.md`](verification/marker/README.md) |
| Bitcell DRC (three decks) | `design/bitcell/run_drc.sh <gds> <scratch>` | `design/bitcell/records/` | [`design/bitcell/README.md`](design/bitcell/README.md) |
| Bitcell LVS + negative control | `design/bitcell/lvs/run_lvs.sh <gds> <scratch>` | `design/bitcell/records/` | [`design/bitcell/README.md`](design/bitcell/README.md) |
| Bitcell corners (read/hold SNM, write trip) and Monte Carlo | `klt sim` requests in `sim/bitcell/requests/` (batch fleet), then `snm_from_artifacts.py`, `make_record.py`, `make_write_mc_record.py`, `make_controls_record.py` | `sim/bitcell/corners/`, `sim/bitcell/records/` | [`sim/bitcell/README.md`](sim/bitcell/README.md) |
| Compiler netlists (periphery, 256 × 32 macro) | `design/compiler/` steps 1-3 (steps 1-2 need xschem + PDK) | `design/compiler/{cells,netlist,macro}/` | [`design/compiler/README.md`](design/compiler/README.md) |
| T1 item 1 attestation | `klt signoff --attest 1 --inventory design/compiler/inventory.json -o design/compiler/evidence/item1.json` | `design/compiler/evidence/` | [`manifests/README.md`](manifests/README.md) |

Multi-corner and Monte Carlo work goes through `klt sim` requests, never
hand-written `ngspice` loops.

## Repo layout

```
spec/          ratified spec + decision records
design/        bitcell and periphery schematics, compiler sources
rtl/           control logic + behavioural model
verification/  cocotb testbenches for control logic and the behavioural model
sim/           testbenches + PVT corner results (ngspice)
layout/        generated GDS + DRC/LVS reports per instance
measurements/  silicon characterization (empty until tape-out)
```

## License

Apache License 2.0 — see [LICENSE](LICENSE).
