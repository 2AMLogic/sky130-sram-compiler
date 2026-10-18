# Bitcell write-trip Monte Carlo record 2026-10-18-write-mc-complete (98c79e4)

Issue: 2AMLogic/sky130-sram-compiler#14 (follows #7). Append-only: add a new dated record, never edit this one. The 45-corner deterministic record `20261018-040941-91ba071.md` is not edited; this record adds the mismatch evidence that record's Limits say is missing.

## Provenance

- sizing (drawn W/L, um): PD 0.84/0.15 nfet_01v8, AX 0.42/0.15 nfet_01v8, PU 0.42/0.15 pfet_01v8 (design/bitcell/sizing.json)
- request `sim/bitcell/requests/mc_write_trip.request.json`; testbench `sim/bitcell/tb/mc_write_trip.sp` (full 6T cell, schematic subckt `bitcell_6t`, per-instance mismatch via the `_mm` library sections)
- Monte Carlo: n=60 samples per point, seed=20261018, vary=mismatch, k_sigma=3.0
- backend: batch fleet; batch job ids in the input reports `sim/bitcell/corners/20261018-write-mc/mc_write_trip.report.json.gz` (base), `sim/bitcell/corners/20261018-write-mc-complete/mc_write_trip.report1.json.gz` (`environment.remote` carries fleet, job_ceiling keys; job ids are printed by klt on stderr only); models staged from the repo-pinned PDK (`options.stage_model_inputs`)
- klt: 0.7.1.dev1865+g1c5546271c61

## Grading bar (taken by reference from gf180-sram, not redesigned)

