# design/bitcell

Logic-rule 6T bitcell, sky130A, ordinary 1.8 V devices (`nfet_01v8`, `pfet_01v8`).
Issue #7 (part of #2).

| File | What |
|---|---|
| `sizing.json` | The one sizing input (drawn W/L per device). Read by the schematic generator, the layout generator and `sim/bitcell/lib/make_tb.py`. |
| `gen_schematic.py` -> `bitcell_6t.sch` | xschem schematic (generated; do not hand-edit). |
| `netlist/bitcell_6t.spice` | `klt netlist --block` output of the schematic (first-line `sch_path` rewritten to a repo-relative path). |
| `gen_bitcell.py` -> `bitcell_6t.gds` | Layout generator (klayout python) and its committed output; regenerate with `uv run --no-project --with klayout python -I design/bitcell/gen_bitcell.py design/bitcell/bitcell_6t.gds` (deterministic: same bytes on a re-run). |
| `run_drc.sh` | The three DRC paths (curated deck, `sky130A.lydrc`, `sky130A_mr.drc`). |
| `lvs/` | `klt lvs` request and reference netlist. |
| `records/` | Dated, append-only DRC / LVS / area records. |

## Rules and marker

The cell is drawn to the ordinary (periphery) rules and carries **no** `areaid.ce`
(81/2) marker, per `verification/marker/records/2026-10-17-f22b400.md`: the marker
would relax li/licon/poly rules and let real logic-rule violations through. All
three decks therefore apply their strict rule set. `sky130A_mr.drc` is the only
one that is marker-aware; it was run with `--deck-var feol=true beol=true thr=1`.

## Cell

Vertical diffusion, horizontal poly: `nL | pL | pR | nR`. Pull-down + access share
one n strip (wide part PD, narrow part AX); the pull-up is the p strip. Q is routed
on li1 only; QB is li1 plus one met1 strap across the centre. Bit lines are
vertical met1, VDD vertical met2 (joined by a met2 strap), VSS is tied by a met3
rail, WL is the poly row. An n-tap sits in the nwell. There is **no p-substrate
tap**: the array must supply one, and LVS declares the substrate as the `vsubs`
pin (reported as `device.body_unverified`).

Not claimed: array abutment. The cell box is a pitch box chosen so mirrored copies
keep half-rule spacing, but no tiled array has been DRC'd, and the unshared
contacts leave area on the table versus a shared-contact variant. That belongs to
the array issue.
