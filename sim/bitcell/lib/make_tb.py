#!/usr/bin/env python3
"""Generate the bitcell testbench bodies and `klt sim` requests from design/bitcell/sizing.json.

Usage: python3 -I sim/bitcell/lib/make_tb.py [--check]
  --check  exit 1 if a committed file differs from what would be generated (sizing drift).

Margin definitions are taken by pinned reference from gf180-sram (see sim/bitcell/README.md):
  read / hold SNM : decoupled half-cell VTC sweep -> butterfly -> largest inscribed square.
  write margin    : write trip voltage, fixed 2 ns write pulse -- the weakest '0' on the losing
                    bit line that still flips the cell. gf180-sram finds it by bisection inside a
                    `.control` loop, which `klt sim` cannot express (it owns the .control block),
                    so here it is a 33-level ladder of independent trials inside ONE transient.
"""
import json
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parents[3]
sz = json.loads((root / "design/bitcell/sizing.json").read_text())

PROCESS = ["tt", "ff", "ss", "sf", "fs"]
TEMPS = [-40, 25, 125]
VDDS = [1.62, 1.8, 1.98]
LADDER = 33          # write-trip trial levels: VDD * k / (LADDER - 1)
TRIAL_NS = 8.0

files = {}


def dev(kind):
    return sz[kind]["model"], sz[kind]["w"], sz[kind]["l"]


def half_cell(tag, wl_expr, out, inp="in"):
    pm, pw, pl = dev("pu")
    nm, nw, nl = dev("pd")
    am, aw, al = dev("ax")
    return (f"XMP{tag} {out} {inp} vdd vdd sky130_fd_pr__{pm} w={pw} l={pl}\n"
            f"XMN{tag} {out} {inp} 0 0 sky130_fd_pr__{nm} w={nw} l={nl}\n"
            f"XMA{tag} bl {wl_expr} {out} 0 sky130_fd_pr__{am} w={aw} l={al}\n")


def snm_tb(mode, n_cells):
    wl = "wl" if mode == "read" else "0"
    cond = ("read: BL precharged to VDD, WL asserted to VDD" if mode == "read"
            else "hold: WL deasserted (0 V), BL precharged to VDD")
    head = (f"* {mode.upper()} SNM half-cell fixture body (circuit body for `klt sim`: no .control/.end).\n"
            f"* {cond}. One storage inverter + its access device, decoupled from the other\n"
            "* inverter; the sweep source is normalised (0..1) and scaled by VDD so one sweep\n"
            "* covers every supply corner. Sizes from design/bitcell/sizing.json (make_tb.py).\n"
            "VVDD vdd 0 dc 1.8\nVNRM nrm 0 dc 0\nBIN in 0 V='v(nrm)*v(vdd)'\nEBL bl 0 vdd 0 1\n")
    if mode == "read":
        head += "EWL wl 0 vdd 0 1\n"
    if n_cells == 1:
        body = half_cell("", wl, "out")
    else:  # two independently mismatched half cells, same input sweep (pair mode)
        body = half_cell("A", wl, "outa") + half_cell("B", wl, "outb")
    return head + body


