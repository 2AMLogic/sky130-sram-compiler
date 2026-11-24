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
import pathlib
import re
import sys

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


# ------------------------------------------------------------- PEX slice DUT (#209)
SLICE_TOP = "sram_col_slice"
# The interface the LVS-matched layout top declares (design/compiler/gen_layout.py
# build_bench_slice), in the .SUBCKT header order the pinned klt 0.9.0 extraction writes
# for that layout (verified on the committed GDS; klt pex pin_order_mismatch fires if the
# generated header ever disagrees). Q00/QB00/Q01/Q02 export the probed storage nodes so
# the same measurement cards address them on the flat extracted leg and here.
SLICE_PINS = ("BL0 BL1 BL2 BL3 BLB0 BLB1 BLB2 BLB3 CS0 CS1 CS2 CS3 DIN DOUT PCHB "
              "Q00 Q01 Q02 QB00 SAE SBL SBLB VDD VSS WEN WL0 WLO WLIN0").split()
PDK_LEAVES = ("sky130_fd_pr__nfet_01v8", "sky130_fd_pr__pfet_01v8")
# bench-side spellings of the storage nodes the ladders probe (v(xc0_0.q) in the classic
# benches): the PEX benches measure the DUT pins instead of reaching into the hierarchy
QNODE_MAP = (("v(xc0_0.q)", "v(q00)"), ("v(xc0_0.qb)", "v(qb00)"),
             ("v(xc0_1.q)", "v(q01)"), ("v(xc0_2.q)", "v(q02)"))


def _subckt_def(name):
    """(ports, device lines) of one subckt of the macro netlist, verbatim."""
    body = macro_subckt(name).splitlines()
    ports = body[0].split()[2:]
    devs = [ln for ln in body[1:] if ln and not ln.startswith(("*", "."))]
    return ports, devs


def _emit_inst(cell, inst, portmap, renames, out):
    """Inline one instance of `cell` into `out`: its devices with port nets mapped through
    `portmap` and every internal net renamed `<inst>.<net>` (or through `renames`)."""
    ports, devs = _subckt_def(cell)
    if set(portmap) != set(ports):
        sys.exit(f"make_column_tb: {cell} port map {sorted(portmap)} != ports {sorted(ports)}")
    for dev in devs:
        toks = dev.split()
        mi = next((i for i, t in enumerate(toks[1:]) if t in PDK_LEAVES), None)
        if mi is None or mi != 4:            # every PDK leaf here is a 4-terminal d,g,s,b call
            sys.exit(f"make_column_tb: unexpected device line in {cell}: {dev}")
        nodes = [portmap.get(n, renames.get(f"{inst}.{n}", f"{inst}.{n}")) for n in toks[1:1 + mi]]
        out.append(f"X{inst}.{toks[0][1:]} " + " ".join(nodes) + " " + " ".join(toks[1 + mi:]))


def slice_dut():
    """The bench bit slice as ONE flat subckt: same cells, same nets as slice_netlist(),
    with every leaf subckt of the compiled macro inlined by the generator (nothing is
    hand-copied) so `klt pex` has a single `.include` to swap for the flat extraction."""
    L = [f"* {SLICE_TOP}: the column benches' bit slice (4 columns x {ROWS} cells, precharge,",
         "* colmux, sense amp, write driver, SAEB inverter, row-0 word-line driver) as one flat",
         f"* subckt, generated from {MACRO}: the macro's own leaf subckts are inlined here,",
         "* internal nets keep '<instance>.<net>' names, and the four probed storage nodes are",
         "* exported as pins so both klt pex legs measure the same nodes. The layout top that",
         "* matches this netlist by LVS is design/compiler/gen_layout.py::build_bench_slice."]
    L.append(".subckt " + SLICE_TOP + " " + " ".join(SLICE_PINS))
    p = {n: n.lower() for n in SLICE_PINS}       # pin -> body net (VSS is tied by the bench)
    for r in range(ROWS):
        for c in range(COLS):
            pm = {"BL": f"bl{c}", "BLB": f"blb{c}", "WL": "wl0" if r == 0 else "wlo",
                  "VDD": p["VDD"], "VSS": p["VSS"]}
            rn = {}
            if (r, c) == (0, 0):
                rn = {"xc0_0.Q": p["Q00"], "xc0_0.QB": p["QB00"]}
            elif (r, c) == (0, 1):
                rn = {"xc0_1.Q": p["Q01"]}
            elif (r, c) == (0, 2):
                rn = {"xc0_2.Q": p["Q02"]}
            _emit_inst("bitcell_6t", f"xc{r}_{c}", pm, rn, L)
    for c in range(COLS):
        _emit_inst("sram_precharge", f"xpch{c}",
                   {"BL": f"bl{c}", "BLB": f"blb{c}", "PCHB": p["PCHB"], "VDD": p["VDD"]}, {}, L)
        _emit_inst("sram_colmux", f"xcm{c}",
                   {"BL": f"bl{c}", "BLB": f"blb{c}", "SBL": p["SBL"], "SBLB": p["SBLB"],
                    "SEL": f"cs{c}", "VSS": p["VSS"]}, {}, L)
    _emit_inst("sram_senseamp", "xsa",
               {"SBL": p["SBL"], "SBLB": p["SBLB"], "SAE": p["SAE"], "SAEB": "saeb",
                "DOUT": p["DOUT"], "VDD": p["VDD"], "VSS": p["VSS"]}, {}, L)
    _emit_inst("sram_wdrv", "xwd",
               {"SBL": p["SBL"], "SBLB": p["SBLB"], "DIN": p["DIN"], "WEN": p["WEN"],
                "VDD": p["VDD"], "VSS": p["VSS"]}, {}, L)
    _emit_inst("sram_inv", "xsainv",
               {"A": p["SAE"], "Y": "saeb", "VDD": p["VDD"], "VSS": p["VSS"]}, {}, L)
    _emit_inst("sram_wldrv", "xwldrv",
               {"A": p["WLIN0"], "Y": "wl0", "VDD": p["VDD"], "VSS": p["VSS"]}, {}, L)
    L += [".ends", ""]
    return "\n".join(L)


