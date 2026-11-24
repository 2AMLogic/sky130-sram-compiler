# Provenance addendum 20261124: the `Committed col_*_snm probe (pre-layout)` column of `20261124-snm-pex.md`

Issue: 2AMLogic/sky130-sram-compiler#236 (raised in review of PR #231, #210). `20261124-snm-pex.md` is
append-only, so its seventh comparison column gets its provenance here, not in an edit to it.
Append-only: add a new dated record, never edit this one.

Result: the column is **re-derivable**. Its four SNM values are the output of the committed single-corner
pre-layout probe of the two in-situ SNM benches, and one run of that probe on 2026-11-24 reproduced all six
values of the column (the four SNM values and the two `vtrip` values beside them) to the printed digits.

## What the column is: the single-corner probe, not a 45-corner grid member

The seventh column of the comparison table in [`20261124-snm-pex.md`](20261124-snm-pex.md) (header line 17,
values lines 19-24, introduced by commit `ec207a0`) is the **single-corner pre-layout probe**: the committed
`sim/column/requests/col_hold_snm.probe.request.json` and `col_read_snm.probe.request.json`, corner `tt`,
`1.800 V`, `25 °C` (corner id `tt/1.800V/25C`), run locally by `sim/column/run.sh`.

Issue #236 read the column as a value of a 45-corner grid and said no committed artifact holds a single-corner
value for these benches. Both halves are wrong as of `d3a3e48`; the correction is:

- `sim/column/README.md:42` and `:91` (bench table and shard table) describe the grid requests
  `requests/col_{hold,read}_snm.request.json`: `tt/ff/ss/sf/fs` x `1.62/1.8/1.98 V` x `-40/25/125 °C`, batch.
- The committed single-corner artifact is the recipe (`sim/column/README.md:22-26`): each bench's
  `.probe.request.json`, which `diff` shows is its grid request with `corners` reduced to `tt`/`1.8`/`25`, the
  `batch` block removed and `"backend": "local"` added (analysis, measurement and options identical), run by
  `sim/column/run.sh`.
- No grid value exists for the column to have come from: `sim/column/corners/` is not committed, and
  `git ls-files` lists only the two `tb/` netlists and the four requests for these benches.
- The probe's corner is the nominal member of the grid's corner set, so the probe is a one-corner subset of
  the grid. Nothing was read from a grid run.

## Command, tools and scratch path

