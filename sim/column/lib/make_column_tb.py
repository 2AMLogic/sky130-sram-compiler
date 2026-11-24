#!/usr/bin/env python3
"""Generate the column testbench bodies and `klt sim` requests (T1 item 9, analog partition).

Usage: python3 -I sim/column/lib/make_column_tb.py [--check]
  --check  exit 1 if a committed file differs from what would be generated (macro/sizing drift).

Every bench instantiates one *bit slice* of the compiled 256 x 32 macro (mux 4 = 64 rows x 128
columns): 4 physical columns x 64 real `bitcell_6t` instances, one `sram_precharge` and one
`sram_colmux` per column, and one `sram_senseamp` + `sram_wdrv` (+ the SAEB inverter) shared by the
four columns, wired as in `sram_256x32_m4` (see design/compiler/macro). All subckts come from the
compiled macro netlist (`.include`), nothing is hand copied; the half-cell devices of the SNM
fixtures are read out of the macro's `bitcell_6t` subckt here.

Benches
  col_read0 / col_read1   read access: SAE-delay ladder (0.0 .. 2.4 ns) on the accessed cell storing 0 / 1
                          with every other cell of the slice storing the opposite (worst-case leakage);
                          per trial: DOUT, sense-bit-line differential, cell state; plus Q/QB bump
                          (read disturb) and half-select retention over the whole run.
  col_write0 / col_write1 write completion: write-pulse-width ladder (WL and WEN together) writing 0 / 1
                          through wdrv -> colmux -> bit line into a restored cell; per trial the cell
                          state after the pulse; half-select retention over the whole run.
  col_write0_nowen        negative control: the same ladder with WEN never asserted; no trial may flip.
  col_read_snm / col_hold_snm (+ mc_*, mc_*_neg)
                          in-situ SNM: the decoupled half cell of margin definition (gf180-sram @
                          74ba8a62, see sim/bitcell/README.md) whose bit line is the real column:
                          precharge ON plus 63 further bitcells on it (WL = 0). Corners, Monte Carlo
                          (two mismatched half cells) and the x6-sigma negative control as in sim/bitcell.
Pre-layout: no bit-line/word-line wire parasitics; the 124 other columns' word-line load is the gate
area of their access devices (248 NMOS gates, m=248). Strobe edges are ideal 50 ps ramps.
"""
import functools
import json
import math
import os
import pathlib
import re
import shlex
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "bitcell/lib"))
import tb_common  # noqa: E402
from tb_common import mm_scale_params, with_params  # noqa: E402

root = pathlib.Path(__file__).resolve().parents[3]
MACRO = "design/compiler/macro/sram_256x32_m4.spice"
INC = f"../../../{MACRO}"

ROWS, COLS = 64, 4          # 256 x 32, mux 4: 64 rows; one bit slice = 4 columns
E = 0.05                    # strobe edge, ns
T_START = 3.0               # first trial after the initialisation phase, ns
# SAE delay after WL, ns: 0.00 .. 1.00 step 0.05, then 1.2 .. 2.4
READ_D = [round(0.05 * k, 3) for k in range(21)] + [1.2, 1.4, 1.6, 1.8, 2.0, 2.4]
# WL/WEN pulse width, ns: 0.05 .. 0.80 step 0.05, then 1.0 .. 2.0
WRITE_W = [round(0.05 * (k + 1), 3) for k in range(16)] + [1.0, 1.25, 1.5, 2.0]
TRAN_STEP = "0.04n"
# Monte Carlo / controls: same parameters as sim/bitcell (make_tb.py)
MC_N, MC_SEED = 60, 20261018
NEG_N, NEG_SEED, NEG_SCALE = 20, 20261019, 6

