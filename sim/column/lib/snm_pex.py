#!/usr/bin/env python3
"""Opt-in extracted-DUT in-situ hold/read SNM harness (#210, provisional item-7 analog input).

Usage: python3 -I sim/column/lib/snm_pex.py (--snm-dut | --measure-snm-dut)
         [--klt CMD] [--outdir DIR] [--top TOP] [--pdk-root DIR] <dut.spice>
  --snm-dut          write col_{hold,read}_snm.sp and col_{hold,read}_snm.probe.request.json for
                     the DUT netlist into --outdir; run nothing.
  --measure-snm-dut  write the same four files, run both probes (`klt sim --backend local`, one
                     corner each) and print the `klt pex` measurement document (JSON) on stdout:
                     the `klt pex --measure-command` contract sim/column/run_snm_pex.sh relies on.
  --outdir DIR       default $KLT_PEX_ARTIFACTS_DIR, which `klt pex` sets for its measure command.

The DUT is a `.subckt <top>` (default sram_snm_halfcell_col64) handed over as the last argument:
the hierarchical LVS reference, or a flat device-only / parasitic-extracted netlist whose pins
`klt pex` renames and reorders. Pins are bound by name against the actual header and the 63
background cells' Q/QB nodes are located in the netlist, so the committed col_{hold,read}_snm
benches' DC sweep, precharge, WL0 bias and Q=0 / QB=1.8 `.nodeset` background
(make_column_tb.py::snm_tb) apply to every leg.

The sweep, timeout, trip point, saved vectors and probe request are make_column_tb's (SNM_SWEEP,
SNM_TIMEOUT_S, SNM_TRIP, SNM_SAVE, base_req, probe_of), imported here so both legs stay pinned to
one definition. This module is not in sim/testbench-inventory.json: keeping the extracted leg out
of make_column_tb.py spares evidence/item9.json a re-attestation on every iteration of it (#245).
"""
import argparse
import json
import math
import os
import pathlib
import re
import shlex
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from make_column_tb import ROWS, SNM_SWEEP, SNM_TIMEOUT_S, SNM_TRIP, SNM_SAVE, base_req, probe_of  # noqa: E402

SNM_DUT_TOP = "sram_snm_halfcell_col64"
SNM_DUT_PINS = ["BL0", "BLB0", "IN", "OUT", "PCHB", "VDD", "VSS"] + [f"WL{r}" for r in range(ROWS)]


def _logical_spice_lines(text):
    """Join SPICE '+' continuation lines into logical cards."""
    out = []
    for raw in text.splitlines():
        s = raw.strip()
        if s.startswith("+") and out:
            out[-1] += " " + s[1:].strip()
        else:
            out.append(s)
    return out


def _subckt_block(text, top=SNM_DUT_TOP):
    """Return (pins, body_lines) for `.subckt <top> ... .ends`."""
    lines = _logical_spice_lines(text)
    in_sub = False
    pins = None
    body = []
    for ln in lines:
        low = ln.lower()
        if not in_sub:
            if low.startswith(".subckt "):
                toks = ln.split()
                if len(toks) >= 2 and toks[1].lower() == top.lower():
                    pins = toks[2:]
                    in_sub = True
        else:
            if low.startswith(".ends"):
                break
            body.append(ln)
    if pins is None:
        raise ValueError(f"subckt {top} not found in netlist")
    return pins, body


def parse_subckt_pins(text, top=SNM_DUT_TOP):
    """Read `.subckt <top>` pin list in header order and verify it matches SNM_DUT_PINS."""
    pins, _ = _subckt_block(text, top)
    got = {p.upper() for p in pins}
    want = {p.upper() for p in SNM_DUT_PINS}
    if got != want or len(pins) != len(SNM_DUT_PINS):
        missing = sorted(want - got)
        extra = sorted(got - want)
        raise ValueError(f"{top} pin mismatch: missing={missing} extra={extra} (count {len(pins)} vs {len(SNM_DUT_PINS)})")
    return pins


