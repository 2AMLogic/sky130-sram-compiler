# design

| Path | What |
|---|---|
| `bitcell/` | Logic-rule 6T bitcell (#7): generator, schematic, netlist, layout. |
| `compiler/` | SRAM compiler netlist path (#26): periphery generator and `(words, bits, mux)` -> macro netlist. |
| `sky130_pdk.py` | PDK-derived values both of the above import: the GDS layer table, the shared drawing rules and the xschem device-geometry formula. One source of truth, so layout and netlist cannot drift apart. |

## Regenerate the 256 x 32 reference netlist

```console
python3 -I design/compiler/sram_compile.py 256 32 4 -o design/compiler/macro/sram_256x32_m4.spice
```

Deterministic: byte-identical on every run. The full chain (schematics, per-cell
netlists, macro, T1 item 1 evidence) is in `compiler/README.md`.
