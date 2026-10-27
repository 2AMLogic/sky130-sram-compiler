# design/compiler

Netlist side of the SRAM compiler (issue #26, T1 item 1 analog). One entry point
turns `(words, bits, mux)` into a macro netlist; the 256 x 32 reference instance
uses the same code path as every other size.

## Regenerate

```console
export PDK_ROOT=~/.ciel PDK=sky130A                      # only for steps 1-2
python3 -I design/compiler/gen_schematic.py              # 1. cells/*.sch from cells.py + sizing.json
python3 -I design/compiler/netlists.py                   # 2. netlist/*.spice via `klt netlist`
python3 -I design/compiler/sram_compile.py 256 32 4 -o design/compiler/macro/sram_256x32_m4.spice   # 3.
klt signoff --attest 1 --inventory design/compiler/inventory.json -o design/compiler/evidence/item1.json
python3 -I design/compiler/test_compiler.py              # PDK-free tests
```

Layout (issue #30, details in `layout/README.md`; needs klayout's python module, via uv):

```console
uv run --no-project --with klayout python -I design/compiler/gen_layout.py 256 32 4 \
    -o layout/sram_256x32_m4.gds --socket layout/sram_256x32_m4.socket.json --lef layout/sram_256x32_m4.lef
uv run --no-project --with klayout python -I design/compiler/test_layout.py
python3 -I design/compiler/attest_layout.py              # T1 item 2 envelope (no klt --attest 2 yet, klayout-tools#4221)
```

`gen_layout.py` takes the geometry from `sram_compile.geometry()` and the logic connectivity
from `sram_compile.macro_body()`, so a new netlist change shows up as a layout change. It
refuses (exit 1) what it cannot place: today more than 64 rows.

Step 3 and the tests need no PDK or xschem. `--check` on steps 1-3 reports drift
(exit 3). `netlists.py --check` compares normalised text (no `sch_path`, joined
continuations) because plain `klt netlist --check` cannot check a committed
netlist whose `sch_path` was made repo-relative (tool gap: 2AMLogic/klayout-tools#4210).

Out-of-range input is rejected: words a power of two in 16..1024, bits 8..64, mux 1/2/4/8
(the README target table, DRAFT/unratified; change `sram_compile.py`'s range, not the tests).

## 256 x 32 choice: mux 4

64 rows x 128 columns: near-square (a 256-row, mux 1 array would give 256-cell
bitlines; mux 8 gives 32 rows x 256 columns, a long wordline), and the middle of the
mux set. This is a starting point, not characterised; #29 may revise it.

## Cells (stable port names; #30/#33 inherit them)

| Subckt | Ports | Role |
|---|---|---|
| `bitcell_6t` | BL BLB WL VDD VSS | from `design/bitcell/` |
| `sram_inv` / `sram_wldrv` | A Y VDD VSS | inverter / wordline driver (large inverter) |
| `sram_nand2/3/4` | A0.. Y VDD VSS | decode gates |
| `sram_precharge` | BL BLB PCHB VDD | per column precharge + equalise |
| `sram_colmux` | BL BLB SBL SBLB SEL VSS | per column NMOS pass pair |
| `sram_senseamp` | SBL SBLB SAE SAEB DOUT VDD VSS | per bit isolated latch |
| `sram_wdrv` | SBL SBLB DIN WEN VDD VSS | per bit write driver (pulls the 0 side low) |

Macro `sram_<words>x<bits>_m<mux>`: `A0..A<n-1> D0.. Q0.. WLEN PCHB SAE WEN VDD VSS`.
`A0..A<log2 mux-1>` select the column (physical column = bit*mux + m), the rest the
row. Row decode: predecode groups of <=3 bits (WLEN gates group 0), NAND of the group
lines, `sram_wldrv`. WLEN/PCHB/SAE/WEN timing belongs to the digital partition (#27).

All devices are `nfet_01v8` / `pfet_01v8` at L=0.15 (checked by the tests), sized in
`sizing.json` (a starting point; no simulation yet - #29). Topology is textbook
(decoder, precharge, pass-gate mux, latch sense amp, pull-down write driver); no cell
is taken from OpenRAM. The bitcell has no substrate tap (see `design/bitcell/README.md`);
the array must supply one - not addressed here.