def snm_dut_background_nodes(text, top=SNM_DUT_TOP):
    """Return the 63 background cells' (q_node, qb_node) inside `xdut` for .nodeset Q=0 / QB=1.8.

    Works unchanged on the hierarchical LVS reference (`XC1_0..XC63_0 ... bitcell_6t`), the
    flat parasitic-extracted netlist (resolving star-resistor terminal nodes to hub nets), and
    the flat parasitic-free `--device-only-leg` netlist.
    """
    _, body = _subckt_block(text, top)
    hier = {}
    for ln in body:
        toks = ln.split()
        if len(toks) >= 7 and toks[0].upper().startswith("XC") and toks[-1].lower() == "bitcell_6t":
            m = re.fullmatch(r"XC(\d+)_0", toks[0], re.I)
            if m:
                r = int(m.group(1))
                hier[r] = (f"xdut.xc{r}_0.q", f"xdut.xc{r}_0.qb")
    if len(hier) == ROWS - 1:
        return [hier[r] for r in range(1, ROWS)]

    # Flat netlist: resolve star-resistor terminal nodes (`<net>__t*`) to their hub net.
    term_to_hub = {}
    for ln in body:
        if ln and ln[0].upper() == "R":
            toks = ln.split()
            if len(toks) >= 4 and "__t" in toks[1]:
                term_to_hub[toks[1]] = toks[2]

    def hub(net):
        return term_to_hub.get(net, net)

    bl_q, blb_qb = {}, {}
    for ln in body:
        if not ln or ln[0].upper() not in ("X", "M"):
            continue
        toks = ln.split()
        if len(toks) < 6:
            continue
        d, g, s = hub(toks[1]), hub(toks[2]), hub(toks[3])
        gu = g.upper()
        if not re.fullmatch(r"WL[1-9]\d*", gu):
            continue
        du, su = d.upper(), s.upper()
        if du == "BL0":
            bl_q[gu] = s
        elif su == "BL0":
            bl_q[gu] = d
        elif du == "BLB0":
            blb_qb[gu] = s
        elif su == "BLB0":
            blb_qb[gu] = d

    missing = [f"WL{r}" for r in range(1, ROWS) if f"WL{r}" not in bl_q or f"WL{r}" not in blb_qb]
    if missing:
        raise ValueError(f"flat {top} missing background cell access nodes for {missing[:5]} (total {len(missing)})")
    return [(f"xdut.{bl_q[f'WL{r}'].lower()}", f"xdut.{blb_qb[f'WL{r}'].lower()}") for r in range(1, ROWS)]


def snm_dut_tb(mode, dut_path, top=SNM_DUT_TOP):
    """In-situ hold/read SNM bench instantiating `<top>` from `dut_path` (schematic, device-only or PEX).

    Binds every pin by name against `<top>`'s actual `.subckt` header so numeric and
    lexicographic pin orders bind identically. Keeps the same DC sweep, input scaling,
    precharge enable, WL0 bias, 63 background word lines at 0 V, and Q=0 / QB=1.8 background
    initialization as `snm_tb(mode, pair=False)`.
    """
    if mode not in ("hold", "read"):
        raise ValueError(f"mode must be 'hold' or 'read', got {mode!r}")
    dut_p = pathlib.Path(dut_path).resolve()
    text = dut_p.read_text()
    pins = parse_subckt_pins(text, top)
    bg_nodes = snm_dut_background_nodes(text, top)
    wl0 = "vdd" if mode == "read" else "0"
    pin_map = {"BL0": "bl0", "BLB0": "blb0", "IN": "in", "OUT": "out", "PCHB": "pchb",
               "VDD": "vdd", "VSS": "0", "WL0": wl0}
    for r in range(1, ROWS):
        pin_map[f"WL{r}"] = "0"
    bound = [pin_map[p.upper()] for p in pins]
    L = [f"* Extracted-DUT in-situ {mode.upper()} SNM on {top} ({dut_p.name})",
         "* Same DC sweep (VNRM 0 1 0.005, IN=nrm*VDD), precharge ON (PCHB=0), WL1..WL63=0,",
         f"* Q=0 / QB=1.8 background .nodeset on rows 1..63, and WL0={'VDD' if mode == 'read' else '0'}.",
         f".include '{dut_p}'",
         "VVDD vdd 0 dc 1.8",
         "VNRM nrm 0 dc 0",
         "BIN in 0 V='v(nrm)*v(vdd)'",
         "VPCHB pchb 0 dc 0",
         "XDUT " + " ".join(bound) + f" {top}"]
    for qn, qbn in bg_nodes:
        L.append(f".nodeset v({qn})=0 v({qbn})=1.8")
    return "\n".join(L) + "\n"