def slice_instance():
    """The DUT one-liner the PEX benches carry in their own body: one include line (`klt pex`'s
    single swap point), the supply, the instantiation in SLICE_PINS order, and the 124 omitted
    columns' word-line gate load -- outside the extracted top, so it loads both legs alike."""
    nets = " ".join("0" if n == "VSS" else n.lower() for n in SLICE_PINS)
    return [f"* PEX bench: the matched DUT sits behind the single .include line klt pex swaps",
            f"* for the extracted netlist ({SLICE_TOP}.spice here, the layout extraction there).",
            f".include '{SLICE_TOP}.spice'",
            "VVDD vdd 0 dc 1.8",
            f"XSLICE {nets} {SLICE_TOP}",
            "* the 124 omitted columns' word-line gate load, outside the extracted top",
            f"XWLLOAD 0 wl0 0 0 sky130_fd_pr__nfet_01v8 L=0.15 W=0.42 m={2 * (128 - COLS)}"]


def pex_meas(meas):
    """Measurement cards with the storage-node probes pointed at the DUT pins."""
    out = []
    for m in meas:
        m2 = dict(m)
        for a, b in QNODE_MAP:
            m2["spice"] = m2["spice"].replace(a, b)
        out.append(m2)
    return out


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
def read_tb(d, dut=None, pex=False):
    """Accessed cell (row 0, col 0) stores d; all other slice cells store 1-d; col 1/2/3 row 0
    (half selected) store 1-d, d, 1-d. `dut` replaces the inline slice (the PEX benches pass
    the matched-DUT instantiation); `pex` points the storage-node probes at the DUT pins."""
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
    L += dut if dut is not None else slice_netlist()
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
    return "\n".join(L), pex_meas(meas) if pex else meas, tmax


