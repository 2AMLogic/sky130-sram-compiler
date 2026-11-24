# SNM half-cell column top, DRC / LVS / extract-only record 20261124

Issue: 2AMLogic/sky130-sram-compiler#228 (part of #207; unblocks #210). Append-only: add a new dated record, never edit this one.
This record delivers the layout only. It measures nothing, runs no simulator, and does not claim the graded item-7 result.

- generator: `uv run --no-project --with klayout python -I design/compiler/gen_layout.py --snm-halfcell -o <gds> --report` (same entry point and `build_array` / `cell_precharge` as the macro; the half-cell is `design/bitcell/gen_bitcell.py` `build(half=True)`)
- top: `sram_snm_halfcell_col64`, 64 rows x 1 column: row 0 the decoupled half-cell, rows 1..63 `bitcell_6t`, one `sram_precharge` on top; 6.07 x 118.29 um
- layout (not committed, regenerated): sha256 `3bd5d3a4b7633ba1526e268d8593f564e00798fc358812f6d46f000dc8ba9373`
- tools: `klt 0.9.0` (`uvx --from klayout-tools==0.9.0 klt`, the signoff pin; klayout engine 0.30.14, which klt warns differs from the 0.30.12 it was tested against), PDK sky130A from `~/.volare`

## What is drawn

- Half-cell = the left half of the bitcell on the same footprint (5.18 x 1.665 um), from the same geometry code, so pu `pfet_01v8` 0.42/0.15, pd `nfet_01v8` 0.84/0.15, ax `nfet_01v8` 0.42/0.15 track `design/bitcell/sizing.json`. Cut: the QB strap and the Q-to-right-gate link; the right inverter and right access device are not drawn.
- `IN` = the shared pull-up/pull-down gate (the bitcell's QB-gate head, m1). `OUT` = the drain node (the bitcell's Q, li). `WL0` = its own access gate, a separate port; the 63 background rows have their own `WL1..WL63` ports (the bench ties them to 0).
- Ports as top-cell labels: `BL0 BLB0 IN OUT WL0..WL63 PCHB VDD VSS`. Both `BL0` and `BLB0` reach the 63 background cells and `sram_precharge` (`PCHB`).
- Each WL pad gets a 0.30 um m3 stub (`met3.area.1`): in the macro the row decoder supplies that m3 area, here the pad is the port.
- The layout imposes no data: background Q = 0 is a simulation `.nodeset`, nothing in the layout.

## DRC

- `design/bitcell/run_drc.sh <gds> <scratch>` (curated `--deck sky130`, `lydrc`, `mr` `sky130A_mr.drc`): curated `clean` 0 violations; lydrc and mr 0 violations, `coverage_unknown` (klt exit 4 on zero-finding klayout runs: no violation reported, not proven clean).
- Negative control: `klt drc <gds> --deck sky130 --negative-control verification/drc/neg_probe.gds --negative-control-categories met1.width.1` -> `passed` (the probe trips `met1.width.1`).
- `verification/drc/probe.py scan <gds>`: 0 `areaid.ce (81/2)` shapes. No marker-layer exception: the top is drawn to the same logic rules as the bitcell.

## LVS

- `design/macro/lvs/run_lvs.sh <gds> <scratch> design/macro/lvs/sram_snm_halfcell_col64.spice sram_snm_halfcell_col64` (script unchanged):

```
ref      engine=klayout status=match  nets (197,197,197) devices (384,384,384)  {'topology': 64, 'topology.flattened': 1}
         power_connectivity=unchecked body_verification=verified
ref_bad  engine=klayout status=mismatch (expected)  nets (197,197,191) devices (384,384,378)
```

- Reference `design/macro/lvs/sram_snm_halfcell_col64.spice`, written by `design/macro/lvs/make_snm_ref.py` (`--check` is a drift gate and a unit test): `bitcell_6t` and `sram_precharge` verbatim from `design/compiler/macro/sram_256x32_m4.spice`; the half-cell devices are that bitcell's `XMPL/XMNL/XMAL` with gate = `IN`, drain = `OUT`. That is the DC fixture's structure (`sim/column/lib/make_column_tb.py::snm_tb(mode, pair=False)`: half-cell on `bl0`, 63 background bitcells, one precharge), not the closed-loop cell. 384 devices = 63 x 6 + 3 + 3.
- Negative control (by `run_lvs.sh`, last background bitcell `XC63_0` wired to `WL0`, the half-cell's word line) reports `mismatch`.
- `power_connectivity: unchecked` (klt checks it only for gate-level Verilog references), so not rail-continuity evidence. The layout reports 197 pins against 71 reference ports: child `Q`/`QB`/etc. labels in the bitcell GDS promote to flat pins, as in the macro; `#210` must bind with `klt pex --pins` / `--rename-declared-pins`.

## Bulk ties

All NFET bulks land on `VSS` through the array's p-substrate tap straps (`B = [0,16,32,48,64]`, tap on the `VSS` m1 columns): the half-cell's `pd` and `ax` included, so nothing uses `vsubs` and no `vsubs` pin workaround is needed; `klt lvs` reports `body_verification: verified`. PFET bulks (half-cell `pu`, precharge) land on `VDD` through the n-taps in the continuous nwell (the bitcell's n-tap, the precharge cell's tap). Extraction: `device_bulk_nets` {VSS: 254, VDD: 130}, one declared global `vsubs` unused by any device.

## Extraction sanity (extract-only)

`design/macro/lvs/run_pex.sh <gds> sram_snm_halfcell_col64 <scratch>` under `klt 0.9.0`: exit 4 (accepted), **1.04-1.08 s wall, peak RSS 125-126 MB**, 384 devices, 197 nets, `body_bias.status=biased`, `unbiased_nets=[]`, bulk nets `VSS`, `VDD`. Well inside the 300 s budget; no simulator was run.

## Regressions

- `gen_bitcell.py --check design/bitcell/bitcell_6t.gds`: 0 (byte-identical); `gen_layout.py 256 32 4 --check layout/sram_256x32_m4.gds`: 0.
- `design/compiler/test_layout.py` (13 tests, 5 new for the top) and `test_compiler.py`: pass. `pyflakes` clean.