def snm_dut_probe_req(tb_name):
    """Single-corner (tt, 1.8 V, 25 C) local probe request matching col_{hold,read}_snm.probe.request.json."""
    r = base_req(tb_name, SNM_SWEEP, SNM_TRIP, SNM_SAVE)
    r["netlist"] = tb_name
    r["options"]["timeout_s"] = SNM_TIMEOUT_S
    return probe_of(r)


def extract_single_curve_snm(waveform_path):
    """Compute numeric (eye_snm, pinned_snm) from a single-curve waveform.raw.json.

    Raises ValueError if the curve is not bistable or either margin is non-finite / non-positive.
    """
    import snm_from_artifacts  # noqa: E402 -- lazy so PDK-free CI never needs sim/build/pinned/

    (plo, phi), (elo, ehi) = snm_from_artifacts.snm_for(waveform_path, pair=False)
    eye = min(elo, ehi)
    pinned = min(plo, phi)
    if not (isinstance(eye, (int, float)) and math.isfinite(eye) and eye > 0):
        raise ValueError(f"non-numeric or non-positive eye_snm: {eye!r}")
    if not (isinstance(pinned, (int, float)) and math.isfinite(pinned) and pinned > 0):
        raise ValueError(f"non-numeric or non-positive pinned_snm: {pinned!r}")
    return float(eye), float(pinned)


def _mode_measurements(mode, *, eye=None, pinned=None, vtrip=None, msg=None, vtrip_msg=None):
    """The `{mode}_{eye_snm,pinned_snm,vtrip}` rows one mode adds to the measurement document: a
    value is a `pass` row, a missing one an `error` row. `msg` is the eye/pinned rows' failure;
    `vtrip_msg` the vtrip row's own, which only a `klt sim` that produced no report at all has."""
    rows = []
    for key, value, why in (("eye_snm", eye, msg), ("pinned_snm", pinned, msg), ("vtrip", vtrip, vtrip_msg)):
        row = {"name": f"{mode}_{key}", "value": value, "status": "pass" if value is not None else "error",
               "unit": "V"}
        if why is not None:
            row["message"] = why
        rows.append(row)
    return rows


