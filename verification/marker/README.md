# verification/marker

Cold-start checks for how klt's sky130 decks treat the SRAM core-area marker
(`areaid.ce`, GDS 81/2). Evidence lives in `records/<date>-<sha>.md`
(append-only; add a new record, never edit an old one).

```
./run_checks.sh /tmp/marker-out     # scratch dir OUTSIDE the repo
```

Needs `klt` on PATH, a sky130A PDK under `~/.ciel` (override with `PDK=<.../sky130A>`)
and the standalone `klayout` for `--engine klayout`. It builds the cases
(`build_cases.py`: foundry bitcell with / without / half marker; `nand2_1` and a
synthetic li probe at inside / outside / edge), runs each through three decks
(curated `--deck sky130`; PDK `sky130A.lydrc`; PDK `sky130A_mr.drc` with
`--deck-var feol=true --deck-var beol=true --deck-var thr=1`) and prints per-case
rule counts (`summarize.py`). Compare against the record; a changed count means
a deck, PDK or klt change and warrants a new record.

The `sky130A_mr.drc` run without those `--deck-var`s silently checks nothing
(`coverage_unknown`, 0 violations); the stripped-marker foundry case is the
control that proves it ran.
