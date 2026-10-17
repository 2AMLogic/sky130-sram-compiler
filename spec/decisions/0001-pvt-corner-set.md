# 0001: PVT corner set is 5 process × 3 temperature × 3 supply (45 corners)

**Status**: Proposed, pending ratification of `spec/sram-compiler.md`.
**Departs from**: `README.md` draft ("Supply 1.8 V ±10%", no named process or
temperature set) and the corner set of the inherited `gf180-sram` spec.

## Decision

Process `tt ff ss sf fs`; temperature −40 / 25 / 125 °C; supply 1.62 / 1.80 /
1.98 V; fully crossed, 45 corners. Every recorded analog result carries all 45
or is recorded as open.

## Why it departs

- `gf180-sram` uses `ff tt ss` × 3 temperatures × 3 supplies = 27. That
  set omits the skewed corners. A 6T cell is a ratioed circuit: read SNM is
  set by the pull-down against the access device and write margin by the
  access device against the pull-up. `sf` and `fs` skew NMOS against PMOS,
  which is the direction that moves exactly those ratios, so a cell can pass
  at `ff`/`ss` and fail at a skewed corner. Omitting them would leave the two
  margins this block exists to prove ungraded in their worst direction.
- Supply is 1.8 V ±10% because sky130's logic supply is 1.8 V; the gf180
  3.3 V axis does not apply.
- The process names are the `.lib` sections of the installed PDK's
  `sky130.lib.spice`: `tt`, `sf`, `ff`, `ss`, `fs` all present (open_pdks
  `f6eeac7dad08`, checked 2026-10-17).

## Not inherited

The 27-corner set and its 3.3 V axis are gf180-specific; only the pass rule
("strictly positive at every corner") is inherited, and it applies to the 45.

## Cost

45 corners is 1.67× the inherited count per testbench. Multi-corner and Monte
Carlo grids go to the batch fleet through `klt sim`, not hand-launched
locally.