# ----------------------------------------------------------------- batch sizing
# The fleet's whole-job ceiling and per-job overhead, as klt's own batch client
# models them: `DEFAULT_BATCH_MAX_JOB_SECONDS` = 3600.0 and `_BATCH_JOB_OVERHEAD_S`
# = 120.0 in `klayout_tools/sim_batch.py`. A job's bound is every unit burning its
# full `options.timeout_s` one after another plus the overhead, and it must stay
# inside the ceiling, so the largest shard the client accepts is
# floor((3600 - 120) / timeout_s) -- the formula `klt sim` states in its own
# `batch_max_units_per_job_invalid` refusal. Derived here, never written as a
# literal, so a `timeout_s` change cannot leave a stale cap behind.
BATCH_MAX_JOB_S = 3600
BATCH_JOB_OVERHEAD_S = 120
# A capped request shards and `klt sim` submits every shard at once, so each
# capped request also bounds the jobs in flight. These jobs take one 16-vCPU
# m7i.4xlarge each, and `BATCH_MAX_VCPU` = 224 (2AMLogic/2am
# `infra/aws/batch-fleet.env`, "224 = 7 x 32 or 14 x 16") is this execution
# layer's whole share of the account's spot vCPU quota -- 14 such instances is
# the entire layer, shared with every other block's sweeps. Half of that is the
# self-limit: under `BATCH_VCPU_BUDGET_MODE=enforce` a request holding the whole
# budget refuses everyone else's launches. The instance cap
# (`BATCH_MAX_CONCURRENT_INSTANCES` = 50) is the looser second bound.
BATCH_MAX_CONCURRENT_JOBS = 7

files = {}