Run once on 2026-11-24 (12:13:41-12:14:11 UTC) at `d3a3e48` (merge of PR #231) with a clean tree, from the
repo root:

```
sim/column/run.sh col_hold_snm col_read_snm
```

`run.sh` sources `sim/env.sh` (PDK pin check), drift-gates the benches (`make_column_tb.py --check`), then for
each bench, from `sim/column/requests`, runs
`klt sim <bench>.probe.request.json --backend local -o sim/build/column-probe/<bench> --format json` and
asserts `lib/check_probe.py`. Outcome: `make_column_tb: 40 generated files current`, `check_probe: col_hold_snm: OK`,
`check_probe: col_read_snm: OK`, exit 0. 29.98 s wall and 373,844 kB peak RSS for the whole command; per-corner
`runtime_s` 14.496 s (hold) and 13.849 s (read), inside the 300 s `timeout_s`.

The probe measures only `vtrip`. `eye_snm` and `pinned_snm` are not `klt sim` measurements: they are derived
from the saved sweep (`v(in)`, `v(out)`; 201 points) by the call `make_column_record.py` makes for a grid
record (`snm_rows` -> `snm_for(..., pair=False)`, the smaller of the two eyes):

```
sim/bitcell/lib/fetch_pinned.sh
python3 -I sim/bitcell/lib/snm_from_artifacts.py sim/build/column-probe/col_hold_snm
python3 -I sim/bitcell/lib/snm_from_artifacts.py sim/build/column-probe/col_read_snm
```

- tool: klt `0.9.3.dev5326+g7a0e2ff48fab` (git commit `7a0e2ff48fab49180e1f12c42b364dfcce053ac9`), the host
  `klt` that `run.sh` takes from `PATH`. A dev build, **not** the `signoff.yml` pin (`klayout-tools==0.9.0`);
  klayout `0.30.13`.
- backend: local. `environment.backend` is `{"resolved": "local", "source": "flag"}` and `engine_host` is
  `local`, with no `remote` block. `KLT_SIM_BACKEND=batch` was set in the ambient environment and did not
  apply, because `run.sh` passes `--backend local`.
- engine: ngspice 47 (`environment.engine_version`; binary sha256 `39ca1adb…`, built 2026-11-13).
- models: PDK `sky130A`, open_pdks `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7` (the `sim/pdk.json` pin); deck
  `sky130.lib.spice`, content `sha256:17c208a6…`.
- margin extractor: gf180-sram `snm_extract.py` @ `74ba8a621c9e` (sha256 `56c044cd…`, verified by
  `fetch_pinned.sh`) and the inscribed-square `eyes()` of `sim/bitcell/lib/snm_from_artifacts.py` (sha256
  `992d4a39…`); python3 3.12.3.
- DUT identity (`environment.netlist_closure`, cross-checked with `sha256sum` on the tree):
  `sim/column/tb/col_hold_snm.sp` `f08fd5ad…`, `sim/column/tb/col_read_snm.sp` `3abdaccf…`, both including
  `design/compiler/macro/sram_256x32_m4.spice` `7815e5c5…`.
- scratch path: `sim/build/column-probe/` (repo-root relative, gitignored, not committed): `<bench>.json` (the
  report), `<bench>.err` (empty), `<bench>/report.json` and
  `<bench>/tt_1p800V_25C/{corner.cir,ngspice.log,waveform.raw,waveform.raw.json}` for each bench, plus
  `sim/build/pinned/snm_extract.py`. The artifacts of the run that first produced the column were likewise
  scratch and were never committed, which is why the column had no path.

Tool versions are read from the two probe reports' `provenance` and `environment` blocks. The klt version
comes from `provenance.klt_version`: a local-run report carries no `environment.client_klt_version`, so
`record_common.klt_version_of` reports `unknown (not in report)` for it.

## Re-run against the record: all six rows

| Row (`tt/1.800V/25C`) | Record, column 7 | Re-run, 6 d.p. | Re-run, full precision | Re-run - record |
|---|---:|---:|---:|---:|
| `hold_eye_snm` | 0.707997 V | **0.707997 V** | 0.7079971345770031 V | +1.35e-07 V |
| `hold_pinned_snm` | 0.773103 V | **0.773103 V** | 0.7731029525444357 V | -4.75e-08 V |
| `hold_vtrip` | 0.435986 | **0.435986** | 0.435986 | 0 |
| `read_eye_snm` | 0.429397 V | **0.429397 V** | 0.4293965228064937 V | -4.77e-07 V |
| `read_pinned_snm` | 0.566909 V | **0.566909 V** | 0.5669089616472905 V | -3.84e-08 V |
| `read_vtrip` | 0.446550 | **0.446550** | 0.44655 | 0 |

All four SNM values reproduce to the printed digits, and so do both `vtrip` values. Every difference is below
5e-07 V, i.e. inside the last printed digit: the record printed six decimals, and each full-precision re-run
value rounds to its literal. That is print rounding, not a measurement difference, and the record's precision
cannot support a finer statement. `vtrip` is a report value and is identical. Both `eye_snm` eyes are equal
(identical half-cell inverters); `pinned_snm` is the smaller of its two eyes.

This is consistent with the issue's suspected cause: the column carries what this derivation path produces,
as a cross-check against a `sim/build/column-probe/` scratch run would. The original scratch is gone, so how
the figures were carried into the record cannot be verified; what the figures are is now verified.

## What this record does not establish

- Which build produced the column originally. That run left no committed artifact and named no build: this
  shows the committed recipe yields the same printed values on the build named above, not that the original
  run used it.
- Anything under the `signoff.yml` pin. The probe was run once, with the host `klt`; it was not re-run under
  klt 0.9.0.
- The other six columns of the table. The schematic, device-only and extracted legs come from the committed
  `pex-sram_snm_halfcell_col64.report.json.gz` and are not re-derived here.
- Any grid, #210 headline number or tooling. None was run or changed, and no tool gap was met.
