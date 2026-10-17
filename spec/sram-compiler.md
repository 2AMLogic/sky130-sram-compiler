# Target spec: sky130 SRAM compiler

**Status**: DRAFT — not ratified. Ratification is an operator gate (issue #8,
step 6); this file is marked ratified only after the operator answers.
**Resolves**: #8 (child of #2)
**Replaces**: the DRAFT table in `README.md`

Agents build and verify against this spec once ratified. It is not relaxed to
make results pass: a change to any row needs a new decision record under
`spec/decisions/`, not an edit against a failing result.

Every parameter is **target / fallback / stretch** with a rationale. Anything
that depends on a measurement not yet made is written `TBD-measured` and names
the issue that will supply it. Nothing in this file is an estimate.

Inputs still open: #6 (how klt's sky130 deck treats the SRAM core-area
marker) and #7 (logic-rule 6T bitcell sizing and area against the foundry
cell). Fields they feed are marked `TBD-measured (#6)` / `TBD-measured (#7)`.

## 1. Bitcell

| | |
|---|---|
| Target | 6T, drawn to the sky130 logic design rules only |
| Fallback | none. A bitcell that needs the relaxed SRAM rules is the foundry-cell approach OpenRAM already provides, and is out of this block's purpose |
| Stretch | none |

Rationale: the logic-rule bitcell is the deliberate choice of this block
(README, "Why this block"). The cost is area against the foundry cell.

- Device sizing ratios (pull-down / access / pull-up): `TBD-measured (#7)`.
- Area against the foundry cell: `TBD-measured (#7)`. The spec states no area
  number until measured.
- Whether the logic-rule bitcell needs the SRAM core-area marker at all, and
  what the periphery-to-array seam must satisfy: `TBD-measured (#6)`.

## 2. Ports

| | |
|---|---|
| Target | 1RW, synchronous: one clock, one address bus, one read/write data path |
| Fallback | same as target |
| Stretch | 1RW1R: an independent read-only port |

Rationale: 1RW is the minimum useful macro and the smallest periphery. 1RW1R
needs a second wordline and bitline pair per cell (an 8T cell or a different
array), which changes the bitcell; it waits until the 1RW range closes.

**Pin interface (1RW)**, name and function. This is the one interface used by
the LEF, Liberty and behavioural model. OpenRAM's sky130 single-port macros
are the comparison point; whether their pin names and polarities match these
is `TBD-measured` (not yet checked), and any difference is recorded, not
silently adopted.

| Pin | Dir | Width | Function |
|---|---|---|---|
| `clk` | in | 1 | rising-edge clock; all inputs sampled on it |
| `csb` | in | 1 | chip select, active low |
| `web` | in | 1 | write enable, active low (low = write, high = read) |
| `wmask` | in | bits/8 | per-byte write mask, active high. `TBD-measured`: kept only if the write driver supports it at no area penalty in #7; otherwise dropped by decision record, not silently |
| `addr` | in | log2(words) | word address |
| `din` | in | bits | write data |
| `dout` | out | bits | read data, registered, valid after the access time |
| `vdd`, `vss` | power | 1 | single supply |

Read latency is one cycle (output registered at the next clock edge).
`TBD-measured`: whether `dout` holds or goes to a defined idle state when
`csb` is high — fixed in the behavioural model once the sense amp timing is
characterized.

## 3. Compiler range

Parameters: `words`, `bits`, `mux` (column mux ratio).

| | words | bits | column mux |
|---|---|---|---|
| Target | 16–1024 | 8–64 | 1, 2, 4, 8 |
| Fallback | 256 | 32 | 4 (single fixed instance through the compiler path) |
| Stretch | up to 4096 | as target | as target |

