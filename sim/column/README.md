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
klt sim col_read1.request.json --wait-for-capacity 600 -o <scratch> --format json > <scratch>/col_read1.json   # batch (see Fleet notes)
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

**The client must match the fleet runner.** `klt sim` compares the runner version the fleet image's
manifest publishes against the submitting client before any S3 write, and refuses a mismatch with
`batch_runner_version_mismatch` under the default `batch.runner_version_check: "enforce"`. No client
version is pinned here, because the runner's is not this repo's to declare: read it from a committed
report's `environment.remote.runner_klt_version` (`corners/<id>/<bench>.report.json.gz`) and run that
client in a throwaway environment, `uvx --from "klayout-tools==<that version>" klt sim ...`, so the
host tool is untouched. `make_column_record.py` takes both versions out of the report the same way
(`runner_version_of` / `klt_version_of` in `sim/bitcell/lib/record_common.py`, which report `unknown
(not in report)` rather than guess), so a record can never name a build that did not produce it.
Check the chosen client's own `--report-out` support before relying on it; `--format json` on stdout
works in every version used so far.

**`batch.max_units_per_job` follows from `options.timeout_s`, and is derived, not written down.** A
batch job's bound is every unit burning its full `timeout_s` one after another plus 120 s of job
overhead, and that bound must stay inside the fleet's 3600 s whole-job ceiling — so the largest shard
a client accepts is `floor((3600 - 120) / timeout_s)`:

| requests | `options.timeout_s` | cap | units | shard jobs | largest shard, serial bound |
|---|---:|---:|---:|---:|---|
| `col_read0`, `col_read1`, `col_write0`, `col_write1` | 900 | 3 | 45 | 15 | 3 units, 2820 s |
| `col_write0_nowen` | 900 | 3 | 12 | 4 | 3 units, 2820 s |
| `col_read_snm`, `col_hold_snm` | 300 | 11 | 45 | 5 | 9 units, 2820 s |
| `col_mc_read_snm`, `col_mc_hold_snm` | 300 | 11 | 360 | 33 | 11 units, 3420 s |
| `col_mc_read_snm_neg`, `col_mc_hold_snm_neg` | 300 | 11 | 120 | 11 | 11 units, 3420 s |

Over the cap, `klt sim` refuses before submit with `batch_max_units_per_job_invalid`.
`make_column_tb.py` computes the value from each request's own `timeout_s`
(`max_units_per_job()`, mirroring the client's `DEFAULT_BATCH_MAX_JOB_SECONDS` /
`_BATCH_JOB_OVERHEAD_S`), so changing a `timeout_s` cannot leave a stale cap behind. The serial bound
is a conservative upper bound, not a runtime estimate: these units finish well inside `timeout_s`.

**A capped request shards, and the shards are submitted all at once**, so every capped request also
sets `batch.max_concurrent_jobs` to 7 — without it, `col_mc_read_snm` alone would ask for 33
simultaneous jobs and meet the fleet's concurrency cap (`batch_concurrency_cap`). Each job takes one
16-vCPU `m7i.4xlarge`, and `BATCH_MAX_VCPU` = 224 (2AMLogic/2am `infra/aws/batch-fleet.env`) is the
whole execution layer's share of the account spot quota — 14 such instances — shared with every other
block's sweeps, so one request holds at most half of it. The instance cap
(`BATCH_MAX_CONCURRENT_INSTANCES` = 50) is the looser second bound.

**Pass `--wait-for-capacity 600` on every batch submit.** The fleet is vCPU-budgeted, so a burst is
refused with `batch_no_capacity`; the flag makes the submit wait with backoff instead of failing the
run.

| Path | What |
|---|---|
| `tb/`, `requests/` | Generated benches and `klt sim` requests (`*.probe.request.json` = single-corner local probes) |
| `lib/` | `make_column_tb.py`, `check_probe.py`, `make_column_record.py` |
| `corners/`, `records/` | Append-only evidence: compressed `klt sim` reports and dated records |