def write_tb():
    n = LADDER
    t = TRIAL_NS
    e = 0.05  # 50 ps edges
    bl, blb, wl = [(0, 1.0)], [(0, 0.0)], [(0, 0.0)]
    for k in range(n):
        t0 = k * t
        lvl = k / (n - 1)
        # [0,2)  preset Q=1: BL=1, BLB=0, WL pulse 0.1..1.9
        # [2,4)  idle, bit lines precharged
        # [4,6)  trial: BLB=1, BL=lvl, 2 ns WL pulse (50 % points at 4.0 and 6.0)
        # [6,8)  idle, precharged; Q sampled at 7.9
        bl += [(t0 + 0.1, 1.0), (t0 + 2.0, 1.0), (t0 + 2.0 + e, 1.0),
               (t0 + 4.0 - e, 1.0), (t0 + 4.0, lvl), (t0 + 6.0, lvl), (t0 + 6.0 + e, 1.0), (t0 + t, 1.0)]
        blb += [(t0 + 0.1, 0.0), (t0 + 2.0, 0.0), (t0 + 2.0 + e, 1.0),
                (t0 + 4.0, 1.0), (t0 + 6.0, 1.0), (t0 + t, 1.0)]
        wl += [(t0 + 0.1, 0.0), (t0 + 0.1 + e, 1.0), (t0 + 1.9, 1.0), (t0 + 1.9 + e, 0.0),
               (t0 + 4.0 - e / 2, 0.0), (t0 + 4.0 + e / 2, 1.0), (t0 + 6.0 - e / 2, 1.0),
               (t0 + 6.0 + e / 2, 0.0), (t0 + t, 0.0)]

    def pwl(name, pts):
        # last writer wins for a repeated time stamp
        d = {}
        for a, b in pts:
            d[round(a, 4)] = b
        s = " ".join(f"{a:g}n {b:g}" for a, b in sorted(d.items()))
        return f"{name} PWL({s})"

    lines = [
        "* WRITE trip-voltage ladder: full cell (schematic subckt), 33 independent trials in one transient.",
        "* Each trial: preset Q=1 with a full write, idle, then a 2 ns WL pulse with BLB=VDD and",
        "* BL=VDD*k/32; Q is sampled 0.1 ns before the next trial. Write trip voltage = the highest",
        "* BL level that still flipped the cell (Q < VDD/2).",
        ".include '../../../design/bitcell/netlist/bitcell_6t.spice'",
        "VVDD vdd 0 dc 1.8",
        pwl("VBLF blf 0", bl), pwl("VBLBF blbf 0", blb), pwl("VWLF wlf 0", wl),
        "BBL bl 0 V='v(blf)*v(vdd)'", "BBLB blb 0 V='v(blbf)*v(vdd)'", "BWL wl 0 V='v(wlf)*v(vdd)'",
        "XDUT bl blb wl vdd 0 bitcell_6t",
    ]
    return "\n".join(lines) + "\n"


def base_req(netlist, analysis, meas, extra_opts=None, mc=None, process=None, vdds=None, temps=None):
    opts = {"timeout_s": 600, "stage_model_inputs": True, "waveforms": True, "keep_artifacts": True}
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


def build():
    for mode in ("read", "hold"):
        files[f"tb/{mode}_snm.sp"] = snm_tb(mode, 1)
        files[f"tb/mc_{mode}_snm.sp"] = snm_tb(mode, 2)
    files["tb/write_trip.sp"] = write_tb()
    sweep = {"kind": "dc", "args": "VNRM 0 1 0.005"}
    keep = {"save_vectors": ["v(in)", "v(out)"]}
    keep2 = {"save_vectors": ["v(in)", "v(outa)", "v(outb)"]}
    trip = [{"name": "vtrip", "spice": ".meas dc vtrip when v(out)=0.9 fall=1", "unit": "V"}]
    for mode in ("read", "hold"):
        files[f"requests/{mode}_snm_corners.request.json"] = base_req(
            f"{mode}_snm.sp", sweep, trip, keep)
        mc = {"n": 60, "seed": 20261018, "vary": "mismatch", "k_sigma": 3}
        files[f"requests/mc_{mode}_snm.request.json"] = base_req(
            f"mc_{mode}_snm.sp", {"kind": "dc", "args": "VNRM 0 1 0.01"},
            [{"name": "vtrip_a", "spice": ".meas dc vtrip_a when v(outa)=0.9 fall=1", "unit": "V"}],
            keep2, mc=mc, process=["tt_mm", "sf_mm", "fs_mm"], vdds=[1.62, 1.98], temps=[125])
        files[f"requests/mc_{mode}_snm.request.json"]["batch"] = {"max_units_per_job": 36, "poll_timeout_s": 5400}
        files[f"requests/mc_{mode}_snm.request.json"]["options"]["timeout_s"] = 90
    meas = []
    for k in range(LADDER):
        ts = k * TRIAL_NS + TRIAL_NS - 0.1
        meas.append({"name": f"q{k:02d}",
                     "spice": f".meas tran q{k:02d} find v(xdut.q) at={ts:g}n", "unit": "V"})
    files["requests/write_trip_corners.request.json"] = base_req(
        "write_trip.sp", {"kind": "tran", "args": f"0.02n {LADDER * TRIAL_NS:g}n"}, meas,
        {"waveforms": False, "keep_artifacts": False})


def main():
    build()
    bad = 0
    for rel, content in files.items():
        p = root / "sim/bitcell" / rel
        text = content if isinstance(content, str) else json.dumps(content, indent=2) + "\n"
        if "--check" in sys.argv:
            if not p.exists() or p.read_text() != text:
                print("DRIFT", rel)
                bad = 1
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
    return bad


if __name__ == "__main__":
    sys.exit(main())
