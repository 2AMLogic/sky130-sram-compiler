# Bitcell sizing exploration (read SNM, 30 corners per candidate)

Issue: 2AMLogic/sky130-sram-compiler#7. Append-only: add a new dated record, never edit this one.

Method: the `read_snm` half-cell fixture (same body as `sim/bitcell/tb/read_snm.sp`, sizes substituted),
one `klt sim` request per candidate to the batch fleet (`--batch-set`; the fleet image ignores
`corners.params`, klayout-tools#3878), models staged from the repo-pinned PDK. 30 corners per candidate:
{tt,ff,ss,sf,fs} x {-40,25,125 C} x {1.62,1.98 V}. SNM is `eye_snm` (largest inscribed square,
`sim/bitcell/lib/snm_from_artifacts.py`). The candidate requests were generated into a scratch directory
and are not committed; the chosen row is the one committed as `design/bitcell/sizing.json`.

| id | PD W/L | AX W/L | PU W/L | cell ratio PD/AX | min read eye SNM (V) | at |
|---|---|---|---|---:|---:|---|
| c0 | 0.42/0.15 | 0.42/0.15 | 0.42/0.15 | 1.0 | 0.131 | sf / 1.98 V / 125 C |
| **c1 (chosen)** | 0.84/0.15 | 0.42/0.15 | 0.42/0.15 | 2.0 | 0.264 | sf / 1.62 V / 125 C |
| c2 | 0.64/0.15 | 0.42/0.15 | 0.42/0.15 | 1.5 | 0.228 | sf / 1.62 V / 125 C |
| c3 | 1.00/0.15 | 0.42/0.15 | 0.42/0.18 | 2.4 | 0.313 | sf / 1.62 V / 125 C |
| c4 | 0.64/0.15 | 0.42/0.18 | 0.42/0.15 | 1.8 | 0.292 | sf / 1.62 V / 125 C |
| c5 | 0.84/0.15 | 0.42/0.18 | 0.42/0.15 | 2.4 | 0.277 | sf / 1.62 V / 125 C |

Choice: c1. Every candidate has a strictly positive read SNM at all 30 corners, so read SNM alone does
not discriminate. c1 was kept because (a) it is the smallest-L-everywhere option with a comfortable
margin, and (b) a narrower pull-down saves no layout width here: the column pitch of the n strip is set
by the bit-line and VSS contact columns, not by the pull-down gate width (c2 was drawn: it failed met1
spacing at the BL / VSS columns and gave no area back), and a longer access gate (c4, c5) would trade
write margin, which was **not** explored for these candidates.

Not done: no write-margin or hold-SNM comparison across candidates (hold does not depend on the access
device and was only run for c1); no Monte Carlo ranking of candidates. c1 is the only sizing carried to
the 45-corner and Monte Carlo evidence (see the dated margin record in this directory).
