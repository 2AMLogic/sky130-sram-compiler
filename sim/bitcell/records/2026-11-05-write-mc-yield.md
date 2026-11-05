# Write-trip MC: `klt yield` report (n=60 baseline)

Append-only addendum to `2026-10-18-write-mc-controls.md`, whose "klt yield" section recorded that the report could not run (klayout-tools#2900, since closed along with #4671). That record is unchanged. Determinism, negative and read/hold controls are in it; this record supplies only the missing yield report.

## Command

```
uvx --from "klayout-tools[yield]==0.9.0" klt yield \
  sim/bitcell/corners/20261018-mc-controls/write_trip_baseline.samples.json --format json \
  > sim/bitcell/corners/20261105-yield/write_trip_baseline.yield.json
```

- klt 0.9.0, run in a throwaway `uvx` environment (host tool untouched). Exit 0, status `reported`.
- Input: the 8 points x 60 lower-bound trip voltages of the n=60 baseline (mismatch only, seed 20261018), limit `min = 0 V`. 480 samples, 0 no-flip.
- Confidence 0.95, default target half-width 0.01. Full output: `corners/20261105-yield/write_trip_baseline.yield.json`.

## Result

| Point (corner / VDD / T) | n | mean trip lb (V) | stddev (V) | empirical yield, 95 % lower bound (Clopper-Pearson) | sigma to spec |
|---|---|---|---|---|---|
| fs_mm / 1.62V / -40C | 60 | 0.2928 | 0.0265 | 0.940 | 11.04 |
| fs_mm / 1.62V / 125C | 60 | 0.2126 | 0.0306 | 0.940 | 6.94 |
| fs_mm / 1.98V / -40C | 60 | 0.4538 | 0.0294 | 0.940 | 15.43 |
| fs_mm / 1.98V / 125C | 60 | 0.3393 | 0.0332 | 0.940 | 10.22 |
| sf_mm / 1.62V / -40C | 60 | 0.7147 | 0.0210 | 0.940 | 33.98 |
| sf_mm / 1.62V / 125C | 60 | 0.7256 | 0.0290 | 0.940 | 25.04 |
| sf_mm / 1.98V / -40C | 60 | 0.9333 | 0.0236 | 0.940 | 39.55 |
| sf_mm / 1.98V / 125C | 60 | 0.9405 | 0.0250 | 0.940 | 37.68 |

Worst point: fs_mm / 1.62 V / 125 C, sigma-to-spec 6.94 (Cpk 2.31, 95 % CI 1.89 to 2.74), matching the 6.9 sigma lower bound in `2026-10-18-write-mc-complete.md`.

## What this does and does not say

- No sample fell outside the limit at any point, so the empirical yield is bounded only from below: at least 94.0 % at 95 % confidence, N = 60 per point. It is not a 100 % yield claim.
- klt's sample-size verdict is `insufficient` at every point: N = 60 resolves the yield only to +/-0.0298; 183 samples are needed for +/-0.01. No larger run was made (out of scope).
- Anderson-Darling rejects normality at every point (A2* 7.6 to 12.4 vs critical 0.787), as klt warns. The normal-fit Cpk and sigma-to-spec are indicative only; the empirical bound above is the figure to cite.
- The input is a lower-bound ladder value (a quantised sample set, klayout-tools#2909 territory), not a continuous trip voltage; the statistics treat it as one.
- Mismatch only, no layout parasitics, `_mm` sections as in the baseline. The limit (trip > 0 V) is this repo's own, not a ratified gf180-sram threshold.