# ------------------------------------------------------------------ write benches
def write_tb(bit, wen=True, dut=None, pex=False):
    """Cell (0,0) restored to 1-bit before each trial, then `bit` written through wdrv/colmux with a
    WL0 + WEN pulse of width w_k. Columns 1..3 row 0 (half selected) store 1-bit, bit, 1-bit.
    `dut`/`pex` as in read_tb()."""
    restore = 1 - bit
    others = 1 - bit
    data1 = [restore, 1 - bit, bit, 1 - bit]    # row-0 data in cols 0..3 after initialisation
    L = [f"* WRITE{bit} completion bench{'' if wen else ' (NEGATIVE CONTROL: WEN never asserted)'}: write-pulse-width ladder on a",
         f"* 64-row x 4-column bit slice of {MACRO}. Initialisation as the read benches (all other cells store {others});",
         "* trial k (variable period): restore cell (0,0) to its old value with forced bit lines, precharge 1.0 ns, then WL0 and",
         f"* WEN high together for w_k (WRITE_W) ns with DIN={bit} through wdrv -> colmux (CS0); cell state sampled",
         "* 0.5 ns after the pulse. Half-select retention (min/max of the row-0 cells of columns 1..3) over the run."]
    L += dut if dut is not None else slice_netlist()
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
    return "\n".join(L), pex_meas(meas) if pex else meas, tmax


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
    sweep = {"kind": "dc", "args": "VNRM 0 1 0.005"}
    keep = {"save_vectors": ["v(in)", "v(out)"]}
    keep2 = {"save_vectors": ["v(in)", "v(outa)", "v(outb)"]}
    trip = [{"name": "vtrip", "spice": ".meas dc vtrip when v(out)=0.9 fall=1", "unit": "V"}]
    for mode in ("read", "hold"):
        files[f"tb/col_{mode}_snm.sp"] = snm_tb(mode, False)
        files[f"tb/col_mc_{mode}_snm.sp"] = snm_tb(mode, True)
        files[f"tb/col_mc_{mode}_snm_neg.sp"] = with_params(snm_tb(mode, True), mm_scale_params(NEG_SCALE))
        r = base_req(f"col_{mode}_snm.sp", sweep, trip, keep)
        r["options"]["timeout_s"] = 300
        r["batch"] = batch_block(r, 5400)
        files[f"requests/col_{mode}_snm.request.json"] = r
        files[f"requests/col_{mode}_snm.probe.request.json"] = probe_of(files[f"requests/col_{mode}_snm.request.json"])
        mcm = [{"name": "vtrip_a", "spice": ".meas dc vtrip_a when v(outa)=0.9 fall=1", "unit": "V"}]
        mc_axes = dict(process=["tt_mm", "sf_mm", "fs_mm"], vdds=[1.62, 1.98], temps=[125])
        mc = {"n": MC_N, "seed": MC_SEED, "vary": "mismatch", "k_sigma": 3}
        r = base_req(f"col_mc_{mode}_snm.sp", {"kind": "dc", "args": "VNRM 0 1 0.01"}, mcm, keep2, mc=mc, **mc_axes)
        r["options"]["timeout_s"] = 300
        r["batch"] = batch_block(r, 5400)
        files[f"requests/col_mc_{mode}_snm.request.json"] = r
        neg = {"n": NEG_N, "seed": NEG_SEED, "vary": "mismatch", "k_sigma": 3}
        r = base_req(f"col_mc_{mode}_snm_neg.sp", {"kind": "dc", "args": "VNRM 0 1 0.01"}, mcm, keep2, mc=neg, **mc_axes)
        r["options"]["timeout_s"] = 300
        r["batch"] = batch_block(r, 5400)
        files[f"requests/col_mc_{mode}_snm_neg.request.json"] = r
    # PEX benches (#209): the same ladders, stimuli and controls, with the LVS-matched DUT
    # behind the one `.include` line `klt pex` swaps for the extracted netlist. Probe-only
    # (single corner, local): the post-layout corner grids are future work.
    files[f"tb/pex/{SLICE_TOP}.spice"] = slice_dut()
    mapq = lambda s: functools.reduce(lambda a, kv: a.replace(*kv), QNODE_MAP, s)
    for name in ("col_read0", "col_read1", "col_write0", "col_write1", "col_write0_nowen"):
        if name.startswith("col_read"):
            body, meas, tmax = read_tb(int(name[-1]), dut=slice_instance(), pex=True)
        elif name == "col_write0_nowen":
            body, meas, tmax = write_tb(0, wen=False, dut=slice_instance(), pex=True)
        else:
            body, meas, tmax = write_tb(int(name[-1]), dut=slice_instance(), pex=True)
        files[f"tb/pex/{name}.sp"] = body
        keep = ({"save_vectors": [mapq(s) for s in save[name]]} if name in save
                else {"waveforms": False, "keep_artifacts": False})
        r = probe_of(base_req(f"pex/{name}.sp", {"kind": "tran", "args": f"{TRAN_STEP} {tmax:g}n"},
                              meas, keep))
        r["netlist"] = f"../../tb/pex/{name}.sp"     # request sits one directory deeper
        files[f"requests/pex/{name}.probe.request.json"] = r


def main():
    build()
    base = root / "sim/column"
    bad = 0
    for rel, content in sorted(files.items()):
        text = content if isinstance(content, str) else json.dumps(content, indent=2) + "\n"
        p = base / rel
        if "--check" in sys.argv:
            if not p.exists() or p.read_text() != text:
                print(f"make_column_tb: DRIFT {rel}")
                bad = 1
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
    if "--check" in sys.argv:
        print("make_column_tb: " + ("drift detected" if bad else f"{len(files)} generated files current"))
        sys.exit(bad)
    print(f"make_column_tb: wrote {len(files)} files under sim/column/")


if __name__ == "__main__":
    main()