def measure_snm_dut(dut_path, outdir, klt_cmd=None, top=SNM_DUT_TOP, pdk_root=None):
    """Run hold + read SNM single-corner probes on `dut_path` and return a klt pex measurement document."""
    out = pathlib.Path(outdir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    klt_argv = shlex.split(klt_cmd) if klt_cmd else ["klt"]
    pdk_root = pdk_root or os.environ.get("PDK_ROOT")
    measurements = []
    corner_id = "tt/1.800V/25C"
    summary = {"side": os.environ.get("KLT_PEX_SIDE"), "dut_netlist": str(pathlib.Path(dut_path).resolve()),
               "top": top, "modes": {}}

    for mode in ("hold", "read"):
        tb_name = f"col_{mode}_snm.sp"
        req_name = f"col_{mode}_snm.probe.request.json"
        (out / tb_name).write_text(snm_dut_tb(mode, dut_path, top))
        req = snm_dut_probe_req(tb_name)
        if pdk_root:
            req["models"]["pdk_root"] = pdk_root
        (out / req_name).write_text(json.dumps(req, indent=2) + "\n")

        sim_out = out / mode
        cmd = klt_argv + ["sim", str(out / req_name), "--backend", "local", "-o", str(sim_out), "--format", "json"]
        t0 = time.monotonic()
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=SNM_TIMEOUT_S + 30)
            elapsed = round(time.monotonic() - t0, 3)
        except subprocess.TimeoutExpired:
            elapsed = round(time.monotonic() - t0, 3)
            msg = f"{mode} SNM probe exceeded {SNM_TIMEOUT_S}s budget (elapsed {elapsed:.1f}s)"
            summary["modes"][mode] = {"status": "timeout", "elapsed_s": elapsed, "message": msg}
            measurements += _mode_measurements(mode, msg=msg, vtrip_msg=msg)
            continue

        (out / f"{mode}.sim.stdout.json").write_text(proc.stdout)
        (out / f"{mode}.sim.stderr").write_text(proc.stderr)
        if proc.returncode != 0:
            msg = f"klt sim exited {proc.returncode}: {proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else 'no stderr'}"
            summary["modes"][mode] = {"status": "sim_error", "returncode": proc.returncode, "elapsed_s": elapsed, "message": msg}
            measurements += _mode_measurements(mode, msg=msg, vtrip_msg=msg)
            continue

        sim_rep = json.loads(proc.stdout)
        c0 = sim_rep["corners"][0]
        corner_id = c0.get("corner_id", corner_id)
        vtrip_rows = [m for m in c0.get("measurements", []) if m.get("name") == "vtrip"]
        vtrip = vtrip_rows[0].get("value") if vtrip_rows else None
        wfs = sorted(sim_out.glob("*/waveform.raw.json"))
        if len(wfs) != 1:
            msg = f"expected 1 waveform.raw.json under {sim_out}, found {len(wfs)}"
            summary["modes"][mode] = {"status": "waveform_error", "elapsed_s": elapsed, "message": msg}
            measurements += _mode_measurements(mode, vtrip=vtrip, msg=msg)
            continue

        try:
            eye, pinned = extract_single_curve_snm(wfs[0])
            wf = json.loads(wfs[0].read_text())
            names = [v["name"] for v in wf["variables"]]
            xi, yi = names.index("v(in)"), names.index("v(out)")
            pts = sorted((p[xi], p[yi]) for p in wf["points"])
            summary["modes"][mode] = {
                "status": "pass", "elapsed_s": elapsed, "points": len(pts),
                "v_out_at_0": pts[0][1], "v_out_at_vdd": pts[-1][1],
                "eye_snm_v": eye, "pinned_snm_v": pinned, "vtrip_v": vtrip,
            }
            measurements += _mode_measurements(mode, eye=eye, pinned=pinned, vtrip=vtrip)
        except Exception as exc:
            msg = f"SNM extraction failed: {exc}"
            summary["modes"][mode] = {"status": "snm_error", "elapsed_s": elapsed, "message": msg}
            measurements += _mode_measurements(mode, vtrip=vtrip, msg=msg)

    (out / "snm_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return {"corners": [{"corner_id": corner_id, "measurements": measurements}]}


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="snm_pex.py",
        description="In-situ hold/read SNM on an extracted or schematic DUT netlist (#210): write the "
                    "two single-corner probe benches, or also run them and print the klt pex "
                    "measurement document.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--snm-dut", action="store_true",
                   help="write col_{hold,read}_snm.sp and .probe.request.json for <dut.spice>; run nothing")
    g.add_argument("--measure-snm-dut", action="store_true",
                   help="write the same files, run both probes through `klt sim --backend local` and "
                        "print the measurement document (JSON) on stdout")
    ap.add_argument("--klt", metavar="CMD", help="klt launcher (default: klt)")
    ap.add_argument("--outdir", metavar="DIR",
                    help="output directory (default: $KLT_PEX_ARTIFACTS_DIR)")
    ap.add_argument("--top", default=SNM_DUT_TOP, metavar="TOP",
                    help="DUT subckt name (default: %(default)s)")
    ap.add_argument("--pdk-root", metavar="DIR",
                    help="models.pdk_root of the probe requests (default: $PDK_ROOT)")
    ap.add_argument("dut_spice", metavar="<dut.spice>", help="DUT netlist holding `.subckt <top>`")
    a = ap.parse_args(argv)
    outdir = a.outdir or os.environ.get("KLT_PEX_ARTIFACTS_DIR")
    if not outdir:
        ap.error("--outdir is required when KLT_PEX_ARTIFACTS_DIR is unset")
    if a.measure_snm_dut:
        doc = measure_snm_dut(a.dut_spice, outdir, klt_cmd=a.klt, top=a.top, pdk_root=a.pdk_root)
        print(json.dumps(doc))
        return
    out = pathlib.Path(outdir).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for mode in ("hold", "read"):
        tb_name = f"col_{mode}_snm.sp"
        (out / tb_name).write_text(snm_dut_tb(mode, a.dut_spice, a.top))
        (out / f"col_{mode}_snm.probe.request.json").write_text(
            json.dumps(snm_dut_probe_req(tb_name), indent=2) + "\n")
    print(f"snm_pex: wrote 4 extracted-DUT SNM files under {out}")


if __name__ == "__main__":
    main()
