# Bitcell Monte Carlo controls record 2026-10-18-write-mc-controls (0842c3d)

Issue: 2AMLogic/sky130-sram-compiler#19 (follows #14, #7). Append-only: add a new dated record, never edit this one. `2026-10-18-write-mc-complete.md` and `20261018-040941-91ba071.md` are not edited; this record supplies the controls their Limits sections say are missing.

## Provenance

- klt: None; backend: batch fleet; models staged from the repo-pinned PDK (`options.stage_model_inputs`)
- determinism control: request `sim/bitcell/requests/mc_write_trip_det.request.json`, testbench `tb/mc_write_trip_det.sp` (the baseline ladder with `.param mc_mm_switch=0` after the `_mm` library section), n=3 per point, report `20261018-mc-controls/mc_write_trip_det.report.json.gz`
- write negative control: request `mc_write_trip_neg.request.json`, testbench `tb/mc_write_trip_neg.sp`, n=20 per point, seed 20261019 (baseline seed 20261018), mismatch sigma x6, report `20261018-mc-controls/mc_write_trip_neg.report.json.gz`
- read / hold negative control: requests `mc_read_snm_neg` / `mc_hold_snm_neg`, n=20 per point, seed 20261019, mismatch sigma x6, same 6 points as the baseline
- mismatch scaling mechanism: the sky130 `_mm` sections sample `param = nominal + MC_MM_SWITCH * AGAUSS(0,1,1) * (<device>__<param>_slope / sqrt(l*w*mult))`; the negative-control testbenches multiply every non-zero slope of nfet_01v8 and pfet_01v8 (pinned open_pdks f6eeac7 `*__mismatch.corner.spice`) by `mm_scale = 6` with `.param` lines placed after the klt-injected `.lib`. klt has no first-class knob for this (filed as 2AMLogic/klayout-tools#3942).
- baseline: n=60 per point write-trip MC (seed 20261018) from `corners/20261018-write-mc/` merged with `corners/20261018-write-mc-complete/` (rule of `make_write_mc_record.py`), and the read/hold MC tables of `records/20261018-040941-91ba071.md`; neither was re-run.

- fleet jobs, determinism (5): `klt-sim-2d064bf9368c`, `klt-sim-5132cbb78b9f`, `klt-sim-881eb80a8920`, `klt-sim-925e51ffebec`, `klt-sim-b0a71768dc4e`
- fleet jobs, write negative (32): `klt-sim-018d48aff527`, `klt-sim-03e7bf2580f2`, `klt-sim-04255b65f124`, `klt-sim-04d8a990cf9b`, `klt-sim-1012ec853718`, `klt-sim-14b230b290c8`, `klt-sim-1e2bcd8fc6cc`, `klt-sim-28e4f0af0eaf`, `klt-sim-51f99cd67ca8`, `klt-sim-56a803668873`, `klt-sim-62e9fd015812`, `klt-sim-67c99c8263ec`, `klt-sim-7e0e97884bda`, `klt-sim-822bb320fd77`, `klt-sim-825edfc777a8`, `klt-sim-849da7edae0f`, `klt-sim-94d6955af6bb`, `klt-sim-96e1c99973b9`, `klt-sim-9cc914a83335`, `klt-sim-a4392e27e48a`, `klt-sim-a5b30b54b401`, `klt-sim-aa8436b4db82`, `klt-sim-ac2fe8e6d411`, `klt-sim-b9c509046d9d`, `klt-sim-c0709a01aac1`, `klt-sim-cc5dbcce2b23`, `klt-sim-d5f8198ccdbd`, `klt-sim-d71bd0311bda`, `klt-sim-d7db67352996`, `klt-sim-e5c93ca42db1`, `klt-sim-ef02252e97ce`, `klt-sim-fd24ef4013e3`
- fleet jobs, read negative (4): `klt-sim-1e1b685ecc74`, `klt-sim-6f175d648353`, `klt-sim-8696fdd7425e`, `klt-sim-a1e23fafc362`
- fleet jobs, hold negative (4): `klt-sim-32edeb1efce9`, `klt-sim-355facb499b7`, `klt-sim-422fcc7fb5ff`, `klt-sim-a72de24ff365`

## Grading bar (by reference, not redesigned)

gf180-sram `spec/statistical-treatment-decision.md` (read in a local checkout at `8d5a317`; the pinned commit `74ba8a621c9e` was not re-read) asks for a determinism control (mismatch off reproduces the deterministic corner), a negative control (an independently seeded, known-bad variant detected as degraded at every point) and a `klt yield` report with recorded seed and sample count. No numeric detection threshold is ratified there, so the one below is this record's own, stated before any control result was read.

## Criteria (fixed before looking at results)

- Determinism: at every point all 3 mismatch-off samples have the same highest flipping level k*, equal to k* of the matching deterministic corner in the 45-corner write table.
- Negative control: a point is *detected* iff sigma(control) >= 2 x sigma(baseline) AND sigmas-to-failure(control) <= 0.5 x sigmas-to-failure(baseline). Scaling sigma by 6 predicts a ratio of about 6 on both. Any undetected point is reported as such and the factor is not changed afterwards.

## Determinism control (write trip, mismatch off)

| process | VDD (V) | T (C) | units | k* of each sample | k* of deterministic corner (45-corner record) | identical and equal |
|---|---:|---:|---:|---|---:|---|
| fs_mm | 1.62 | -40 | 3 | [6, 6, 6] | 6 | yes |
| fs_mm | 1.62 | 125 | 3 | [4, 4, 4] | 4 | yes |
| fs_mm | 1.98 | -40 | 3 | [7, 7, 7] | 7 | yes |
| fs_mm | 1.98 | 125 | 3 | [5, 5, 5] | 5 | yes |
| sf_mm | 1.62 | -40 | 3 | [14, 14, 14] | 14 | yes |
| sf_mm | 1.62 | 125 | 3 | [14, 14, 14] | 14 | yes |
| sf_mm | 1.98 | -40 | 3 | [15, 15, 15] | 15 | yes |
| sf_mm | 1.98 | 125 | 3 | [15, 15, 15] | 15 | yes |

Result: all 8 points reproduce the deterministic k*.

## Negative control, write trip (sigma x6, n=20, seed 20261019)

Mean / sigma are of the lower-bound trip voltage (V); sigmas-to-failure = mean/sigma against 0 V; no-flip samples enter at 0 V and are counted.

| process | VDD (V) | T (C) | units | n valid | no-flip | non-monotone | baseline mean / sigma | control mean / sigma | baseline sigmas | control sigmas | detected |
|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---|
| fs_mm | 1.62 | -40 | 20 | 20 | 1 | 0 | 0.293 / 0.027 | 0.367 / 0.321 | 11.0 | 1.1 | yes |
| fs_mm | 1.62 | 125 | 20 | 20 | 2 | 0 | 0.213 / 0.031 | 0.319 / 0.462 | 6.9 | 0.7 | yes |
| fs_mm | 1.98 | -40 | 20 | 20 | 0 | 0 | 0.454 / 0.029 | 0.433 / 0.197 | 15.4 | 2.2 | yes |
| fs_mm | 1.98 | 125 | 20 | 20 | 1 | 0 | 0.339 / 0.033 | 0.415 / 0.187 | 10.2 | 2.2 | yes |
| sf_mm | 1.62 | -40 | 20 | 20 | 0 | 0 | 0.715 / 0.021 | 0.554 / 0.127 | 34.0 | 4.4 | yes |
| sf_mm | 1.62 | 125 | 20 | 20 | 0 | 0 | 0.726 / 0.029 | 0.623 / 0.206 | 25.0 | 3.0 | yes |
| sf_mm | 1.98 | -40 | 20 | 20 | 0 | 0 | 0.933 / 0.024 | 0.854 / 0.109 | 39.5 | 7.8 | yes |
| sf_mm | 1.98 | 125 | 20 | 20 | 0 | 0 | 0.941 / 0.025 | 0.872 / 0.110 | 37.7 | 7.9 | yes |

Result: detected at 8 of 8 points.

## Negative control, read / hold SNM (sigma x6, n=20, seed 20261019)

### read SNM

| point | n | extract fail | baseline mean / sigma (V) | control mean / sigma (V) | baseline sigmas to 0 | control sigmas to 0 | control min (V) | detected |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| fs_mm_1p620V_125C | 20 | 0 | 0.4402 / 0.0081 | 0.3962 / 0.0511 | 54.3 | 7.7 | 0.3308 | yes |
| fs_mm_1p980V_125C | 20 | 0 | 0.4924 / 0.0096 | 0.4519 / 0.0548 | 51.3 | 8.2 | 0.3725 | yes |
| sf_mm_1p620V_125C | 20 | 0 | 0.2516 / 0.0108 | 0.2215 / 0.0566 | 23.3 | 3.9 | 0.0601 | yes |
| sf_mm_1p980V_125C | 20 | 0 | 0.2856 / 0.0108 | 0.2544 / 0.0730 | 26.4 | 3.5 | 0.1686 | yes |
| tt_mm_1p620V_125C | 20 | 0 | 0.3573 / 0.0093 | 0.3132 / 0.0529 | 38.4 | 5.9 | 0.2202 | yes |
| tt_mm_1p980V_125C | 20 | 0 | 0.3952 / 0.0112 | 0.3521 / 0.0623 | 35.3 | 5.7 | 0.2226 | yes |

### hold SNM

| point | n | extract fail | baseline mean / sigma (V) | control mean / sigma (V) | baseline sigmas to 0 | control sigmas to 0 | control min (V) | detected |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| fs_mm_1p620V_125C | 20 | 0 | 0.6190 / 0.0075 | 0.5575 / 0.0591 | 82.5 | 9.4 | 0.4399 | yes |
| fs_mm_1p980V_125C | 20 | 0 | 0.7264 / 0.0085 | 0.6710 / 0.0422 | 85.5 | 15.9 | 0.6027 | yes |
| sf_mm_1p620V_125C | 20 | 0 | 0.5421 / 0.0124 | 0.5146 / 0.0509 | 43.7 | 10.1 | 0.4326 | yes |
| sf_mm_1p980V_125C | 20 | 0 | 0.6076 / 0.0095 | 0.5832 / 0.0628 | 64.0 | 9.3 | 0.4865 | yes |
| tt_mm_1p620V_125C | 20 | 0 | 0.6171 / 0.0095 | 0.5698 / 0.0435 | 65.0 | 13.1 | 0.4917 | yes |
| tt_mm_1p980V_125C | 20 | 0 | 0.6927 / 0.0104 | 0.6597 / 0.0518 | 66.6 | 12.7 | 0.5480 | yes |

Result: detected at 12 of 12 read/hold points.

## klt yield (baseline n=60 write trip)

`klt yield` did not run: `the klt_yield_native extension is not installed -- from a repo checkout, run `maturin develop --release` inside native/yield/ (or `uv sync --group yield`); see docs/cli/yield.md#building-the-native-extension` (klt `klt 0.7.1.dev2133+gc2e647e2cf05`). No yield, interval or Cpk is reported here and none is hand-computed in its place. Known gap: 2AMLogic/klayout-tools#2900 (the documented `klayout-tools[yield]` install path does not resolve; `klt-yield-native` is not on the package index). The input is committed (`20261018-mc-controls/write_trip_baseline.samples.json`: the 8 points x 60 lower-bound trip voltages of the n=60 baseline, seed 20261018, limit min 0 V; a no-flip sample would enter as -VDD/32; there are none) so the report can be produced where the extension is installed: `klt yield 20261018-mc-controls/write_trip_baseline.samples.json --format json`. Known related: klayout-tools#2909 (quantised sample sets, relevant here because the ladder values take few distinct levels).

## Limits of this record

- n = 20 per point for the negative controls and 3 for the determinism control (not the baseline's 60); the detection test compares sigma of 20 against sigma of 60, relative sampling error about 16 % and 9 %.
- The scaled variant changes mismatch sigma only through the pinned model's slope parameters; it does not change the process corner, the nominal parameters or the topology. A single factor was run, so no sensitivity curve is claimed.
- Under the larger sigma the lower-bound mean can rise rather than fall (fs points): no-flip samples enter at 0 V and the lower bound floors there, so a heavy lower tail is invisible to the mean. Detection is therefore by sigma and sigmas-to-failure, as the criterion says, and the no-flip counts are reported beside them.
- The pass/fail thresholds are this record's own (gf180-sram ratifies none); they are not a yield claim about the bitcell.
- Write controls cover the same 8 points as the baseline (fs/sf `_mm` x 1.62/1.98 V x -40/125 C) and the read/hold controls the same 6 points (tt/sf/fs `_mm` x 1.62/1.98 V x 125 C).
- No layout parasitics (no PEX). The fleet image PDK is open_pdks c6d73a3; `options.stage_model_inputs` ships the repo-pinned models.

