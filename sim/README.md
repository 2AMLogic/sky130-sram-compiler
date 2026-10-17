# sim

Simulation environment and toolchain smoke bench. Nothing here sizes or draws
the design.

## Prerequisites

- `bash`, `python3`, `git`, `sha256sum`
- `ngspice` (recorded: ngspice-46) and `yosys` (recorded: 0.67) on `PATH`
- sky130A at the open_pdks revision pinned in [`pdk.json`](pdk.json), installed
  with ciel (or open_pdks / a direct checkout at that commit). `env.sh` finds
  it via `SKY130_PDK_PATH`, or `PDK_ROOT` (+ `PDK`), or `~/.ciel`, `~/.volare`,
  `/usr/share/pdk`, `/usr/local/share/pdk`, `~/share/pdk`, `/opt/pdk`.

## Cold start

```bash
git clone <this repo> && cd sky130-sram-compiler
source sim/env.sh      # resolves PDK_ROOT/PDK, checks the pin, prints paths
sim/smoke/run.sh       # one tt inverter (DC op + transient) + one Yosys synthesis
```

`env.sh` refuses with a named error (`PDK_NOT_FOUND`, `PDK_FILE_MISSING`,
`PDK_REVISION_UNKNOWN`, `PDK_REVISION_MISMATCH`, `PIN_FILE_MISSING`,
`PIN_FILE_INVALID`, `TOOL_MISSING`) and returns non-zero. Each successful
`run.sh` adds a new, never-overwritten record to `sim/smoke/records/`
holding the simulator version, PDK revision and deck hash. Records carry
identity only (variant and revision), never host paths.

The smoke run is a single local corner. Multi-corner and Monte Carlo work
goes through `klt sim`, not hand-written `ngspice` loops.

## Layout

| Path | Purpose |
|---|---|
| `pdk.json` | PDK pin: open_pdks revision, install method, model files |
| `env.sh` | Sourced resolver; refuses on pin mismatch |
| `smoke/` | Inverter deck, Yosys script and placeholder module, `run.sh`, `records/` |
| `build/` | Scratch output (gitignored) |

Variable names in `env.sh` follow `gf180-sram` `sim/lib/pdk_env.sh`
(`*_VARIANT_DIR`, `*_MODEL_FILE`, `*_PDK_VERSION`), so the adopted harness can
replace it. See `spec/decisions/0001-sim-env-resolver.md`.
