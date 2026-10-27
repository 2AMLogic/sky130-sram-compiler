# layout

## control/ — routed control block (T1 item 2, digital)

`layout/control/` holds the place-and-route of the synthesized `sram_ctrl`
256 x 32 control netlist (`rtl/synth/sram_ctrl_256x32_synth.v`) with
`klt place-and-route` on `sky130_fd_sc_hd` / `tt_025C_1v80` (same pin as
`rtl/synth/request.json` and `sim/pdk.json`).

| File | Role |
| --- | --- |
| `place-and-route.request.json` | the request: utilization floorplan, `sky130hd` PDN preset (tapcell + straps + fillers), `target_stage: route`, `seed: 1` |
| `run_pnr.sh` | reproducible wrapper; `--check` runs the flow twice and requires both GDS identical to each other and to the committed one (exit 3 on drift) |
| `control.gds`, `control.gds.sha256` | committed routed stream and its hash |
| `place-and-route.response.json` | committed P&R response (`power.pdn: true`, named `power.tapcell_master`); item 11 consumes it |

Regenerate: `layout/control/run_pnr.sh`; verify: `layout/control/run_pnr.sh --check`.
The wrapper runs klt from the repo root on purpose: the `openroad` on `PATH`
is a container that mounts only its working directory, so the netlist
(outside `layout/control/`) is only visible from the root.

Assumed floorplan (the macro edge is not defined while `partition_boundary`
is a placeholder pending #2): a free-standing core with the four
analog-facing control outputs (`pch`, `wl_en`, `sae`, `wen`) pinned to the
south edge; all other pins are placed by the tool. Pin side and die area
should follow the control-signal mapping (#38) once written. The 10 ns clock
period is a placeholder, not a spec value; timing closure is out of scope.

The as-built netlist with CTS buffers (`verilog_path` in the response) is the
LVS reference for #33, not the pre-CTS `rtl/synth` netlist.