def max_units_per_job(timeout_s):
    """Largest `batch.max_units_per_job` the fleet's whole-job ceiling allows at `timeout_s`."""
    cap = int((BATCH_MAX_JOB_S - BATCH_JOB_OVERHEAD_S) // timeout_s)
    if cap < 1:
        sys.exit(f"make_column_tb: options.timeout_s {timeout_s:g} leaves no room inside the "
                 f"{BATCH_MAX_JOB_S} s whole-job ceiling ({BATCH_JOB_OVERHEAD_S} s overhead)")
    return cap


def batch_block(req, poll_timeout_s):
    """`request.batch` for `req`: the cap derived from its own `options.timeout_s`, plus the
    concurrency bound the resulting shards need. Call after `options.timeout_s` is final."""
    return {"max_units_per_job": max_units_per_job(req["options"]["timeout_s"]),
            "max_concurrent_jobs": BATCH_MAX_CONCURRENT_JOBS,
            "poll_timeout_s": poll_timeout_s}


def macro_subckt(name):
    text = (root / MACRO).read_text()
    m = re.search(rf"^\.subckt {name} .*?^\.ends", text, re.S | re.M)
    if not m:
        sys.exit(f"make_column_tb: subckt {name} not found in {MACRO}")
    return m.group(0)


def bitcell_devices():
    """(model, W, L) of the pull-up, pull-down and access device of the macro's bitcell_6t."""
    body = macro_subckt("bitcell_6t")
    out = {}
    for key, inst in (("pu", "XMPL"), ("pd", "XMNL"), ("ax", "XMAL")):
        m = re.search(rf"^{inst} \S+ \S+ \S+ \S+ sky130_fd_pr__(\w+) L=([\d.]+) W=([\d.]+)", body, re.M)
        if not m:
            sys.exit(f"make_column_tb: {inst} not found in bitcell_6t")
        out[key] = (m.group(1), m.group(3), m.group(2))
    return out


# ------------------------------------------------------------------ PWL helpers
def pwl(name, intervals, init=0.0, active=1.0):
    """PWL source `name` that is `active` inside each (t_on, t_off) interval (ns) and `init` elsewhere."""
    pts = {0.0: init}
    for a, b in intervals:
        pts[round(a, 4)] = pts.get(round(a, 4), init)
        pts[round(a + E, 4)] = active
        pts[round(b, 4)] = active
        pts[round(b + E, 4)] = init
    s = " ".join(f"{t:g}n {v:g}" for t, v in sorted(pts.items()))
    return f"V{name.upper()} {name} 0 PWL({s})"


def drive(node, ctrl, invert=False):
    """Behavioural driver: node = VDD * ctrl (or VDD * (1 - ctrl))."""
    expr = f"(1-v({ctrl}))*v(vdd)" if invert else f"v({ctrl})*v(vdd)"
    return f"B{node.upper()} {node} 0 V='{expr}'"


# ------------------------------------------------------------------ slice netlist
def slice_netlist():
    """Bit slice body. Returns lines. Cell (r, c) is instance xc{r}_{c}; row 0 word line is `wl0`
    (real sram_wldrv driven from `wlin0`, plus the gate load of the other 124 columns), rows 1.. share `wlo`."""
    L = [f".include '{INC}'", "VVDD vdd 0 dc 1.8"]
    for r in range(ROWS):
        for c in range(COLS):
            L.append(f"XC{r}_{c} bl{c} blb{c} {'wl0' if r == 0 else 'wlo'} vdd 0 bitcell_6t")
    L += ["XWLDRV wlin0 wl0 vdd 0 sram_wldrv",
          f"XWLLOAD 0 wl0 0 0 sky130_fd_pr__nfet_01v8 L=0.15 W=0.42 m={2 * (128 - COLS)}",
          "* rows 1..63 share an ideal word line (never asserted after initialisation)"]
    for c in range(COLS):
        L += [f"XPCH{c} bl{c} blb{c} pchb vdd sram_precharge",
              f"XCM{c} bl{c} blb{c} sbl sblb cs{c} 0 sram_colmux"]
    L += ["XSAINV sae saeb vdd 0 sram_inv", "XSA sbl sblb sae saeb dout vdd 0 sram_senseamp",
          "XWD sbl sblb din wen vdd 0 sram_wdrv"]
    return L


def common_sources(wl0_iv, wlo_iv, pchb_low_iv, cs_iv, sae_iv, wen_iv, din):
    L = [pwl("wl0f", wl0_iv), drive("wlin0", "wl0f", invert=True),
         pwl("wlof", wlo_iv), drive("wlo", "wlof"),
         pwl("pchbf", pchb_low_iv, init=1.0, active=0.0), drive("pchb", "pchbf"),
         pwl("saef", sae_iv), drive("sae", "saef"),
         pwl("wenf", wen_iv), drive("wen", "wenf"), f"BDIN din 0 V='{din}*v(vdd)'"]
    for c in range(COLS):
        L += [pwl(f"csf{c}", cs_iv[c]), drive(f"cs{c}", f"csf{c}")]
    return L


def meas_find(name, expr, t):
    return {"name": name, "spice": f".meas tran {name} find {expr} at={t:g}n", "unit": "V"}


# ------------------------------------------------------------------ read benches
def read_tb(d):
    """Accessed cell (row 0, col 0) stores d; all other slice cells store 1-d; col 1/2/3 row 0
    (half selected) store 1-d, d, 1-d."""
    data = [d, 1 - d, d, 1 - d]       # row 0 of cols 0..3 (for the row-0 re-init)
    others = 1 - d
    # init phase 1: every row's WL high, all columns forced to `others`; phase 2: row 0 only, forced to `data`.
    ctl = {c: [(0.1, 2.3)] for c in range(COLS)}
    L = [f"* READ{d} access bench: SAE-delay ladder on a 64-row x 4-column bit slice of {MACRO}.",
         f"* Cell (0,0) stores {d}, every other cell of the column/slice stores {1 - d} (worst-case leakage);",
         "* half-selected row-0 cells of columns 1..3 store 1-d, d, 1-d. Phase 1 (0.1..1.2 ns): all word lines",
         "* high, bit lines forced to the background value; phase 2 (1.3..2.3 ns): row 0 only, forced to the row-0 data.",
         "* Trial k (variable period): precharge 1.5 ns, WL0+CS0 high, SAE rises d_k after WL (d_k from READ_D),",
         "* WL and SAE fall 0.8 ns after SAE rose. Measured: DOUT and the sense-bit-line differential at SAE,",
         "* cell state after the trial; max Q/QB bump and min half-select node over the run."]
    L += slice_netlist()
    # drivers: phase 1 data = others on all columns; phase 2 data = row-0 data
    L += [".model swinit sw(vt=0.5 vh=0.05 ron=20 roff=1e12)"]
    for c in range(COLS):
        L += [f"BDB{c} drvb{c} 0 V='(v(ph2)*{data[c]}+(1-v(ph2))*{others})*v(vdd)'",
              f"BDN{c} drvn{c} 0 V='(1-(v(ph2)*{data[c]}+(1-v(ph2))*{others}))*v(vdd)'",
              f"SB{c} bl{c} drvb{c} ctl{c} 0 swinit", f"SN{c} blb{c} drvn{c} ctl{c} 0 swinit",
              pwl(f"ctl{c}", ctl[c])]
    L.append(pwl("ph2", [(1.25, 2.4)]))
    wl0, cs, sae, pchb = [(0.1, 1.2), (1.3, 2.3)], {c: [] for c in range(COLS)}, [], [(2.4, 2.9)]
    wlo = [(0.1, 1.2)]
    meas, tb = [], T_START
    for k, dk in enumerate(READ_D):
        t_wl, t_sae = tb + 1.6, tb + 1.6 + dk
        t_off = t_sae + 0.8
        pchb.append((tb, tb + 1.5))
        wl0.append((t_wl, t_off))
        sae.append((t_sae, t_off))
        cs[0].append((tb, t_off + 0.6))
        meas += [meas_find(f"dout{k:02d}", "v(dout)", t_sae + 0.7),
                 meas_find(f"dv{k:02d}", "v(dvsa)", t_sae - 0.01),
                 meas_find(f"q{k:02d}", "v(xc0_0.q)", t_off + 0.5)]
        tb = t_off + 1.3
    tmax = tb
    L += ["BDVSA dvsa 0 V='v(sbl)-v(sblb)'"]
    L += common_sources(wl0, wlo, pchb, cs, sae, [], 0)
    t0, t1 = T_START, tmax
    bump = "q" if d == 0 else "qb"
    meas += [{"name": "bump", "spice": f".meas tran bump max v(xc0_0.{bump}) from={t0:g}n to={t1:g}n", "unit": "V"},
             {"name": "hs1", "spice": f".meas tran hs1 {'min' if d == 0 else 'max'} v(xc0_1.q) from={t0:g}n to={t1:g}n", "unit": "V"},
             {"name": "hs2", "spice": f".meas tran hs2 {'min' if d == 1 else 'max'} v(xc0_2.q) from={t0:g}n to={t1:g}n", "unit": "V"}]
    # hs1 stores 1-d: for d=0 it stores 1 (watch the minimum), for d=1 it stores 0 (watch the maximum); hs2 stores d.
    L.append("")
    return "\n".join(L), meas, tmax


# ------------------------------------------------------------------ write benches
def write_tb(bit, wen=True):
    """Cell (0,0) restored to 1-bit before each trial, then `bit` written through wdrv/colmux with a
    WL0 + WEN pulse of width w_k. Columns 1..3 row 0 (half selected) store 1-bit, bit, 1-bit."""
    restore = 1 - bit
    others = 1 - bit
    data1 = [restore, 1 - bit, bit, 1 - bit]    # row-0 data in cols 0..3 after initialisation
    L = [f"* WRITE{bit} completion bench{'' if wen else ' (NEGATIVE CONTROL: WEN never asserted)'}: write-pulse-width ladder on a",
         f"* 64-row x 4-column bit slice of {MACRO}. Initialisation as the read benches (all other cells store {others});",
         "* trial k (variable period): restore cell (0,0) to its old value with forced bit lines, precharge 1.0 ns, then WL0 and",
         f"* WEN high together for w_k (WRITE_W) ns with DIN={bit} through wdrv -> colmux (CS0); cell state sampled",
         "* 0.5 ns after the pulse. Half-select retention (min/max of the row-0 cells of columns 1..3) over the run."]
    L += slice_netlist()
    L += [".model swinit sw(vt=0.5 vh=0.05 ron=20 roff=1e12)"]
    # forcing windows: init phase 1/2 on all columns, then per-trial restore on column 0 only
    ctl = {c: [(0.1, 2.3)] for c in range(COLS)}
    wl0, wlo, pchb, cs, wenv = [(0.1, 1.2), (1.3, 2.3)], [(0.1, 1.2)], [(2.4, 2.9)], {c: [] for c in range(COLS)}, []
    meas = []
    rest_iv = []
    tb = T_START
    for k, w in enumerate(WRITE_W):
        ctl[0].append((tb + 0.1, tb + 1.5))
        rest_iv.append((tb + 0.1, tb + 1.5))
        wl0.append((tb + 0.2, tb + 1.2))
        pchb.append((tb + 1.6, tb + 2.6))
        cs[0].append((tb + 1.4, tb + 2.7 + w + 0.6))
        wl0.append((tb + 2.7, tb + 2.7 + w))
        if wen:
            wenv.append((tb + 2.7, tb + 2.7 + w))
        meas.append(meas_find(f"q{k:02d}", "v(xc0_0.q)", tb + 2.7 + w + 0.5))
        tb = tb + 2.7 + w + 0.9
    for c in range(COLS):
        # data forced while ctl{c} is high: init phases as read benches, per-trial restore (column 0) = restore value
        if c == 0:
            expr = f"(v(ph2)*{data1[0]}+(1-v(ph2))*{others})"
            expr = f"(v(rst)*{restore}+(1-v(rst))*{expr})"
        else:
            expr = f"(v(ph2)*{data1[c]}+(1-v(ph2))*{others})"
        L += [f"BDB{c} drvb{c} 0 V='{expr}*v(vdd)'", f"BDN{c} drvn{c} 0 V='(1-{expr})*v(vdd)'",
              f"SB{c} bl{c} drvb{c} ctl{c} 0 swinit", f"SN{c} blb{c} drvn{c} ctl{c} 0 swinit",
              pwl(f"ctl{c}", ctl[c])]
    L += [pwl("ph2", [(1.25, 2.4)]), pwl("rst", rest_iv)]
    L += common_sources(wl0, wlo, pchb, cs, [], wenv, bit)
    tmax = tb
    hs = lambda c, stored: ("min" if stored == 1 else "max")
    meas += [{"name": "hs1", "spice": f".meas tran hs1 {hs(1, data1[1])} v(xc0_1.q) from={T_START:g}n to={tmax:g}n", "unit": "V"},
             {"name": "hs2", "spice": f".meas tran hs2 {hs(2, data1[2])} v(xc0_2.q) from={T_START:g}n to={tmax:g}n", "unit": "V"}]
    L.append("")
    return "\n".join(L), meas, tmax


# ------------------------------------------------------------------ SNM benches
def snm_tb(mode, pair):
    dv = bitcell_devices()
    (pm, pw, pl), (nm, nw, nl), (am, aw, al) = dv["pu"], dv["pd"], dv["ax"]
    wl = "vdd" if mode == "read" else "0"
    L = [f"* In-situ {mode.upper()} SNM: decoupled half cell(s) {'(two independently mismatched)' if pair else ''}",
         "* whose bit line is the real column bl0 of the 64 x 4 bit slice: sram_precharge ON (PCHB = 0) and 63 further",
         "* bitcell_6t on the column (WL = 0, background data stored by .nodeset, Q = 0 = worst-case DC load on BL).",
         f"* Half-cell devices read from the macro's bitcell_6t (pu {pm} {pw}/{pl}, pd {nm} {nw}/{nl}, ax {am} {aw}/{al}).",
         f"* {'read: WL = VDD' if mode == 'read' else 'hold: WL = 0'}; sweep source is normalised and scaled by VDD."]
    L += [f".include '{INC}'", "VVDD vdd 0 dc 1.8", "VNRM nrm 0 dc 0", "BIN in 0 V='v(nrm)*v(vdd)'", "VPCHB pchb 0 dc 0"]
    for r in range(1, ROWS):
        L.append(f"XC{r}_0 bl0 blb0 0 vdd 0 bitcell_6t")
        L.append(f".nodeset v(xc{r}_0.q)=0 v(xc{r}_0.qb)=1.8")
    L += ["XPCH0 bl0 blb0 pchb vdd sram_precharge"]
    tags = ["a", "b"] if pair else [""]
    for t in tags:
        out = "out" + t
        L += [f"XMP{t} {out} in vdd vdd sky130_fd_pr__{pm} w={pw} l={pl}",
              f"XMN{t} {out} in 0 0 sky130_fd_pr__{nm} w={nw} l={nl}",
              f"XMA{t} bl0 {wl} {out} 0 sky130_fd_pr__{am} w={aw} l={al}"]
    return "\n".join(L) + "\n"


# ---------------------------------------------------------- opt-in extracted-DUT SNM (#210)
SNM_DUT_TOP = "sram_snm_halfcell_col64"
SNM_DUT_PINS = ["BL0", "BLB0", "IN", "OUT", "PCHB", "VDD", "VSS"] + [f"WL{r}" for r in range(ROWS)]
SNM_SWEEP = {"kind": "dc", "args": "VNRM 0 1 0.005"}
SNM_TIMEOUT_S = 300
SNM_TRIP = [{"name": "vtrip", "spice": ".meas dc vtrip when v(out)=0.9 fall=1", "unit": "V"}]
SNM_SAVE = {"save_vectors": ["v(in)", "v(out)"]}


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
            measurements += [
                {"name": f"{mode}_eye_snm", "value": None, "status": "error", "unit": "V", "message": msg},
                {"name": f"{mode}_pinned_snm", "value": None, "status": "error", "unit": "V", "message": msg},
                {"name": f"{mode}_vtrip", "value": None, "status": "error", "unit": "V", "message": msg},
            ]
            continue

        (out / f"{mode}.sim.stdout.json").write_text(proc.stdout)
        (out / f"{mode}.sim.stderr").write_text(proc.stderr)
        if proc.returncode != 0:
            msg = f"klt sim exited {proc.returncode}: {proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else 'no stderr'}"
            summary["modes"][mode] = {"status": "sim_error", "returncode": proc.returncode, "elapsed_s": elapsed, "message": msg}
            measurements += [
                {"name": f"{mode}_eye_snm", "value": None, "status": "error", "unit": "V", "message": msg},
                {"name": f"{mode}_pinned_snm", "value": None, "status": "error", "unit": "V", "message": msg},
                {"name": f"{mode}_vtrip", "value": None, "status": "error", "unit": "V", "message": msg},
            ]
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
            measurements += [
                {"name": f"{mode}_eye_snm", "value": None, "status": "error", "unit": "V", "message": msg},
                {"name": f"{mode}_pinned_snm", "value": None, "status": "error", "unit": "V", "message": msg},
                {"name": f"{mode}_vtrip", "value": vtrip, "status": "pass" if vtrip is not None else "error", "unit": "V"},
            ]
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
            measurements += [
                {"name": f"{mode}_eye_snm", "value": eye, "status": "pass", "unit": "V"},
                {"name": f"{mode}_pinned_snm", "value": pinned, "status": "pass", "unit": "V"},
                {"name": f"{mode}_vtrip", "value": vtrip, "status": "pass" if vtrip is not None else "error", "unit": "V"},
            ]
        except Exception as exc:
            msg = f"SNM extraction failed: {exc}"
            summary["modes"][mode] = {"status": "snm_error", "elapsed_s": elapsed, "message": msg}
            measurements += [
                {"name": f"{mode}_eye_snm", "value": None, "status": "error", "unit": "V", "message": msg},
                {"name": f"{mode}_pinned_snm", "value": None, "status": "error", "unit": "V", "message": msg},
                {"name": f"{mode}_vtrip", "value": vtrip, "status": "pass" if vtrip is not None else "error", "unit": "V"},
            ]

    (out / "snm_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return {"corners": [{"corner_id": corner_id, "measurements": measurements}]}


# ------------------------------------------------------------------ requests
base_req = functools.partial(tb_common.base_req, timeout_s=900)


def probe_of(req):
    """Single-corner (tt, 1.8 V, 25 C) local debug / cold-start probe of a corner request."""
    r = json.loads(json.dumps(req))
    r["corners"] = {"process": ["tt"], "supply_v": {"vvdd": [1.8]}, "temperature_c": [25]}
    r.pop("monte_carlo", None)
    r.pop("batch", None)
    r["backend"] = "local"
    return r


def build():
    benches = {}
    for d in (0, 1):
        body, meas, tmax = read_tb(d)
        benches[f"col_read{d}"] = (body, meas, tmax)
    for bit in (0, 1):
        benches[f"col_write{bit}"] = write_tb(bit)[0:3]
    benches["col_write0_nowen"] = write_tb(0, wen=False)[0:3]
    save = {"col_read0": ["v(wl0)", "v(sae)", "v(dout)", "v(sbl)", "v(sblb)", "v(xc0_0.q)", "v(xc0_0.qb)"]}
    save["col_read1"] = save["col_read0"]
    for name, (body, meas, tmax) in benches.items():
        files[f"tb/{name}.sp"] = body
        keep = {"save_vectors": save[name]} if name in save else {"waveforms": False, "keep_artifacts": False}
        files[f"requests/{name}.request.json"] = base_req(
            f"{name}.sp", {"kind": "tran", "args": f"{TRAN_STEP} {tmax:g}n"}, meas, keep)
        # ~2-7 min per transient unit; the cap is what the job ceiling allows at timeout_s 900
        files[f"requests/{name}.request.json"]["batch"] = batch_block(
            files[f"requests/{name}.request.json"], 14400)
        files[f"requests/{name}.probe.request.json"] = probe_of(files[f"requests/{name}.request.json"])
    # the negative control only needs the skew corners that bound write margin
    files["requests/col_write0_nowen.request.json"]["corners"] = {
        "process": ["tt", "fs", "sf"], "supply_v": {"vvdd": [1.62, 1.98]}, "temperature_c": [-40, 125]}
    files["requests/col_write0_nowen.probe.request.json"] = probe_of(files["requests/col_write0_nowen.request.json"])
    # SNM
    sweep = SNM_SWEEP
    keep = SNM_SAVE
    keep2 = {"save_vectors": ["v(in)", "v(outa)", "v(outb)"]}
    trip = SNM_TRIP
    for mode in ("read", "hold"):
        files[f"tb/col_{mode}_snm.sp"] = snm_tb(mode, False)
        files[f"tb/col_mc_{mode}_snm.sp"] = snm_tb(mode, True)
        files[f"tb/col_mc_{mode}_snm_neg.sp"] = with_params(snm_tb(mode, True), mm_scale_params(NEG_SCALE))
        r = base_req(f"col_{mode}_snm.sp", sweep, trip, keep)
        r["options"]["timeout_s"] = SNM_TIMEOUT_S
        r["batch"] = batch_block(r, 5400)
        files[f"requests/col_{mode}_snm.request.json"] = r
        files[f"requests/col_{mode}_snm.probe.request.json"] = probe_of(files[f"requests/col_{mode}_snm.request.json"])
        mcm = [{"name": "vtrip_a", "spice": ".meas dc vtrip_a when v(outa)=0.9 fall=1", "unit": "V"}]
        mc_axes = dict(process=["tt_mm", "sf_mm", "fs_mm"], vdds=[1.62, 1.98], temps=[125])
        mc = {"n": MC_N, "seed": MC_SEED, "vary": "mismatch", "k_sigma": 3}
        r = base_req(f"col_mc_{mode}_snm.sp", {"kind": "dc", "args": "VNRM 0 1 0.01"}, mcm, keep2, mc=mc, **mc_axes)
        r["options"]["timeout_s"] = SNM_TIMEOUT_S
        r["batch"] = batch_block(r, 5400)
        files[f"requests/col_mc_{mode}_snm.request.json"] = r
        neg = {"n": NEG_N, "seed": NEG_SEED, "vary": "mismatch", "k_sigma": 3}
        r = base_req(f"col_mc_{mode}_snm_neg.sp", {"kind": "dc", "args": "VNRM 0 1 0.01"}, mcm, keep2, mc=neg, **mc_axes)
        r["options"]["timeout_s"] = SNM_TIMEOUT_S
        r["batch"] = batch_block(r, 5400)
        files[f"requests/col_mc_{mode}_snm_neg.request.json"] = r


def _parse_opt(argv, flag):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 >= len(argv):
            sys.exit(f"make_column_tb: {flag} requires a value")
        val = argv[i + 1]
        del argv[i:i + 2]
        return val
    return None


def main():
    argv = list(sys.argv[1:])
    if "--measure-snm-dut" in argv or "--snm-dut" in argv:
        measure = "--measure-snm-dut" in argv
        argv = [a for a in argv if a not in ("--measure-snm-dut", "--snm-dut")]
        klt_cmd = _parse_opt(argv, "--klt")
        outdir = _parse_opt(argv, "--outdir") or os.environ.get("KLT_PEX_ARTIFACTS_DIR")
        top = _parse_opt(argv, "--top") or SNM_DUT_TOP
        pdk_root = _parse_opt(argv, "--pdk-root")
        if len(argv) != 1 or not outdir:
            sys.exit("usage: make_column_tb.py (--snm-dut|--measure-snm-dut) [--klt CMD] [--outdir DIR] [--top TOP] <dut.spice>")
        dut_path = argv[0]
        if measure:
            doc = measure_snm_dut(dut_path, outdir, klt_cmd=klt_cmd, top=top, pdk_root=pdk_root)
            print(json.dumps(doc))
        else:
            out = pathlib.Path(outdir).resolve()
            out.mkdir(parents=True, exist_ok=True)
            for mode in ("hold", "read"):
                tb_name = f"col_{mode}_snm.sp"
                (out / tb_name).write_text(snm_dut_tb(mode, dut_path, top))
                (out / f"col_{mode}_snm.probe.request.json").write_text(
                    json.dumps(snm_dut_probe_req(tb_name), indent=2) + "\n")
            print(f"make_column_tb: wrote 4 extracted-DUT SNM files under {out}")
        return

    build()
    base = root / "sim/column"
    bad = 0
    for rel, content in sorted(files.items()):
        text = content if isinstance(content, str) else json.dumps(content, indent=2) + "\n"
        p = base / rel
        if "--check" in argv:
            if not p.exists() or p.read_text() != text:
                print(f"make_column_tb: DRIFT {rel}")
                bad = 1
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
    if "--check" in argv:
        print("make_column_tb: " + ("drift detected" if bad else f"{len(files)} generated files current"))
        sys.exit(bad)
    print(f"make_column_tb: wrote {len(files)} files under sim/column/")


if __name__ == "__main__":
    main()
