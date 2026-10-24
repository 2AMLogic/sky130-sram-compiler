# sky130-sram-compiler

An SRAM compiler on [SkyWater sky130](https://github.com/google/skywater-pdk),
the 130 nm open PDK — a generator that turns a word count and a bit width
into a DRC/LVS-clean macro with its abstract and timing views, built on a
6T bitcell drawn to logic design rules — designed by AI agents driving
[klayout-tools](https://github.com/2AMLogic/klayout-tools), xschem + ngspice
for the bitcell and periphery, and Yosys/OpenROAD for the control logic.

**Status: just opened, specification phase.** Nothing is designed yet.

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
