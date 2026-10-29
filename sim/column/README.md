# sim/column

Column (bit-slice) benches for the 256 x 32 reference instance, T1 item 9 (analog partition, issue #29).
Everything multi-corner or Monte Carlo is a `klt sim` request to the batch fleet; nothing here loops `ngspice`.

Design under test: one bit slice of the compiled macro `design/compiler/macro/sram_256x32_m4.spice` (mux 4 =
64 rows x 128 columns, so **64 cells per bit line**): 4 physical columns x 64 `bitcell_6t`, a `sram_precharge` and
a `sram_colmux` per column, one `sram_senseamp`, `sram_wdrv` and SAEB inverter, wired as in the macro, and the real
`sram_wldrv` on the accessed word line (row 0). Every subckt is `.include`d from the macro netlist; the SNM half-cell
devices are read out of the macro's `bitcell_6t` by the generator. No hand-copied netlist.

## Cold start

```bash
git clone <this repo> && cd sky130-sram-compiler
source sim/env.sh                    # PDK pin check (sim/pdk.json)
sim/run_all_benches.sh               # every bench, once: digital (cocotb) + analog (one local corner each, ~15 min)
sim/column/run.sh col_read1          # or one analog bench
rtl/tb/cocotb/run.sh                 # or the digital bench only
```

`sim/column/run.sh` checks the committed benches against the macro (`make_column_tb.py --check`), runs each
bench's `requests/<bench>.probe.request.json` (tt, 1.8 V, 25 C, `--backend local`) and asserts the bench shows what
it exists to detect (`lib/check_probe.py`: a ladder must have a failing and a passing end; the negative control must
never flip). The corner / Monte Carlo grids are the committed `requests/<bench>.request.json`:

```bash
python3 -I sim/column/lib/make_column_tb.py          # regenerate tb/ + requests/ (--check = drift gate)
sim/bitcell/lib/fetch_pinned.sh                      # gf180-sram snm_extract.py @ 74ba8a62, sha256 verified
cd sim/column/requests
klt sim col_read1.request.json -o <scratch> --format json > <scratch>/col_read1.json   # batch backend (KLT_SIM_BACKEND=batch)
python3 -I ../lib/make_column_record.py --id <id> --out ../records/<id>.md --evidence ../corners/<id> --scratch <scratch>
```

## Benches

| Bench | Measures | Grid | Negative control / validity |
|---|---|---|---|
| `col_read0`, `col_read1` | read access: SAE-delay ladder (0 .. 2.4 ns) reading a stored 0 / 1 with every other cell storing the opposite (worst-case leakage); DOUT, sense differential, Q/QB read bump, half-select retention | 45 corners | read 1 at delay 0 must fail (ladder has a failing end); stored value must survive every read |
| `col_write0`, `col_write1` | write completion: WL + WEN pulse-width ladder (0.05 .. 2.0 ns) through wdrv, colmux and the bit line into a restored cell; half-select retention | 45 corners | shortest pulse must not write; `col_write0_nowen` (WEN never asserted) must never flip |
| `col_read_snm`, `col_hold_snm` | in-situ SNM: decoupled half cell whose bit line is the real column (precharge on + 63 cells) | 45 corners | - |
| `col_mc_read_snm`, `col_mc_hold_snm` | the same with two independently mismatched half cells | tt/sf/fs `_mm` x 1.62/1.98 V x 125 C, n = 60 | `_neg`: mismatch sigma x6, n = 20 (must collapse the margin) |

Margin definitions are taken from `gf180-sram` @ `74ba8a62` through `sim/bitcell/lib` (see `sim/bitcell/README.md`);
the SNM reported is `eye_snm` (inscribed square) with the pinned extractor's number beside it, as there.

## Not modelled (pre-layout)

No bit-line / word-line wire parasitics; the 124 other columns load the word line as 248 access-sized NMOS gates;
strobes are ideal 50 ps ramps; the row decoder and strobe timing (digital partition) are outside the bench.

## Fleet notes

- The fleet runner is klt 0.7.0 and refuses a 0.8.x client (`batch_runner_version_mismatch`, klayout-tools#4211). Fleet
  runs here use `uvx --from "klayout-tools==0.7.0" klt sim ...` (a throwaway environment; the host tool is untouched).
  0.7.0 has no `--report-out`; the report is stdout (`--format json`).
- Ladder units are 2-7 min each, so the requests set `batch.max_units_per_job` to 3 (3600 s job ceiling).

| Path | What |
|---|---|
| `tb/`, `requests/` | Generated benches and `klt sim` requests (`*.probe.request.json` = single-corner local probes) |
| `lib/` | `make_column_tb.py`, `check_probe.py`, `make_column_record.py` |
| `corners/`, `records/` | Append-only evidence: compressed `klt sim` reports and dated records |
