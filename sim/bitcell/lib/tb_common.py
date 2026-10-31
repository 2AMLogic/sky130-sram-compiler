"""Testbench-generator helpers shared by sim/bitcell/lib/make_tb.py and sim/column/lib/make_column_tb.py.

One copy of the corner grid, the pinned mismatch slope table and the `klt sim` request skeleton, so the
bitcell and column margin records stay comparable (methodology taken by reference from gf180-sram).
"""

PROCESS = ["tt", "ff", "ss", "sf", "fs"]
TEMPS = [-40, 25, 125]
VDDS = [1.62, 1.8, 1.98]

# Per-instance MOS mismatch in the sky130 `_mm` library sections is
#   param = nominal + MC_MM_SWITCH * AGAUSS(0, 1, 1) * (<device>__<param>_slope / sqrt(l*w*mult)),
# so every sigma scales linearly with these `.param` slopes. Values are the non-zero slopes of the pinned
# open_pdks f6eeac7 libs.ref/sky130_fd_pr/spice/sky130_fd_pr__{nfet,pfet}_01v8__mismatch.corner.spice.
MM_SLOPES = {
    "nfet_01v8": {"toxe_slope": "3.443e-03", "voff_slope": "0.007", "vth0_slope": "3.356e-03",
                  "vth0_slope1": "7.356e-03"},
    "pfet_01v8": {"toxe_slope": "4.443e-03", "toxe_slope1": "6.443e-03", "toxe_slope2": "3.443e-03",
                  "nfactor_slope": "0.1", "nfactor_slope1": "0.1", "voff_slope2": "0.007",
                  "vth0_slope": "5.856e-03", "vth0_slope1": "7.356e-03", "vth0_slope2": "4.356e-03"},
}


def mm_scale_params(scale):
    """`.param` lines (placed after the klt-injected `.lib`, so they win) scaling every mismatch sigma."""
    lines = [f"* NEGATIVE CONTROL: every per-instance mismatch sigma x {scale} (slope params of the pinned",
             "* open_pdks mismatch.corner files, x mm_scale); nominal parameters and process corner unchanged.",
             f".param mm_scale={scale}"]
    for dev, ps in MM_SLOPES.items():
        lines += [f".param sky130_fd_pr__{dev}__{k}='{v}*mm_scale'" for k, v in ps.items()]
    return "\n".join(lines) + "\n"


def with_params(body, params):
    """Insert `params` after the leading comment block of a testbench body."""
    lines = body.split("\n")
    i = 0
    while lines[i].startswith("*"):
        i += 1
    return "\n".join(lines[:i]) + "\n" + params + "\n".join(lines[i:])


def base_req(netlist, analysis, meas, extra_opts=None, mc=None, process=None, vdds=None, temps=None, *,
             timeout_s):
    opts = {"timeout_s": timeout_s, "stage_model_inputs": True, "waveforms": True, "keep_artifacts": True}
    opts.update(extra_opts or {})
    r = {
        "netlist": f"../tb/{netlist}", "engine": "ngspice",
        "models": {"pdk": "sky130A", "lib": "libs.tech/ngspice/sky130.lib.spice"},
        "corners": {"process": process or PROCESS, "supply_v": {"vvdd": vdds or VDDS},
                    "temperature_c": temps or TEMPS},
        "analysis": analysis, "measurements": meas, "options": opts,
    }
    if mc:
        r["monte_carlo"] = mc
    return r
