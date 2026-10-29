# layout

Layout of the SRAM compiler (issue #30, T1 item 2 analog). One generator,
`design/compiler/gen_layout.py`, turns `(words, bits, mux)` into the macro GDS, a LEF abstract
and a klt socket descriptor. The 256 x 32 reference instance (`mux 4`: 64 rows x 128 columns)
goes through the same code path as every other size; there is no per-instance code. The
geometry (rows, columns, address split, predecode groups) comes from `sram_compile.geometry()`
and the logic connectivity is read from `sram_compile.macro_body()`, so the layout cannot
drift from the netlist without a test or an LVS noticing.

| File | What |
|---|---|
| `sram_256x32_m4.gds` | The macro, committed generator output. |
| `sram_256x32_m4.lef` | LEF abstract (pins as drawn, m1-m4 blocked elsewhere). |
| `sram_256x32_m4.socket.json` | `klt socket-check` descriptor the LEF was made from (outline + 78 pins). |
| `records/` | Dated, append-only development checks (DRC, LVS, area). Not the #32 / #33 signoff. |

## Regenerate

```console
export PDK_ROOT=~/.ciel PDK=sky130A                       # only for --lef / --check-lef
uv run --no-project --with klayout python -I design/compiler/gen_layout.py 256 32 4 \
    -o layout/sram_256x32_m4.gds --socket layout/sram_256x32_m4.socket.json \
    --lef layout/sram_256x32_m4.lef --report
sha256sum layout/sram_256x32_m4.gds
# ca10c045b447a8ce3bdb55f8922e2dfb954826dd8a9583ca0d39629d5b9e555c
uv run --no-project --with klayout python -I design/compiler/gen_layout.py 256 32 4 \
    --check layout/sram_256x32_m4.gds --check-socket layout/sram_256x32_m4.socket.json \
    --check-lef layout/sram_256x32_m4.lef                   # exit 3 on drift
uv run --no-project --with klayout python -I design/compiler/test_layout.py
python3 -I design/compiler/attest_layout.py                 # rewrites design/compiler/evidence/item2.json
```

The output is deterministic (GDS timestamps off, no host paths); two runs are byte-identical
(`test_deterministic`). klayout 0.30.12, klt 0.8.1.dev58, open_pdks `f6eeac7d`.

## What is drawn

Bottom to top (all to the ordinary logic rules; **no `areaid.ce` marker anywhere**):

| Block | Drawn how |
|---|---|
| Array | The committed `design/bitcell/bitcell_6t.gds` tiled by translation, **5.18 x 1.735 um** pitch, plus the shapes the cell leaves to the array (below). |
| p-substrate taps | A 0.8 um strap row of p-taps on the VSS columns below row 0, after every 16 rows and above the last row (5 strap rows for 64 rows). The bitcell has no substrate tap. |
| Precharge row (above) | One `sram_precharge` per column, hand drawn at the column pitch: MP1/MP2 with the bit lines landing on their drain contacts, a lateral equaliser, a PCHB m3 bar, the VDD/VSS m3 buses. |
| Column mux row (below) | One `sram_colmux_m<k>` per column (k = column mod mux), NMOS pass pair, SEL on its own m3 track. For `mux 1` the pass gates are tied to VDD. |
| Bit slices | `sram_senseamp` and `sram_wdrv` per bit, built by the same two-strip cell generator as the logic cells, wired to the columns by m3 collectors and m4 verticals. A cell wider than its `mux x 5.18` um group goes in a second tier (see Limits). |
| Row decoder (left) | Per row a NAND (or inverter) and `sram_wldrv` in a lane of height `lanes x 1.735` um; lanes interleave (even rows / odd rows), predecode lines arrive on m4 buses and m3 stubs, the wordline leaves on m3 to a poly landing pad. |
| Control row (below) | Address inverters, predecode and column-select gates placed in the order of the netlist, wired with an m3/m4 channel. |
| Supplies | Right-hand m4 VDD/VSS rings, every cell row's rails run to them; the lane rails use m2 spines tied to the rings by m3 bars above the macro. |

Periphery cells (each was also DRC-checked and LVS-compared alone against its
`design/compiler/netlist/*.spice` while it was drawn; the macro-level checks below cover the
variants actually used):

| Cell | Size (um) | Cell | Size (um) |
|---|---|---|---|
| `sram_precharge` | 5.18 x 3.25 | `sram_senseamp` | 8.74 x 6.62 |
| `sram_colmux_m<k>` | 5.18 x 4.20 | `sram_wdrv` | 6.94 x 5.50 |
| row `nand2` + `wldrv` | 3.54 + 5.54 x 3.18 | control `inv` / `nand2/3/4` | 2.44 / 3.34 / 4.24 / 5.14 x 4.02 |

## The abutted bitcell pitch (the finding this issue exists for)

The committed cell box is 5.18 x 1.665 um. Tiling it as drawn (4 x 4 test array, three DRC
decks as in `design/bitcell/run_drc.sh`):

| Tiling | curated `sky130` | `sky130A_mr.drc` |
|---|---|---|
| translate, 1.665 um vertical pitch | 84 `nsdm.space.1` | 84 `nsdm.1`, **12 `difftap.3`** |
| alternate rows mirrored (MX) | 96: `li1.space`, `met1.space`, `met3.space`, `npc.space`, 64 `nsdm.space`, `psdm.space` | 83: `li.3`, `m1.2` x 8, `m3.2`, `npc.2`, `nsdm.1` x 58, `psdm.1` |
| translate, **1.735 um** pitch + fills below | clean | clean |

* The n-tap at the top of one cell is 0.20 um from the p diffusion at the bottom of the next
  (rule `difftap.3`: 0.27 um), so the vertical pitch has to grow by **0.07 um** (+4.2 %,
  8.625 -> 8.987 um^2 per bit). The curated deck is blind to `difftap.3`
  (2AMLogic/klayout-tools#4282); `sky130A_mr.drc` sees it.
* Mirroring the rows is worse, not better: the cell is not symmetric about its horizontal
  edges, so the mirrored pairs bring VSS m3 rails, m1 pads, li, implants and npc of
  neighbouring cells closer than their spacing rules (the 96 / 83 findings above).
* The horizontal pitch 5.18 um is legal as drawn.
* Fills the generator adds to make the tile legal: `nsdm` bridges between columns and rows
  (implant spacing 0.38 um), a poly bridge between the wordline stubs of neighbouring cells
  (they end 0.22 um apart, not connected), and continuous nwell, bit-line (m1), VSS (m1) and
  VDD (m2) stripes through the 0.07 um row gaps and the strap rows.
* **The wordline is a bare poly line.** The bitcell has no wordline landing above poly, so a
  row of 128 cells is 663 um of 0.15 um poly (about 4400 squares) driven from one end by the
  wordline driver. The bitcell would need a metal strap (a WL contact and an m2/m3 landing)
  before the access time means anything; that is a bitcell change (#7), not done here.

## Area, against the foundry/OpenRAM reference

| | bbox (um) | area (um^2) | per bit (um^2) |
|---|---|---|---|
| this macro, 256 x 32 mux 4 | 713.99 x 179.63 | 128,254 | 15.66 |
| of which array (8192 cells) | 663.04 x 115.04 | 76,278 (59.5 %) | 9.31 |
| OpenRAM `sram_1rw1r_32_256_8_sky130` | 377.10 x 447.14 | 168,617 | 20.58 |

**Ratio this / OpenRAM = 0.761** (24 % smaller by bounding box).
OpenRAM figure: `klt stats` on `libs.ref/sky130_sram_macros/gds/sram_1rw1r_32_256_8_sky130.gds`
(open_pdks `f6eeac7d`, sha256 `3d102bc9...bf60`), the OpenRAM (VLSIDA) 1 kB macro that
ships in the sky130 PDK; same capacity (256 words x 32 bits). Nothing of it is reused.

Not like-for-like, and the comparison is only a sanity check on the order of magnitude:

* OpenRAM's macro is **1RW1R** (two ports, the foundry dual-port cell 3.96 x 3.035 um =
  12.0 um^2, two sets of bit lines and periphery); this one is single port.
* This bitcell is drawn to logic rules and is not characterised (read/write margins are #29);
  the foundry cell is drawn to relaxed rules inside the SRAM core marker.
* This macro has no digital controller (#31) and no timing/replica circuit; OpenRAM's has
  both, plus its own power rings. Power grid and tap distance here are not analysed.
* Nothing here says the periphery works: sizing is the #26 starting point, no simulation
  has been run on the layout (no extraction), and the wordline strap above is missing.

## Family: what is checked, what the generator refuses

Development checks (record `records/20261027-ca10c045.md`; DRC = the three decks of
`design/bitcell/run_drc.sh`; LVS = `klt lvs` of the whole macro against
`sram_compile.py`'s netlist, flat, with `combine_devices`):

See the table in the record. In short: every size listed there is generated by the same
entry point, is DRC clean and LVS `match`.

Where the generator breaks (and says so, exit 1, never a wrong layout):

* **Rows > 64** (`words / mux > 64`, which is three predecode groups and a 3-input row gate)
  are refused: the lane scheme routes each predecode input as one m3 track per 1.735 um row
  pitch, and three per row from three interleaved lanes does not fit the m3 pitch (a
  `256 x 8 mux 1` run had 880 m3 and 512 m2 spacing violations before the refusal was added).
  Fixing it needs a different decoder floorplan (predecode buses copied per lane, or a metal
  layer above m4), so it is the next issue, not a range claim.
* **`mux 1`** works only because the sense-amp and write-driver cells (8.74 and 6.94 um wide)
  go in two tiers; the four m4 verticals of a bit must keep 0.7 um from every other bit's, so
  Q and D jog sideways on m3 to a free slot. `_choose_slots` raises `GenError` if no slot
  exists for a given group width.
* Pitch-matched cells are the two that are drawn by hand (`sram_precharge`,
  `sram_colmux`): their bit-line contacts have to land on the cell's m1 columns, which the
  generic two-strip engine cannot place.

## Not claimed

DRC and LVS of the committed instance as signoff evidence (#32, #33), power delivery and tap
distance (#34), extraction, timing, any other reference instance, 1RW1R. The development
checks above were run to find generator bugs; they are listed in `records/` and do not replace
those issues' records.

## control/ — routed control block (T1 item 2, digital)

`layout/control/` holds the place-and-route of the synthesized `sram_ctrl`
256 x 32 control netlist (`rtl/synth/sram_ctrl_256x32_synth.v`) with
`klt place-and-route` on `sky130_fd_sc_hd` / `tt_025C_1v80` (same pin as
`rtl/synth/request.json` and `sim/pdk.json`).

| File | Role |
| --- | --- |
| `place-and-route.request.json` | the request: utilization floorplan, `sky130hd` PDN preset (tapcell + straps + fillers), `target_stage: route`, `seed: 1` |
| `run_pnr.sh` | reproducible wrapper; `--check` runs the flow twice and requires both GDS identical to each other and to the committed one (exit 3 on drift) |
| `control.gds`, `control.gds.sha256` | committed routed stream and its hash |
| `place-and-route.response.json` | committed P&R response (`power.pdn: true`, named `power.tapcell_master`); item 11 consumes it |

Regenerate: `layout/control/run_pnr.sh`; verify: `layout/control/run_pnr.sh --check`.
The wrapper runs klt from the repo root on purpose: the `openroad` on `PATH`
is a container that mounts only its working directory, so the netlist
(outside `layout/control/`) is only visible from the root.

Assumed floorplan (the macro edge is not defined while `partition_boundary`
is a placeholder pending #2): a free-standing core with the four
analog-facing control outputs (`pch`, `wl_en`, `sae`, `wen`) pinned to the
south edge; all other pins are placed by the tool. Pin side and die area
should follow the control-signal mapping (#38) once written. The 10 ns clock
period is a placeholder, not a spec value; timing closure is out of scope.

The as-built netlist with CTS buffers (`verilog_path` in the response) is the
LVS reference for #33, not the pre-CTS `rtl/synth` netlist.
