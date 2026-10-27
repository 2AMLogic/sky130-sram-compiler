# verification

| Directory | What |
|---|---|
| `marker/` | How klt's sky130 deck treats the SRAM core-area marker (`areaid.ce`, 81/2): inside, outside, edge (#6). |
| `drc/` | T1 item 3, DRC clean, for the 256 x 32 reference instance (#32): `run_drc.sh` runs the curated deck (graded) and the two PDK decks (disclosed) plus an `areaid.ce` scan and seam / negative controls; `make_record.py` writes the evidence envelopes and the dated record in `drc/records/`. |

Records are append-only: add a new dated file, never edit one.