Rationale: the range matches the README draft. The fallback is the one
instance that closes first (CLAUDE.md: "the 256 × 32 instance through the
compiler path closes first"). A compiler proves a family, so the fallback
still runs through the same code path and is not a hand-drawn macro.

**Legality rules** (decision record `0002`):

1. `words` is a power of two.
2. `bits` is a multiple of 8, 8 to 64: `{8, 16, 24, 32, 40, 48, 56, 64}`.
3. `mux` is in `{1, 2, 4, 8}`.
4. Array rows `= words / mux` must be at least 8 (decoder floor).
5. Array columns `= bits × mux` must be at most 512.
6. Array rows above 256 are `TBD-measured (#7)`: the legal row limit is set by
   bitline length, which depends on the measured bitcell.

Legal-combination table, `words` against `mux`. `L` legal, `-` illegal (rule
4), `M` legal only if the row limit in rule 6 is measured to allow it. Rule 5
cannot fail inside the target range (`64 × 8 = 512`), so no cell is
`-` because of columns. Every `bits` value in rule 2 behaves identically
because no rule depends on `bits` below that bound.

| words \ mux | 1 | 2 | 4 | 8 |
|---|---|---|---|---|
| 16 | L | L | - | - |
| 32 | L | L | L | - |
| 64 | L | L | L | L |
| 128 | L | L | L | L |
| 256 | L | L | L | L |
| 512 | M | L | L | L |
| 1024 | M | M | L | L |

Stretch words 2048 and 4096 follow the same rules; every cell with rows above
256 is `M`. No cell is left undefined.

## 4. Reference instances

| | Instances |
|---|---|
| Target | 64 × 32, 256 × 32, 1024 × 32, all DRC/LVS-clean |
| Fallback | 256 × 32 only |
| Stretch | none beyond target |

Rationale: three instances a decade apart in words span the range and its
row-count scaling. 256 × 32 is the fallback and the first to close.

Fixed column mux for each reference instance (decision record `0002`):

| Instance | mux | Array (rows × cols) |
|---|---|---|
| 64 × 32 | 2 | 32 × 64 |
| 256 × 32 | 4 | 64 × 128 |
| 1024 × 32 | 8 | 128 × 256 |

Every row count is within 256, so rule 6 does not apply to them. Other mux
options of the same words/bits are exercised as range-claim instances (§10),
not reference instances.

## 5. Periphery

Each block is drawn pitch-matched to the bitcell and generated by the same
code path for every legal `(words, bits, mux)`. Pitch matching is where the
generator is expected to break; the legality rules above are the contract it
must hold.

| Block | Target | Fallback | Stretch |
|---|---|---|---|
| Row decoder | predecoded NAND/NOR tree, pitch-matched to the cell row pitch, generated for 3 to 10 address bits | fixed decoder for the 256-row case | n/a |
| Wordline driver | per-row driver, pitch-matched to the row pitch, sized by the row's column count | one fixed size | sized per instance from measured wordline load |
| Column mux | pass-gate mux 1/2/4/8, pitch-matched to the bit-column pitch | the 4:1 mux only | n/a |
| Sense amplifier | latched differential, one per output bit, enabled by the timing block | same | n/a |
| Write driver | one per input bit, drives the selected column pair | same | per-byte mask (`wmask`) |
| Timing / control | synthesized control logic (Yosys/OpenROAD) with a dummy-column replica path for sense enable | fixed delay chain | n/a |

Rationale: choices follow the standard single-port SRAM organization that
OpenRAM also uses; OpenRAM's sky130 output is the reference for comparison and
is not reimplemented. Sizing of every block is `TBD-measured`: it follows the
bitcell (#7) and is set when the periphery is characterized, not here.

Scaling: decoder depth grows with `log2(words/mux)`, wordline driver load
with `bits × mux`, bitline load with `words/mux`. These are the three axes a
fixed-size block cannot cover, so each is a generator parameter.

Where the periphery meets the array, the seam rules come from `#6` and are
`TBD-measured (#6)`.

## 6. Margins

Definitions, the pass rule and the statistical treatment are inherited from
`gf180-sram` by pinned reference and not re-decided (§9). Restated here so the
spec is self-contained; the pinned source governs on any difference.

| Quantity | Definition (from `gf180-sram` `spec/sram.md`) | Pass rule |
|---|---|---|
| Read SNM | minimum butterfly-curve square side, bitlines precharged, wordline asserted, cell holding 0 and 1 | strictly positive at every corner |
| Hold SNM | same measurement, wordline deasserted | strictly positive at every corner |
| Write margin | minimum bitline drive that flips the cell within the write pulse width | strictly positive at every corner |
| Read / write access time | clock edge to valid `dout`, or to completed write | recorded at every corner; feeds Liberty |

| | |
|---|---|
| Target | read SNM, hold SNM and write margin strictly positive at every one of the PVT corners (§7), with Monte Carlo evidence |
| Fallback | none. A corner that cannot close is recorded as open, not dropped |
| Stretch | none |

- Read SNM, hold SNM and write margin are statistical rows: each needs Monte
  Carlo (device mismatch) with a recorded seed, sample count, deterministic
  negative control and a `klt yield` report, combined with, never replacing,
  the corner matrix. Access time is not a statistical row.
- No numeric `target_yield` is set. Cpk, sigma-to-spec and the exact
  Clopper-Pearson yield lower bound are reported per row. This is inherited.
- **Write pulse width**: `gf180-sram` fixes 2 ns for its macro. That number
  depends on the gf180 process and supply and is not inherited. Here it is
  `TBD-measured (#7)`, set by decision record before write margin is graded.
- Whether sky130's models expose a per-instance mismatch switch equivalent to
  the one the inherited Monte Carlo harness uses is `TBD-measured`; settled
  when the harness is brought up (#4).
- Margins are measured on a representative column / bitcell testbench where
  full-array simulation is impractical, as in the inherited definition.

## 7. PVT corners

| Axis | Points |
|---|---|
| Process | `tt`, `ff`, `ss`, `sf`, `fs` |
| Temperature | −40 °C, 25 °C, 125 °C |
| Supply | 1.62 V, 1.80 V, 1.98 V (1.8 V ±10%) |

Fully crossed: 5 × 3 × 3 = **45 corners**. The process names are the `.lib`
section names in the installed PDK's `sky130.lib.spice` (open_pdks
`f6eeac7dad08`, confirmed 2026-10-17: `tt`, `sf`, `ff`, `ss`, `fs` all
present). Every recorded analog result carries all 45, or is recorded as open.
Decision record `0001` explains the departure from the 27-corner set in the
inherited spec.

| | |
|---|---|
| Target | the 45-corner set above |
| Fallback | none. Fewer corners is not a fallback, it is a relaxation and needs a decision record |
| Stretch | none |

## 8. Views and per-view checks

| | Views |
|---|---|
| Target | GDS, LEF, Liberty, Verilog behavioural model, per instance |
| Fallback | GDS, LEF |
| Stretch | none |

Rationale: GDS and LEF are what integration needs; Liberty and the behavioural
model complete a usable macro. LEF and Liberty generation driven from the
compiler without per-instance hand work is an open question in #2 and is
exercised on the first instance.

| View | Check |
|---|---|
| GDS | DRC clean, with the marker handling in §1 settled by #6 |
| LEF | generated by `klt`; pin and obstruction geometry checked against the GDS |
| Liberty | generated from the recorded corner timing data; checked against the simulated arcs it was built from, at every corner |
| Verilog | simulated with cocotb + Icarus against the pin interface in §2; checked for the same read-after-write behaviour as the sim |
| All | cross-view consistency: same pin names, same pin order, same area |

Check commands and tolerances are `TBD-measured`: set when the first view is
generated, by decision record. Liberty is not shippable without the
corner-by-corner timing data behind it.

## 9. Inheritance from `gf180-sram`

`gf180-sram` is master for the PDK-independent half. Taken by pinned
reference through `reuse.lock.json`, per `REUSE.md` in `2AMLogic/2am`. Pinned
commit: `74ba8a621c9edab9b7a75ecb19ca7ea6771588da` (`gf180-sram` `main`,
2026-10-17; the spec files below are byte-identical to those at `d0bacc0fceb6`,
the commit named when the issue was filed — only the Loom install changed).

| Item | Source at the pinned commit | What is taken | What is not taken |
|---|---|---|---|
| Margin definitions and pass rule | `spec/sram.md` § Characterization | read SNM, hold SNM, write margin, strictly positive at every corner | corner set (3 × 3 × 3, 3.3 V) and the 2 ns write pulse, both gf180-specific |
| Statistical treatment | `spec/statistical-treatment-decision.md`, `spec/target-yield-decision.md` | the three rows are statistical; Monte Carlo required with seed, sample count, negative control and `klt yield` report; no numeric `target_yield`; Cpk / sigma-to-spec / Clopper-Pearson reported | nothing |
| Record format | `sim/` record tree convention, `sim/lib/mint_sim_envelope.py`, `sim/lib/env_provenance.py`, `sim/lib/render_signoff_table.py` | append-only record layout and envelope fields | none |
| Sim harness | `sim/lib/run_corner_sweep.sh`, `sim/lib/run_mc_campaign.py`, `sim/lib/snm_extract.py`, `sim/lib/pdk_env.sh` | adopt-or-record outcome: see decision record `0003` | the gf180 PDK binding in each script |

The pins and file hashes are in `reuse.lock.json`. A finding about
`gf180-sram` is filed on `gf180-sram`, not recorded here.

## 10. Signoff and what a range claim requires

**Per instance**, a macro is signed off when all of these hold:

1. DRC clean and LVS clean on the full generated layout.
2. Every margin in §6 strictly positive at every corner in §7, with Monte
   Carlo evidence for the three statistical rows.
3. Access time recorded at every corner and used to generate Liberty.
4. Every view in §8 generated and checked by its row of the check table.

**A range claim** (a claim the compiler accepts `[a, b]` of some parameter)
requires:

1. Every size the compiler accepts is generated by the same code path.
2. The three reference instances (§4) signed off as above first.
3. For each legal `(words, bits, mux)` cell claimed, a generated instance that
   is DRC/LVS-clean. A claim covers exactly the cells it names; a range is
   claimed as the enumerated set, not interpolated from the corners of it.
4. For `M` cells in §3, the measured row limit recorded before the cell is
   claimed.

The 256 × 32 instance through the compiler path closes first. The other
reference instances follow; range growth and 1RW1R wait.

Maturity ladder (from the README): spec ratified → bitcell characterized
across PVT → periphery characterized → first instance DRC/LVS-clean →
reference instances DRC/LVS-clean → views generated and checked → shuttle seat
→ measured silicon.

## 11. Ratification

Not ratified. The ratification request goes to the operator as a ranked
decision (issue #8, step 6). This spec is marked ratified only after that
answer, and the ratification date and the answer are recorded here at that
time.
