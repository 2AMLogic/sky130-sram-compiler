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
and prints per-case rule counts (`summarize.py`). Compare against the record; a
changed count means a deck, PDK or klt change and warrants a new record.

The three-deck invocations themselves live in `design/bitcell/three_deck_drc.sh`,
shared with `design/bitcell/run_drc.sh` so the load-bearing deck flags have one
source; per-deck stderr is kept as `<case>.<deck>.err` and any deck/klt failure
aborts the run (klt exit-code contract: 0 clean, 3 violations, 4 `coverage_unknown`
are normal outcomes).

The `sky130A_mr.drc` run without the `--deck-var` trio that helper passes
silently checks nothing (`coverage_unknown`, 0 violations); the stripped-marker
foundry case is the control that proves it ran. `summarize.py` enforces this:
it prints `CONTROL ok/FAILED` and exits nonzero unless that case's mr deck
fired >0 violations.