gf180-sram `spec/sram.md` § Characterization (ratified by `spec/statistical-treatment-decision.md`, read at commit `74ba8a621c9e`, the same commit the read/hold margin definitions are pinned to): write margin is a statistical row, graded against the limit **margin > 0 at every corner**; no numeric `target_yield` is ratified there, so none is invented here. Its recorded statistics are sigma-to-spec (mean/sigma against the limit), the exact Clopper-Pearson empirical-yield lower bound, a determinism control and a negative control, N = 200 per point. `reuse.lock.json` is not on `main` yet (PR #12 adds the gf180-sram pin), so this is a by-commit citation. Here the limit is the trip voltage > 0 V, i.e. the cell flips with the losing bit line driven fully to 0 V (ladder level k = 0); a sample that does not flip at k = 0 is a write failure.

## Interval censoring of the ladder (stated choice)

The ladder is **not refined**. Each sample's trip voltage is only known to lie in [VDD*k*/32, VDD*(k*+1)/32), k* the highest flipping level (step VDD/32 = 51 mV at 1.62 V, 62 mV at 1.98 V). Three estimates are reported: the *lower bound* (VDD*k*/32, the conservative value, equal to the quantity recorded in the 45-corner table), the *midpoint* (k*+0.5 steps), and sigma of the midpoint with the quantisation variance step^2/12 removed (Sheppard correction; valid only when the true spread is not small against the step). `sigmas-to-failure` is mean/sigma against 0 V computed from (a) the lower-bound samples and (b) the Sheppard-corrected midpoint estimate. A sample with no flip at any level has trip < 0 and is counted in `no-flip`; it enters the lower-bound statistics at 0 V (a bound in the pessimistic direction for the mean only).

## Results

| process | VDD (V) | T (C) | units requested | n valid | no-flip | non-monotone | mean trip, lower bound (V) | sigma (V) | min (V) | mean trip, midpoint (V) | sigmas-to-failure (lower bound) | sigmas-to-failure (Sheppard midpoint) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fs_mm | 1.62 | -40 | 60 | 60 | 0 | 0 | 0.293 | 0.027 | 0.253 | 0.318 | 11.0 | 14.4 |
| fs_mm | 1.62 | 125 | 60 | 60 | 0 | 0 | 0.213 | 0.031 | 0.152 | 0.238 | 6.9 | 8.8 |
| fs_mm | 1.98 | -40 | 60 | 60 | 0 | 0 | 0.454 | 0.029 | 0.433 | 0.485 | 15.4 | 20.7 |
| fs_mm | 1.98 | 125 | 60 | 60 | 0 | 0 | 0.339 | 0.033 | 0.247 | 0.370 | 10.2 | 13.2 |
| sf_mm | 1.62 | -40 | 60 | 60 | 0 | 0 | 0.715 | 0.021 | 0.658 | 0.740 | 34.0 | 48.9 |
| sf_mm | 1.62 | 125 | 60 | 60 | 0 | 0 | 0.726 | 0.029 | 0.658 | 0.751 | 25.0 | 30.0 |
| sf_mm | 1.98 | -40 | 60 | 60 | 0 | 0 | 0.933 | 0.024 | 0.866 | 0.964 | 39.5 | 62.5 |
| sf_mm | 1.98 | 125 | 60 | 60 | 0 | 0 | 0.941 | 0.025 | 0.928 | 0.971 | 37.7 | 55.7 |

## Conclusion

No sample failed to flip (0 no-flip over 480 valid samples), and the lowest lower-bound sigmas-to-failure over the 8 points is 6.9. No mismatch-driven write failure is observed at these points at n = 60 (the smallest margin, fs / 1.62 V / 125 C, is 6.9 sigma on the lower-bound estimate); the sizing in `design/bitcell/sizing.json` (access / pull-up ratio) is unchanged and no lever is named. This is not a graded yield claim: the determinism control, negative control and `klt yield` report are out of this record (below).

## Compared with 2026-10-18-write-mc.md

Base report: `sim/bitcell/corners/20261018-write-mc/mc_write_trip.report.json.gz` (the partial first look). Merge rule: samples are keyed by (point, sample index) = `corner_id`; the valid ladders of the base report are kept, units re-run in the later report fill only the indices that had none, and no index is counted twice. The request and seed 20261018 are unchanged, so a re-run index is the same mismatch draw.

Determinism of the draw: of the 130 indices valid in the base report, 130 reproduce the identical ladder in the later report.

- fs_mm / 1.62 V / -40 C: n valid 15 -> 60; lower-bound mean 0.297 -> 0.293 V, min 0.253 -> 0.253 V, sigmas-to-failure (lower bound) 16.7 -> 11.0
- fs_mm / 1.62 V / 125 C: n valid 15 -> 60; lower-bound mean 0.219 -> 0.213 V, min 0.203 -> 0.152 V, sigmas-to-failure (lower bound) 8.9 -> 6.9
- fs_mm / 1.98 V / -40 C: n valid 5 -> 60; lower-bound mean 0.446 -> 0.454 V, min 0.433 -> 0.433 V, sigmas-to-failure (lower bound) 16.1 -> 15.4
- fs_mm / 1.98 V / 125 C: n valid 15 -> 60; lower-bound mean 0.334 -> 0.339 V, min 0.247 -> 0.247 V, sigmas-to-failure (lower bound) 8.5 -> 10.2
- sf_mm / 1.62 V / -40 C: n valid 15 -> 60; lower-bound mean 0.722 -> 0.715 V, min 0.709 -> 0.658 V, sigmas-to-failure (lower bound) 31.2 -> 34.0
- sf_mm / 1.62 V / 125 C: n valid 20 -> 60; lower-bound mean 0.744 -> 0.726 V, min 0.709 -> 0.658 V, sigmas-to-failure (lower bound) 31.3 -> 25.0
- sf_mm / 1.98 V / -40 C: n valid 25 -> 60; lower-bound mean 0.936 -> 0.933 V, min 0.928 -> 0.866 V, sigmas-to-failure (lower bound) 45.6 -> 39.5
- sf_mm / 1.98 V / 125 C: n valid 20 -> 60; lower-bound mean 0.937 -> 0.941 V, min 0.928 -> 0.928 V, sigmas-to-failure (lower bound) 41.4 -> 37.7

## Limits of this record

- 480 units over 8 points; fs and sf `_mm` sections at 1.62 / 1.98 V and -40 / 125 C only, not the 45-corner set. tt/ff/ss and 1.80 V were not run; no pooled estimate across points.
- n = 60 valid samples at every point (gf180-sram's recipe asks N = 200; n = 60 was chosen because the lowest sigmas-to-failure in the partial table were 8.5 to 12.3, which settles whether a mismatch write failure is plausible, at 3.3x fewer units on a fleet at its concurrency cap). Sigma has relative sampling error about 1/sqrt(2(n-1)) = 9 %, and a zero no-flip count bounds the empirical failure rate only from above (rule of three: at 95 % confidence p < 0.05 per point).
- No determinism control (mismatch off reproducing the deterministic corner) and no negative control (known-bad mismatch scale) were run, and no `klt yield` report was produced, so gf180-sram's full statistical-evidence recipe is not met. The deterministic 45-corner table is the consistency reference.
- Fixed 2 ns write pulse, a single write-pulse width; the trip voltage is not a write-time margin. No layout parasitics (no PEX).
- The fleet image PDK is open_pdks c6d73a3; `options.stage_model_inputs` ships the repo-pinned models (worker `pdk.models_staged` in the report).

