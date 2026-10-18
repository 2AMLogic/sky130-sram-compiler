# sim/bitcell

Bitcell sizing and margin evidence (issue #7). Everything multi-corner or Monte
Carlo is a `klt sim` request to the batch fleet; nothing here loops `ngspice`.

```bash
source sim/env.sh                         # PDK pin check
sim/bitcell/lib/fetch_pinned.sh           # fetch gf180-sram snm_extract.py @ pinned commit, verify sha256
python3 -I sim/bitcell/lib/make_tb.py     # regenerate tb/ + requests/ from design/bitcell/sizing.json (--check = drift gate)
cd sim/bitcell/requests
klt sim read_snm_corners.request.json --backend batch -o <scratch> --report-out <scratch>/read.json.gz
python3 -I ../lib/snm_from_artifacts.py <scratch>          # SNM per corner from the waveform artifacts
```

| Path | What |
|---|---|
| `tb/` | Testbench bodies (generated). `read_snm`/`hold_snm`: decoupled half cell; `mc_*`: two independently mismatched half cells; `write_trip`: full cell (schematic subckt) with a 33-trial ladder; `mc_write_trip`: the same ladder under `_mm` mismatch (fs, sf x 1.62/1.98 V x -40/125 C, 60 requested per point; record via `lib/make_write_mc_record.py`; batch jobs are capped at 5 units by the fleet's 3600 s ceiling, so run it when the fleet has free instances). `records/2026-10-18-write-mc-complete.md` merges the partial `20261018-write-mc` report with a full re-run (`corners/20261018-write-mc-complete/`, `make_write_mc_record.py --report <base> <rerun>`) to n = 60 valid at all 8 points. |
| `requests/` | `klt sim` requests (generated): 45 corners = {tt,ff,ss,sf,fs} x {-40,25,125 C} x {1.62,1.80,1.98 V}; MC requests use the `_mm` library sections. |
| `lib/` | `make_tb.py`, `fetch_pinned.sh`, `snm_from_artifacts.py`, `make_record.py`, `make_write_mc_record.py`, `make_controls_record.py`. |
| Controls | `mc_write_trip_det` (mismatch switched off, n=3), `mc_write_trip_neg` / `mc_{read,hold}_snm_neg` (mismatch sigma x6 via the `_slope` params, n=20, seed 20261019); record `records/2026-10-18-write-mc-controls.md` via `lib/make_controls_record.py`. Fleet only. |
| `corners/`, `records/` | Append-only evidence: compressed `klt sim` reports and dated records. |

## Margin definitions (taken from `gf180-sram` @ `74ba8a62`, pinned)

- **Read / hold SNM**: butterfly of the decoupled half cell (read: BL = VDD, WL = VDD; hold: WL = 0),
  side of the largest square in a lobe. The sweep is normalised and scaled by VDD.
- **Write margin**: write trip voltage with a fixed 2 ns write pulse: the weakest `0` on the losing
  bit line that still flips the cell.

Two deviations, both recorded in the evidence record and neither relaxing a pass bar:

1. **Write trip by ladder, not bisection.** gf180-sram bisects inside a `.control` loop; `klt sim` owns
   the `.control` block, so each corner runs 33 independent 2 ns trials (BL = VDD*k/32) in one
   transient and the margin is the highest level that flipped. Resolution is VDD/32 (56 mV at 1.8 V);
   the reported value is the highest *flipping* level, i.e. a lower bound on the trip voltage.
2. **SNM square.** The pinned `snm_extract.py` takes the largest *vertical* gap between a VTC and its
   mirror as the square side. That is not the largest inscribed square (the side is the gap along the
   y = x direction divided by sqrt 2) and over-reads: at tt / 1.98 V / 25 C read, pinned 0.572 V,
   inscribed square 0.442 V, and an independent series-noise-source SPICE probe 0.441 V. This
   directory therefore reports `eye_snm` (inscribed square, `snm_from_artifacts.py`) as the margin and
   `pinned_snm` beside it. Filed on `2AMLogic/gf180-sram`.

## Fleet notes

- The fleet image carries open_pdks `c6d73a3`, not the repo pin `f6eeac7`; every request sets
  `options.stage_model_inputs` so the pinned model library is what runs.
- The fleet image predates `corners.params` (klayout-tools#3878), so sizing candidates are separate
  requests, not a parameter axis.
