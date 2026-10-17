# 0002: Legality rules for (words, bits, mux) and the reference-instance mux

**Status**: Proposed, pending ratification of `spec/sram-compiler.md`.
**Departs from**: `README.md` draft, which gave ranges (words 16–1024, bits
8–64, mux 1/2/4/8) but not which combinations are legal.

## Decision

1. `words` is a power of two; `bits` is a multiple of 8 from 8 to 64; `mux` is
   1, 2, 4 or 8.
2. Array rows `words / mux` ≥ 8; array columns `bits × mux` ≤ 512.
3. Rows above 256 are `TBD-measured (#7)`: the limit is set by bitline length,
   which depends on the measured bitcell, so no limit is asserted now.
4. Reference instances use mux 2 (64 × 32), 4 (256 × 32) and 8 (1024 × 32),
   giving 32, 64 and 128 rows.

## Why

- The draft left the combinations open, and a compiler's contract is its set
  of legal inputs. Without rules, the table in the spec would have undefined
  cells.
- Power-of-two `words` keeps the row decoder a plain binary decoder. A
  non-power-of-two count needs an out-of-range address rule that the spec
  would have to define and test for no benefit to the stated range.
- `bits` a multiple of 8 matches the byte granularity of the optional write
  mask and of the pin interface.
- The 8-row floor is a chosen design floor, not a measured one: below it the
  decoder is too small to exercise the predecode structure the generator must
  prove. It is written as a rule so that a different floor is a new decision
  record.
- 512 columns is the largest `bits × mux` inside the target range (`64 × 8`),
  so rule 2's column bound never excludes a target cell; it exists to bound the
  stretch range.
- Reference mux values keep all three reference instances at 256 rows or fewer,
  so they are independent of the open row limit, and keep the aspect ratio
  within a factor of two across the three.

## Consequence

Each cell of the legal-combination table in the spec is `L`, `-` or `M`. No
cell is undefined.
