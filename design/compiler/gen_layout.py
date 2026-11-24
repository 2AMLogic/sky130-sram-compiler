"""SRAM compiler layout generator: (words, bits, mux) -> macro GDS, LEF, socket descriptor.

Usage (needs klayout's python module; the repo does not pin the runner):
  uv run --no-project --with klayout python -I design/compiler/gen_layout.py WORDS BITS MUX \
      [-o OUT.gds] [--socket OUT.json] [--lef OUT.lef] [--report] [--check OUT.gds]
      [--check-socket OUT.json] [--check-lef OUT.lef]
  uv run --no-project --with klayout python -I design/compiler/gen_layout.py \
      --bench-slice OUT.gds | --check-bench-slice OUT.gds
  uv run --no-project --with klayout python -I design/compiler/gen_layout.py --snm-halfcell \
      [-o OUT.gds] [--check OUT.gds] [--report]
--snm-halfcell builds the dedicated test top for the DC SNM fixture instead of a macro: a 64-row
single column whose row 0 is the decoupled half-cell (free IN/OUT, own WL), rows 1..63 are bitcell_6t,
and the column carries one sram_precharge. It takes no WORDS BITS MUX and no --socket/--lef.
--check / --check-socket / --check-lef exit 3 when the committed file differs from a fresh build. --lef and
--check-lef run `klt lef-abstract` (needs klt and PDK_ROOT/PDK in the environment). --bench-slice emits the
column-bench slice top (see build_bench_slice); it takes no WORDS BITS MUX and no other output flag.

Every size goes through build(); there is no per-instance code. The geometry
(rows, cols, address split) comes from sram_compile.geometry(), the cell
connectivity from cells.CELLS and sizing.json, so layout and netlist cannot
drift apart silently. Output is deterministic (no timestamps, no host paths).

All shapes are drawn to the ordinary (logic) sky130 rules; the macro carries NO
areaid.ce (81/2) marker (see design/bitcell/README.md).
"""
import hashlib
import json
import pathlib
import sys
import tempfile

import klayout.db as db

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))  # design/: sky130_pdk
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I drops the script dir
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "bitcell"))  # gen_bitcell
import cells  # noqa: E402
import sram_compile as sc  # noqa: E402
from sky130_pdk import (DIFF_END, IMPL, LAYERS, LIC, NPC_ENC,  # noqa: E402
                        POLY_DIFF, POLY_END, VIA, write_gds)

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BITCELL_GDS = ROOT / "design/bitcell/bitcell_6t.gds"
BITCELL = "sky130_sram_bitcell_6t"

# ---- layers (GDS layer, datatype) ------------------------------------------------
# LAYERS is the shared table imported above; it stays a gen_layout attribute because
# gen_erc_spec.py and test_layout.py read it as gen_layout.LAYERS.
LBL = {"li": "li_lbl", "m1": "m1_lbl", "m2": "m2_lbl", "m3": "m3_lbl", "m4": "m4_lbl"}

# ---- drawing constants (um), all multiples of the 0.005 grid ----------------------
# LIC, VIA, DIFF_END, POLY_END, POLY_DIFF, IMPL and NPC_ENC are shared PDK
# rules, imported above from design/sky130_pdk.py; only compiler-local dimensions
# are defined here.
LI_W = 0.17          # li bar width
M1_W = 0.23          # m1 stub / pad width (mcon 0.17 + 0.03 enclosure each side)
M1_H = 0.37          # m1 pad height: 0.10 beyond the mcon (m1.5) and area >= 0.083
VIA2 = 0.20
PAD1 = 0.32          # m1 / m2 pad around via (0.085 enclosure)
PAD3 = 0.38          # m3 pad around via2 / via3 (0.09 enclosure)
POLY_PAD = 0.33      # poly contact pad
GATE_PITCH = 0.74    # gate-to-gate pitch of the periphery cells
RAIL = 0.29          # m1 supply rail width in the standard-height cells

# ---- array geometry ---------------------------------------------------------------
ROW_DY = 0.07        # extra vertical pitch: n-tap to next row's p diff needs 0.27 (difftap.3)
STRAP_H = 0.80       # p-substrate tap row inserted every STRAP_EVERY array rows
STRAP_EVERY = 16


def snap(v):
    """Round to the 0.005 um manufacturing grid."""
    return round(round(v / 0.005) * 0.005, 4)


class Pen:
    """A cell plus the helpers to draw shapes on it (um coordinates)."""

    default_labels = False      # cells are unlabelled inside the macro (see build()); tests switch it on

    def __init__(self, ly, name, labels=None):
        self.labels_on = Pen.default_labels if labels is None else labels
        self.ly = ly
        self.cell = ly.create_cell(name)
        self.name = name
        self.pins = {}      # name -> (layer, x, y)   m1/m2/m3 pad centres exported to the parent
        self.pin_rects = {}  # macro pins only: name -> (layer, x0, y0, x1, y1) of the pin metal

    def li(self, layer):
        return self.ly.layer(*LAYERS[layer])

    def rect(self, layer, x0, y0, x1, y1):
        self.cell.shapes(self.li(layer)).insert(
            db.DBox(snap(min(x0, x1)), snap(min(y0, y1)), snap(max(x0, x1)), snap(max(y0, y1))))

    def pad(self, layer, cx, cy, w, h=None):
        h = w if h is None else h
        self.rect(layer, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

    def cut(self, layer, cx, cy, size):
        self.pad(layer, cx, cy, size)

    def label(self, layer, text, x, y, drawing=False):
        """Text on the layer's label purpose; drawing=True repeats it on the drawing purpose
        (macro pins: `klt lef-abstract` resolves a pin's LEF layer from its declared GDS layer)."""
        if not self.labels_on:
            return
        self.cell.shapes(self.li(LBL[layer])).insert(db.DText(text, snap(x), snap(y)))
        if drawing:
            self.cell.shapes(self.li(layer)).insert(db.DText(text, snap(x), snap(y)))

    def pin(self, name, layer, x, y):
        self.pins[name] = (layer, snap(x), snap(y))
        self.label(layer, name, x, y)


# ---- contact stacks -----------------------------------------------------------------
def li_pad(p, cx, cy, h=0.33):
    p.pad("li", cx, cy, LI_W, h)


def sd_contact(p, cx, cy, to_m1=False):
    """licon on diff/tap with an li pad; optionally continue to an m1 pad."""
    p.cut("licon", cx, cy, LIC)
    li_pad(p, cx, cy)
    if to_m1:
        p.cut("mcon", cx, cy, LIC)
        p.pad("m1", cx, cy, M1_W, M1_H)


def poly_contact(p, cx, cy, to_m1=True):
    """licon on a poly pad (pad itself drawn by the caller) with npc and li pad."""
    p.cut("licon", cx, cy, LIC)
    p.pad("npc", cx, cy, LIC + 2 * NPC_ENC)
    li_pad(p, cx, cy)
    if to_m1:
        p.cut("mcon", cx, cy, LIC)
        p.pad("m1", cx, cy, M1_W, M1_H)


def via1(p, cx, cy):
    p.cut("via", cx, cy, VIA)
    p.pad("m1", cx, cy, PAD1)
    p.pad("m2", cx, cy, PAD1)


def via2(p, cx, cy):
    p.cut("via2", cx, cy, VIA2)
    p.pad("m2", cx, cy, 0.37)
    p.pad("m3", cx, cy, PAD3)


def via3(p, cx, cy):
    p.cut("via3", cx, cy, VIA2)
    p.pad("m3", cx, cy, PAD3)
    p.pad("m4", cx, cy, PAD3)


# ---- CMOS cells built from two diffusion strips ------------------------------------
X0 = 1.25            # first SD column of a cell (tap column sits left of it)
TAP_X = 0.40


def _tap(p, kind, cx, cy, rail_y):
    """Substrate/well tap 0.29 square with licon, li, mcon and an m1 stub to the rail."""
    p.pad("tap", cx, cy, 0.29)
    p.pad("psdm" if kind == "p" else "nsdm", cx, cy, 0.29 + 2 * IMPL)
    sd_contact(p, cx, cy, to_m1=True)
    p.rect("m1", cx - M1_W / 2, min(cy, rail_y), cx + M1_W / 2, max(cy, rail_y))


SUPPLY = ("VDD", "VSS")


def std_cell(ly, name, nseq, pseq, wn, wp, gap=0.90, ports=(), pitch=GATE_PITCH,
             join=(), m2_trunks=False, wn_cols=None, wp_cols=None, hc=None):
    """Two diffusion strips (N below, P above) with vertical poly gates.

    nseq/pseq alternate SD net, gate net, SD net ... (even index = SD column, odd =
    gate column); None = no diffusion/device there (a gate column with None breaks
    the strip). A gate with the same net in both strips is one poly line through
    the gap; a gate present in one strip only stops in the gap. Gates of nets in
    `join` are tied with a poly bar and one contact (inverter fingers); every other
    contact of a net is wired with li (same column, N above P) or a trunk in the
    gap: m1 (default) or, with m2_trunks, one m2 track per net so crossings are
    impossible. Returns the Pen with .pins and .size.
    """
    p = Pen(ly, name)
    n = len(nseq)
    assert n == len(pseq) and n % 2 == 1
    xs = [snap(X0 + i * pitch / 2) for i in range(n)]
    yn0 = 0.30
    wn_cols, wp_cols = wn_cols or {}, wp_cols or {}

    def runs(seq):
        out, i = [], 0
        while i < n:
            if seq[i] is None:
                i += 1
                continue
            j = i
            while j + 2 < n and seq[j + 1] is not None:
                j += 2
            out.append((i, j))
            i = j + 2
        return out

    def run_w(r, cols, dflt):
        ws = {cols.get(g, dflt) for g in range(r[0] + 1, r[1], 2)}
        assert len(ws) <= 1, (name, r, ws)
        return ws.pop() if ws else dflt

    wcol_n, wcol_p = {}, {}
    for r in runs(nseq):
        for c in range(r[0], r[1] + 1):
            wcol_n[c] = run_w(r, wn_cols, wn)
    for r in runs(pseq):
        for c in range(r[0], r[1] + 1):
            wcol_p[c] = run_w(r, wp_cols, wp)
    wn_max, wp_max = max(wcol_n.values()), max(wcol_p.values())
    yn1 = yn0 + wn_max
    # nets that need a trunk: more than one column
    cols_of = {}
    for strip, seq in (("n", nseq), ("p", pseq)):
        for i, net in enumerate(seq):
            if net and net not in SUPPLY:
                cols_of.setdefault(net, set()).add(i)
    trunk_nets = [k for k, v in cols_of.items() if len(v) > 1 and k not in join]
    trunk_nets += [k for k in join if k in cols_of and len(cols_of[k]) > 1
                   and len(cols_of[k] - {i for i in range(1, n, 2)}) > 0]
    trunk_nets = sorted(set(trunk_nets), key=lambda k: min(cols_of[k]))
    ntr = len(trunk_nets)
    if m2_trunks:
        gap = max(gap, 0.90 + 0.7 * max(ntr - 1, 0) + 0.50)
    min_gap = gap
    if hc is not None:                # force the cell height: all the slack goes into the gap
        gap = hc - 0.60 - wn_max - wp_max
        assert gap >= min_gap - 1e-9, (name, "hc too small", hc)
    yp0 = snap(yn1 + gap)
    yp1 = yp0 + wp_max
    hc = snap(yp1 + 0.30)
    w_cell = snap(xs[-1] + DIFF_END + LIC / 2 + 0.145)
    ync = {c: snap(yn0 + w / 2) for c, w in wcol_n.items()}
    ypc = {c: snap(yp0 + w / 2) for c, w in wcol_p.items()}
    for (y0, seq, wcol, kind) in ((yn0, nseq, wcol_n, "n"), (yp0, pseq, wcol_p, "p")):
        prev = None
        for (i, j) in runs(seq):
            y1 = y0 + wcol[i]
            dl, dr = xs[i] - LIC / 2 - DIFF_END - 0.02, xs[j] + LIC / 2 + DIFF_END + 0.02
            p.rect("diff", dl, y0, dr, y1)
            impl = "nsdm" if kind == "n" else "psdm"
            p.rect(impl, dl - IMPL, y0 - IMPL, dr + IMPL, y1 + IMPL)
            if prev:                  # implants closer than their 0.38 spacing are merged
                p.rect(impl, prev[0] + IMPL, y0 - IMPL, dl - IMPL, y0 + min(prev[1], wcol[i]) + IMPL)
            prev = (dr, wcol[i])
    p.rect("nwell", 0, yp0 - 0.20, w_cell, hc)
    p.rect("m1", 0, 0, w_cell, RAIL)
    p.rect("m1", 0, hc - RAIL, w_cell, hc)
    p.label("m1", "VSS", w_cell - 0.15, RAIL / 2)
    p.label("m1", "VDD", w_cell - 0.15, hc - RAIL / 2)
    _tap(p, "p", TAP_X, yn0 + 0.30, RAIL / 2)
    _tap(p, "n", TAP_X, yp0 + wp_max - 0.30, hc - RAIL / 2)
    track = {k: snap(yn1 + 0.90 + 0.7 * t) for t, k in enumerate(trunk_nets)}
    y_tr1 = snap(yp0 - 0.20)

    pts = {}                                    # net -> [(x, y, kind)] connection points
    # gates
    y_gp = snap(yn1 + POLY_DIFF + POLY_PAD / 2)
    gates = {}
    for i in range(1, n, 2):
        gn, gp = nseq[i], pseq[i]
        if gn is None and gp is None:
            continue
        assert gp is None or gn == gp, (name, i, gn, gp)
        assert gn is not None
        top = yp0 + wcol_p[i] + POLY_END if gp else y_gp + POLY_PAD / 2
        p.rect("poly", xs[i] - 0.075, yn0 - POLY_END, xs[i] + 0.075, top)
        p.pad("poly", xs[i], y_gp, POLY_PAD)
        gates.setdefault(gn, []).append(xs[i])
    for net, gx in gates.items():
        if net in join:
            p.rect("poly", gx[0] - POLY_PAD / 2, y_gp - POLY_PAD / 2, gx[-1] + POLY_PAD / 2, y_gp + POLY_PAD / 2)
            gx = gx[:1]
        for x in gx:
            poly_contact(p, x, y_gp)
            pts.setdefault(net, []).append((x, y_gp))
    # SD contacts
    colpts = {}
    for strip, seq, ycs in (("n", nseq, ync), ("p", pseq, ypc)):
        for i in range(0, n, 2):
            net = seq[i]
            if net is None:
                continue
            yc = ycs[i]
            sd_contact(p, xs[i], yc)
            if net == "VSS":
                p.cut("mcon", xs[i], yc, LIC)
                p.rect("m1", xs[i] - M1_W / 2, RAIL / 2, xs[i] + M1_W / 2, yc + M1_H / 2)
            elif net == "VDD":
                p.cut("mcon", xs[i], yc, LIC)
                p.rect("m1", xs[i] - M1_W / 2, yc - M1_H / 2, xs[i] + M1_W / 2, hc - RAIL / 2)
            else:
                colpts.setdefault((net, xs[i]), []).append((strip, yc))
    for (net, x), lst in colpts.items():
        if len(lst) == 2:
            p.rect("li", x - LI_W / 2, lst[0][1], x + LI_W / 2, lst[1][1])
        # the contact that carries the net's metal: the P one if the column has both
        # (keeps m1 off the VSS rail), else the only one
        pts.setdefault(net, []).append((x, lst[-1][1]))
    for net, plist in pts.items():
        multi = len({x for x, _ in plist}) > 1
        if not multi:
            if net in ports:
                x, yc = plist[0]
                if yc == y_gp:
                    pass
                else:
                    p.cut("mcon", x, yc, LIC)
                    p.pad("m1", x, yc, M1_W, M1_H)
                p.pin(net, "m1", x, yc)
            continue
        ytr = track[net] if m2_trunks else y_tr1
        for x, yc in plist:
            if yc != y_gp:
                p.cut("mcon", x, yc, LIC)
            p.rect("m1", x - M1_W / 2, min(yc, ytr) - M1_H / 2, x + M1_W / 2, max(yc, ytr) + M1_H / 2)
            if m2_trunks:
                via1(p, x, ytr)
        xa, xb = min(x for x, _ in plist), max(x for x, _ in plist)
        if m2_trunks:
            p.rect("m2", xa - PAD1 / 2, ytr - 0.115, xb + PAD1 / 2, ytr + 0.115)
        else:
            p.rect("m1", xa - M1_W / 2, ytr - M1_W / 2, xb + M1_W / 2, ytr + M1_W / 2)
        if net in ports:
            p.pin(net, "m2" if m2_trunks else "m1", xb, ytr)
    p.rect("bound", 0, 0, w_cell, hc)
    p.size = (w_cell, hc)
    return p


def cell_inv(ly, name, nf, wn_tot, wp_tot, hc=None, pitch=GATE_PITCH):
    ns = ["VSS" if j % 2 == 0 else "Y" for j in range(nf + 1)]
    seqn, seqp = [], []
    for j in range(nf + 1):
        seqn += [ns[j]] + (["A"] if j < nf else [])
        seqp += ["VDD" if ns[j] == "VSS" else "Y"] + (["A"] if j < nf else [])
    return std_cell(ly, name, seqn, seqp, wn_tot / nf, wp_tot / nf, ports=("A", "Y"), join=("A",), hc=hc, pitch=pitch)


def cell_nand(ly, name, k, wn, wp, hc=None, pitch=GATE_PITCH):
    seqn = ["Y"]
    for i in range(k):
        seqn += [f"A{i}", f"N{i + 1}" if i < k - 1 else "VSS"]
    seqp = ["VDD"]
    for i in range(k):
        seqp += [f"A{i}", "Y" if i % 2 == 0 else "VDD"]
    return std_cell(ly, name, seqn, seqp, wn, wp, ports=tuple(f"A{i}" for i in range(k)) + ("Y",), hc=hc, pitch=pitch)


def cell_senseamp(ly, name):
    S = cells.SIZING
    nseq = ["SBL", "SAEB", "SAN", "SANB", "TAIL", "SAN", "SANB", "SAEB", "SBLB", None,
            "TAIL", "SAE", "VSS", None, "DOUT", "SANB", "VSS"]
    pseq = [None, None, "SAN", "SANB", "VDD", "SAN", "SANB", None, None, None,
            None, None, None, None, "DOUT", "SANB", "VDD"]
    return std_cell(ly, name, nseq, pseq, S["sa_n"]["w"], S["sa_p"]["w"],
                    ports=("SBL", "SBLB", "SAE", "SAEB", "DOUT"), pitch=0.9, m2_trunks=True,
                    wn_cols={11: S["sa_tail"]["w"], 15: S["sa_out_n"]["w"]},
                    wp_cols={15: S["sa_out_p"]["w"]})


def cell_wdrv(ly, name):
    S = cells.SIZING
    nseq = ["SBL", "DINB", "X1", "WEN", "VSS", "WEN", "X2", "DIN", "SBLB", None,
            "DINB", "DIN", "VSS"]
    pseq = [None] * 10 + ["DINB", "DIN", "VDD"]
    return std_cell(ly, name, nseq, pseq, S["wd_n"]["w"], S["wd_inv_p"]["w"],
                    ports=("SBL", "SBLB", "DIN", "WEN"), pitch=0.9, m2_trunks=True,
                    wn_cols={11: S["wd_inv_n"]["w"]})


# ---- column-pitch cells (pitch-matched to the bitcell, drawn by hand) ----------------
BC_W, BC_H = 5.18, 1.665     # bitcell box (asserted against the committed GDS in build())
BL_X, BLB_X = 0.45, 4.73     # bit-line m1 centres inside a column
VSS_XS = (0.87, 4.31)        # vertical m1 VSS columns
VDD_XS = (1.81, 3.37)        # vertical m2 VDD columns (0.33 wide)
PITCH_Y = BC_H + ROW_DY
MP_X = ((0.27, 1.11), (4.07, 4.91))     # diff x extent of the two pass/precharge devices
STRIPE_X = (0.14, 5.04)                 # horizontal gate-poly stripe
ROW_OFF = 0.215                         # licon centre to gate centre


def _hdev(p, kind, x0, x1, yb):
    """Horizontal-poly device (W along x): diff + implant. Contact rows at yb and yb+2*ROW_OFF."""
    y0, y1 = yb - LIC / 2 - DIFF_END, yb + 2 * ROW_OFF + LIC / 2 + DIFF_END
    p.rect("diff", x0, y0, x1, y1)
    # implant runs to the cell edge so abutting column cells merge their implants (0.38 spacing)
    p.rect("psdm" if kind == "p" else "nsdm", 0 if x0 < 1 else x0 - IMPL, y0 - IMPL,
           BC_W if x1 > BC_W - 1 else x1 + IMPL, y1 + IMPL)


def cell_precharge(ly, name):
    """Per-column precharge: MP1/MP2 (BL/BLB to VDD) and the lateral equaliser MEQ,
    one PCHB gate stripe. The bit-line m1 lines enter from below and land on the top
    contact row; PCHB is an m3 bar through the cell (abutting cells merge it)."""
    p = Pen(ly, name)
    W = BC_W
    yb = 0.53
    yg, yt = snap(yb + ROW_OFF), snap(yb + 2 * ROW_OFF)
    ym = snap(yg + 0.42)
    hpc = 3.25
    p.rect("nwell", 0, 0.20, W, hpc)
    p.rect("nwell", 1.42, 0, 3.76, 0.30)          # joins the array nwell stripe
    for (x0, x1) in MP_X:
        _hdev(p, "p", x0, x1, yb)
    p.rect("poly", STRIPE_X[0], yg - 0.075, STRIPE_X[1], yg + 0.075)
    # MP1: BL (top row, x=BL_X) / VDD (bottom row); MP2 mirrored
    for xb, xv in ((BL_X, 0.80), (BLB_X, 4.38)):
        sd_contact(p, xb, yt, to_m1=True)
        sd_contact(p, xv, yb)
    p.rect("m1", BL_X - 0.07, 0, BL_X + 0.07, yt)
    p.rect("m1", BLB_X - 0.07, 0, BLB_X + 0.07, yt)
    p.pin("BL", "m1", BL_X, 0.1)
    p.pin("BLB", "m1", BLB_X, 0.1)
    # VDD: li bar on the bottom row, landed on both array VDD m2 columns
    p.rect("li", 0.80 - LI_W / 2, yb - LI_W / 2, 4.38 + LI_W / 2, yb + LI_W / 2)
    for x in VDD_XS:
        p.cut("mcon", x, yb, LIC)
        via1(p, x, yb)
        p.rect("m2", x - 0.165, 0, x + 0.165, 2.50)
    # n-tap on the first VDD column (nwell body tie)
    tcy = 1.80
    p.pad("tap", VDD_XS[0], tcy, 0.29)
    p.pad("nsdm", VDD_XS[0], tcy, 0.29 + 2 * IMPL)
    sd_contact(p, VDD_XS[0], tcy, to_m1=True)
    via1(p, VDD_XS[0], tcy)
    # equaliser: lateral PMOS, W along y, between the two devices
    xe1, xg, xe2 = 2.375, 2.59, 2.805
    p.rect("diff", xe1 - 0.145, ym - 0.21, xe2 + 0.145, ym + 0.21)
    p.rect("psdm", xe1 - 0.145 - IMPL, ym - 0.21 - IMPL, xe2 + 0.145 + IMPL, ym + 0.21 + IMPL)
    p.rect("poly", xg - 0.075, yg - 0.075, xg + 0.075, ym + 0.21 + POLY_END)
    sd_contact(p, xe1, ym)
    sd_contact(p, xe2, ym)
    p.rect("li", BL_X - LI_W / 2, yt - LI_W / 2, xe1 + LI_W / 2, yt + LI_W / 2)
    p.rect("li", xe1 - LI_W / 2, yt, xe1 + LI_W / 2, ym)
    p.rect("li", xe2 - LI_W / 2, yt - LI_W / 2, BLB_X + LI_W / 2, yt + LI_W / 2)
    p.rect("li", xe2 - LI_W / 2, yt, xe2 + LI_W / 2, ym)
    # PCHB: poly stub up to a contact pad, m1/m2 to the m3 bar
    xp, yp = 3.88, 1.45
    p.rect("poly", xp - 0.075, yg - 0.075, xp + 0.075, yp)
    p.pad("poly", xp, yp, POLY_PAD)
    poly_contact(p, xp, yp)
    via1(p, xp, yp)
    via2(p, xp, yp)
    p.rect("m3", 0, yp - 0.15, W, yp + 0.15)
    p.pin("PCHB", "m3", xp, yp)
    # supply buses on m3 at the top: VDD from the m2 columns, VSS from the m1 columns
    yv, ys = 2.30, 3.00
    p.rect("m3", 0, yv - 0.15, W, yv + 0.15)
    p.rect("m3", 0, ys - 0.15, W, ys + 0.15)
    for x in VDD_XS:
        via2(p, x, yv)
    for x in VSS_XS:
        p.rect("m1", x - 0.07, 0, x + 0.07, ys)
        via1(p, x, ys)
        via2(p, x, ys)
    p.pin("VDD", "m3", 0.5, yv)
    p.pin("VSS", "m3", 0.5, ys)
    p.rect("bound", 0, 0, W, hpc)
    p.size = (W, hpc)
    return p


def cell_colmux(ly, name, m, mux=1):
    """Per-column NMOS pass pair (BL->SBL, BLB->SBLB, gate SEL). The bit-line m1 lines
    enter from above; SBL/SBLB leave downward on m1. The SEL contact is an m3 pad at
    track m (the macro draws the CS<m> m3 line through it)."""
    p = Pen(ly, name)
    W = BC_W
    yb = 0.40
    yg, yt = snap(yb + ROW_OFF), snap(yb + 2 * ROW_OFF)
    ytap = 1.40
    ypad = snap(1.55 + 0.7 * m)
    hcm = snap(1.55 + 0.7 * (mux - 1) + 0.55)
    for (x0, x1) in MP_X:
        _hdev(p, "n", x0, x1, yb)
    p.rect("poly", STRIPE_X[0], yg - 0.075, STRIPE_X[1], yg + 0.075)
    for xb in (BL_X, BLB_X):
        for yc, up in ((yt, True), (yb, False)):    # tight rows: short li, m1 pad grows away from the other row
            p.cut("licon", xb, yc, LIC)
            # li encloses the licon by 0.08 on the sides and on the far end only
            p.rect("li", xb - 0.165, yc - LIC / 2 - (0 if up else 0.08), xb + 0.165, yc + LIC / 2 + (0.08 if up else 0))
            p.cut("mcon", xb, yc, LIC)
            if up:
                p.rect("m1", xb - M1_W / 2, yc - 0.145, xb + M1_W / 2, yc + 0.20)
            else:
                p.rect("m1", xb - M1_W / 2, yc - 0.20, xb + M1_W / 2, yc + 0.145)
        p.rect("m1", xb - 0.07, yt, xb + 0.07, hcm)
        p.rect("m1", xb - 0.07, 0, xb + 0.07, yb)
    p.pin("BL", "m1", BL_X, hcm - 0.1)
    p.pin("BLB", "m1", BLB_X, hcm - 0.1)
    p.pin("SBL", "m1", BL_X, 0.1)
    p.pin("SBLB", "m1", BLB_X, 0.1)
    # p-substrate tap on the VSS column (bulk tie)
    p.pad("tap", VSS_XS[0], ytap, 0.29)
    p.pad("psdm", VSS_XS[0], ytap, 0.29 + 2 * IMPL)
    sd_contact(p, VSS_XS[0], ytap, to_m1=True)
    p.rect("m1", VSS_XS[0] - 0.07, ytap, VSS_XS[0] + 0.07, hcm)
    p.pin("VSS", "m1", VSS_XS[0], hcm - 0.1)
    # SEL
    xp = 2.60
    p.rect("poly", xp - 0.075, yg - 0.075, xp + 0.075, ypad)
    p.pad("poly", xp, ypad, POLY_PAD)
    poly_contact(p, xp, ypad)
    via1(p, xp, ypad)
    via2(p, xp, ypad)
    p.rect("m3", 0, ypad - 0.15, W, ypad + 0.15)
    p.pin("SEL", "m3", xp, ypad)
    p.rect("bound", 0, 0, W, hcm)
    p.size = (W, hcm)
    return p


# ---- macro assembly -----------------------------------------------------------------
def u(v):
    return int(round(v * 1000))


def place(parent, child, x, y):
    parent.cell.insert(db.CellInstArray(child.cell.cell_index(), db.Trans(u(x), u(y))))


def place_array(parent, child, x, y, nx, ny, dx, dy):
    parent.cell.insert(db.CellInstArray(child.cell.cell_index(), db.Trans(u(x), u(y)),
                                        db.Vector(u(dx), 0), db.Vector(0, u(dy)), nx, ny))


def stack(p, x, y, lo, hi, ext=-1):
    """Via stack between metal layers lo..hi ('m1'..'m4') at (x, y). A stack that passes
    through m3 gets a 0.30 stub on the `ext` side so the lone m3 pad meets the 0.24 area rule."""
    order = ["m1", "m2", "m3", "m4"]
    fns = [via1, via2, via3]
    for i in range(order.index(lo), order.index(hi)):
        fns[i](p, x, y)
    if lo in ("m1", "m2") and hi == "m4":
        p.rect("m3", x - PAD3 / 2, y if ext > 0 else y - PAD3 / 2 - 0.30,
               x + PAD3 / 2, y + PAD3 / 2 + 0.30 if ext > 0 else y)


def hbar(p, layer, x0, x1, y, w):
    p.rect(layer, x0, y - w / 2, x1, y + w / 2)


def vbar(p, layer, x, y0, y1, w):
    p.rect(layer, x - w / 2, y0, x + w / 2, y1)


class ArrayGeom:
    def __init__(self, rows, cols):
        self.rows, self.cols = rows, cols
        self.B = sorted(set(range(0, rows, STRAP_EVERY)) | {rows})
        self.height = len(self.B) * STRAP_H + rows * PITCH_Y
        self.width = cols * BC_W

    def row_y(self, r):
        return sum(1 for b in self.B if b <= r) * STRAP_H + r * PITCH_Y

    def strap_y(self, i):
        return i * STRAP_H + self.B[i] * PITCH_Y


class BuildGeom:
    """build()'s geometry result: the two values callers read back.

    Attributes:
        ag:  the ArrayGeom (rows, cols, strap rows B, height/width in um).
        hcm: column-mux cell height (um), the periphery row below the array.
    """

    def __init__(self, ag, hcm):
        self.ag = ag
        self.hcm = hcm


def build_array(T, bc, ag, row0_cell=None):
    """Tile the committed bitcell (translation only, +ROW_DY vertical pitch), add the
    shapes the cell leaves to the array: implant/poly bridges, continuous well, bit-line,
    VSS and VDD columns, the p-substrate tap rows, and the wordline landing pads.
    row0_cell (SNM test top only, a one-column array): a cell of the bitcell footprint
    placed in row 0 in place of the bitcell."""
    rows, cols = ag.rows, ag.cols
    for i in range(len(ag.B) - 1):
        r0, r1 = ag.B[i], ag.B[i + 1]
        if row0_cell is not None and r0 == 0:
            place(T, row0_cell, 0, ag.row_y(0))
            place_array(T, bc, 0, ag.row_y(1), cols, r1 - 1, BC_W, PITCH_Y)
        else:
            place_array(T, bc, 0, ag.row_y(r0), cols, r1 - r0, BC_W, PITCH_Y)
        y0, y1 = ag.row_y(r0) + 0.075, ag.row_y(r1 - 1) + BC_H - 0.075
        for c in range(cols):
            x = c * BC_W
            T.rect("nsdm", x + 0.115, y0, x + 1.205, y1)
            T.rect("nsdm", x + 3.975, y0, x + 5.065, y1)
            if c < cols - 1:
                T.rect("nsdm", x + 5.065, y0, x + 5.295, y1)
        for r in range(r0, r1):
            for c in range(cols - 1):
                T.rect("poly", c * BC_W + 5.07, ag.row_y(r) + 1.03, c * BC_W + 5.29, ag.row_y(r) + 1.18)
    for c in range(cols):
        x = c * BC_W
        T.rect("nwell", x + 1.42, 0, x + 3.76, ag.height)
        for bx in (BL_X, BLB_X) + VSS_XS:
            vbar(T, "m1", x + bx, 0, ag.height, 0.14)
        for vx in VDD_XS:
            vbar(T, "m2", x + vx, 0, ag.height, 0.33)
    # p-substrate tap rows
    for i in range(len(ag.B)):
        ys = ag.strap_y(i) + STRAP_H / 2
        for c in range(cols):
            for vx in VSS_XS:
                x = c * BC_W + vx
                T.pad("tap", x, ys, 0.29)
                T.pad("psdm", x, ys, 0.29 + 2 * IMPL)
                sd_contact(T, x, ys, to_m1=True)
    # wordline landing pads (poly stub out of the first cell to a contact pad)
    for r in range(rows):
        y = ag.row_y(r) + 1.105
        T.rect("poly", -0.40, y - 0.075, 0.11, y + 0.075)
        T.pad("poly", -0.40, y, POLY_PAD)
        poly_contact(T, -0.40, y)
        stack(T, -0.40, y, "m1", "m3")


class GenError(ValueError):
    """The compiler accepts the size but this generator cannot place it."""


class _Ref:
    def __init__(self, cell):
        self.cell = cell


def _natural_hc(wn, wp):
    return snap(0.60 + wn + wp + 0.90)


def _circ(d, G):
    d = d % G
    return min(d, G - d)


def _choose_slots(G, w_sa, w_wd, sa_x, wd_x, pitch=0.7):
    """x (inside the bit group, periodic with G) of the four m4 verticals of a bit:
    SBL and SBLB sit on the sense-amp/write-driver pins (the two cells share their x);
    Q and D go to the free x closest to their pins, with an m3 jog at the pin's y.
    Every vertical of one net must keep `pitch` from the others, also across groups."""
    assert abs(sa_x["SBL"] - wd_x["SBL"]) < 1e-9 and abs(sa_x["SBLB"] - wd_x["SBLB"]) < 1e-9
    fixed = [sa_x["SBL"], sa_x["SBLB"]]
    if _circ(fixed[0] - fixed[1], G) < pitch:
        raise GenError(f"SBL/SBLB pins {pitch} um apart cannot be pitch-matched at G={G:.2f} um")
    slots = {}
    taken = list(fixed)
    for nm, target in (("Q", sa_x["Q"]), ("D", wd_x["D"])):
        best = None
        for k in range(0, int(round(G * 20))):
            for sgn in (1, -1):
                cand = round(target + sgn * k * 0.05, 3)
                if all(_circ(cand - t, G) >= pitch for t in taken):
                    best = cand
                    break
            if best is not None:
                break
        if best is None:
            raise GenError(f"no free m4 slot for {nm} in a {G:.2f} um bit group")
        slots[nm] = best
        taken.append(best)
    t_sa = max(1, -(-int(round(w_sa * 1000)) // int(round(G * 1000))))
    t_wd = max(1, -(-int(round(w_wd * 1000)) // int(round(G * 1000))))
    return t_sa, t_wd, slots


def _mk_logic_cell(ly, cname, nm, hc, pitch):
    """Build the standard-height logic cell for macro-netlist cell type `cname`."""
    S = cells.SIZING
    if cname == "sram_wldrv":
        return cell_inv(ly, nm, 4, S["wldrv_n"]["w"], S["wldrv_p"]["w"], hc=hc, pitch=pitch)
    if cname == "sram_inv":
        return cell_inv(ly, nm, 1, S["inv_n"]["w"], S["inv_p"]["w"], hc=hc, pitch=pitch)
    k = int(cname[-1])
    return cell_nand(ly, nm, k, S[f"nand{k}_n"]["w"], S[f"nand{k}_p"]["w"], hc=hc, pitch=pitch)


def _nat_hc(cname):
    """Natural (minimum) cell height of logic cell type `cname`."""
    S = cells.SIZING
    if cname == "sram_wldrv":
        return _natural_hc(S["wldrv_n"]["w"] / 4, S["wldrv_p"]["w"] / 4)
    if cname == "sram_inv":
        return _natural_hc(S["inv_n"]["w"], S["inv_p"]["w"])
    k = int(cname[-1])
    return _natural_hc(S[f"nand{k}_n"]["w"], S[f"nand{k}_p"]["w"])


class _BusRouter:
    """Vertical m4 buses to the left of the decoder lanes: net -> [x, ymin, ymax]."""

    def __init__(self, xr):
        self.xr = xr
        self.buses = {}

    def bus(self, nm):
        if nm not in self.buses:
            self.buses[nm] = [snap(self.xr - 0.9 * len(self.buses)), None, None]
        return self.buses[nm]

    def touch(self, nm, y):
        b = self.bus(nm)
        b[1] = y if b[1] is None else min(b[1], y)
        b[2] = y if b[2] is None else max(b[2], y)
        return b[0]


def _place_bit_slices(T, ag, hcm, G, mux, bits, pc, sa, wd):
    """Collectors, sense amps, write drivers and the Q/D m4 verticals.
    Returns (t_sa, t_wd, y_sa, y_wd, y_qd_top)."""
    yc1 = -hcm - 0.7
    yc2 = yc1 - 0.7
    sa_x = {"SBL": sa.pins["SBL"][1], "SBLB": sa.pins["SBLB"][1], "Q": sa.pins["DOUT"][1]}
    wd_x = {"SBL": wd.pins["SBL"][1], "SBLB": wd.pins["SBLB"][1], "D": wd.pins["DIN"][1]}
    t_sa, t_wd, slots = _choose_slots(G, sa.size[0], wd.size[0], sa_x, wd_x)
    y_sa0 = yc2 - 1.0 - sa.size[1]
    y_sa = [y_sa0 - t * (sa.size[1] + 0.8) for t in range(t_sa)]
    y_wd0 = y_sa[-1] - 1.0 - wd.size[1]
    y_wd = [y_wd0 - t * (wd.size[1] + 0.8) for t in range(t_wd)]
    y_qd_top = ag.height + pc.size[1] + 0.6
    for t in range(t_sa):
        place_array(T, sa, t * G, y_sa[t], len(range(t, bits, t_sa)), 1, t_sa * G, 0)
    for t in range(t_wd):
        place_array(T, wd, t * G, y_wd[t], len(range(t, bits, t_wd)), 1, t_wd * G, 0)
    col_spans = {}      # (net, y) -> [xmin, xmax] of m3 collector bars
    for k in range(bits):
        xs_sbl = [(k * mux + j) * BC_W + BL_X for j in range(mux)]
        xs_sblb = [(k * mux + j) * BC_W + BLB_X for j in range(mux)]
        for xs, yc, nm in ((xs_sbl, yc1, "SBL"), (xs_sblb, yc2, "SBLB")):
            for x in xs:
                vbar(T, "m1", x, yc, -hcm + 0.1, 0.14)
                stack(T, x, yc, "m1", "m3")
            col_spans.setdefault((nm, k), [yc, min(xs), max(xs)])
        tsa, twd = k % t_sa, k % t_wd
        xsa, xwd = k * G, k * G
        sa_pin = lambda n: (xsa + sa.pins[n][1], y_sa[tsa] + sa.pins[n][2], sa.pins[n][0])
        wd_pin = lambda n: (xwd + wd.pins[n][1], y_wd[twd] + wd.pins[n][2], wd.pins[n][0])
        for nm, yc in (("SBL", yc1), ("SBLB", yc2)):
            for (x, y, lay) in (sa_pin(nm), wd_pin(nm)):
                stack(T, x, y, lay, "m4")
                vbar(T, "m4", x, y, yc, 0.30)
                stack(T, x, yc, "m3", "m4")
                span = col_spans[(nm, k)]
                span[1], span[2] = min(span[1], x), max(span[2], x)
        for nm, (x, y, lay) in (("Q", sa_pin("DOUT")), ("D", wd_pin("DIN"))):
            xv = k * G + slots[nm]
            if abs(xv - x) < 1e-9:
                stack(T, x, y, lay, "m4", ext=1)
            else:                    # jog on m3 at the pin's y to the free vertical slot
                stack(T, x, y, lay, "m3")
                hbar(T, "m3", min(x, xv) - PAD3 / 2, max(x, xv) + PAD3 / 2, y, PAD3)   # as tall as the pads: no notches
                via3(T, xv, y)
            vbar(T, "m4", xv, y, y_qd_top, 0.30)
            T.label("m4", f"{nm}{k}", xv, y_qd_top - 0.2, drawing=True)
            T.pins[f"{nm}{k}"] = ("m4", xv, y_qd_top - 0.2)
            T.pin_rects[f"{nm}{k}"] = ("m4", xv - 0.15, y_qd_top - 0.8, xv + 0.15, y_qd_top)
    for (nm, k), (yc, x0, x1) in col_spans.items():
        pad_ = max(0.2, (0.9 - (x1 - x0)) / 2)          # m3 area rule: bar at least 0.9 long
        hbar(T, "m3", x0 - pad_, x1 + pad_, yc, 0.30)
        T.label("m3", f"{nm}{k}", x0, yc)
    return t_sa, t_wd, y_sa, y_wd, y_qd_top


def _partition_logic(words, bits, mux, rows):
    """Split the macro netlist's logic instances into row gates, row drivers and control logic.
    Returns (row_gate, row_drv, ctl, gname, nin)."""
    LOGIC = ("sram_inv", "sram_nand2", "sram_nand3", "sram_nand4", "sram_wldrv")
    row_gate, row_drv, ctl = {}, {}, []
    for ln in sc.macro_body(words, bits, mux):
        t = ln.split()
        if t[-1] not in LOGIC:
            continue
        cname, nets = t[-1], t[1:-1]
        ports = cells.CELLS[cname][0]
        out = nets[ports.index("Y")]
        if out.startswith("RWLB"):
            row_gate[int(out[4:])] = (cname, nets)
        elif out.startswith("WL"):
            row_drv[int(out[2:])] = (cname, nets)
        else:
            ctl.append((cname, nets))
    assert len(row_gate) == rows and len(row_drv) == rows
    gname = row_gate[0][0]
    nin = len(cells.CELLS[gname][0]) - 3
    if nin > 2:
        raise GenError(
            f"{words}x{bits} mux {mux}: {rows} rows need {nin} predecode lines per row, but the "
            f"decoder lanes route one m3 track per input per {PITCH_Y} um row pitch and three per "
            f"row do not fit the m3 pitch (generator limit: rows <= 64; see layout/README.md)")
    return row_gate, row_drv, ctl, gname, nin


def _place_row_decoders(T, ly, ag, rows, row_gate, gname, nin):
    """Row decoder lanes to the left of the array. Returns (lanes, router)."""
    hc_row = max(_nat_hc(gname), _nat_hc("sram_wldrv"))
    L = max(2, -(-int(round(hc_row * 1000)) // int(round(PITCH_Y * 1000))))
    gate_r = _mk_logic_cell(ly, gname, "row_" + gname, hc_row, 1.0)
    wl_r = _mk_logic_cell(ly, "sram_wldrv", "row_sram_wldrv", hc_row, 1.0)
    wg = gate_r.size[0]
    Wl = wg + wl_r.size[0]
    lanes, xr = [], -1.4
    for j in range(L):
        xl = xr - Wl
        lanes.append({"xl": xl, "xr": xr, "vss": xl - 1.0, "vdd": xl - 2.2})
        xr = lanes[-1]["vdd"] - 1.4
    router = _BusRouter(xr)
    for r in range(rows):
        j = r % L
        ln = lanes[j]
        y0 = ag.row_y(r)
        place(T, gate_r, ln["xl"], y0)
        place(T, wl_r, ln["xl"] + wg, y0)
        gcell, gnets = row_gate[r]
        gports = cells.CELLS[gcell][0]
        for i in range(nin):
            px, py = gate_r.pins[gports[i]][1:]
            ax, ay = ln["xl"] + px, y0 + py
            ystub = snap(y0 + 0.75 + 0.65 * i)
            via1(T, ax, ay)
            vbar(T, "m2", ax, min(ystub, ay) - 0.115, max(ystub, ay) + 0.115, 0.23)
            via2(T, ax, ystub)
            bx = router.touch(gnets[i], ystub)
            hbar(T, "m3", bx, ax, ystub, 0.30)
            via3(T, bx, ystub)
        yx, yy = ln["xl"] + gate_r.pins["Y"][1], y0 + gate_r.pins["Y"][2]
        ax2, ay2 = ln["xl"] + wg + wl_r.pins["A"][1], y0 + wl_r.pins["A"][2]
        via1(T, yx, yy)
        T.label("m2", f"RWLB{r}", yx, yy)
        hbar(T, "m2", yx, ax2, yy, 0.23)
        vbar(T, "m2", ax2, min(ay2, yy), max(ay2, yy), 0.23)
        via1(T, ax2, ay2)
        ox, oy = ln["xl"] + wg + wl_r.pins["Y"][1], y0 + wl_r.pins["Y"][2]
        ywl = y0 + 1.105
        stack(T, ox, oy, "m1", "m3")
        vbar(T, "m3", ox, min(oy, ywl) - 0.15, max(oy, ywl) + 0.15, 0.30)
        hbar(T, "m3", -0.40 - 0.15, ox + 0.15, ywl, 0.30)
        for net, yr in (("VSS", y0 + 0.145), ("VDD", y0 + hc_row - 0.145)):
            xsp = ln["vss"] if net == "VSS" else ln["vdd"]
            hbar(T, "m1", xsp - 0.16, ln["xl"] + 0.2, yr, RAIL)
            via1(T, xsp, yr)
    return lanes, router


def _place_control_row(T, ly, g, mux, bits, G, CW, sa, wd, y_wd, ctl, router):
    """Control logic row under the bit slices plus its left-edge channel router.
    Returns (x_end, x_rd_pre, y_cell0, hc_ctl, y_track)."""
    buses = router.buses
    for m in range(mux if mux > 1 else 0):
        router.bus(f"CS{m}")
    router.bus("SAE")
    router.bus("SAEB")
    cnames = sorted({c for c, _ in ctl})
    hc_ctl = max(_nat_hc(c) for c in cnames)
    cvar = {c: _mk_logic_cell(ly, c, "ctl_" + c, hc_ctl, 0.9) for c in cnames}
    xc, cinst = 0.0, []
    for (cname, nets) in ctl:
        cinst.append((cname, nets, xc))
        xc += cvar[cname].size[0]
    x_ctl_right = xc
    x_right = max(CW, (bits - 1) * G + sa.size[0], (bits - 1) * G + wd.size[0], x_ctl_right)
    x_end = snap(x_right + 1.0)
    x_rd_pre = snap(x_end + 3.6)
    pin_right = {f"A{i}" for i in range(g["na"])} | {"WLEN", "SAE"}
    nets_pins = {}                 # net -> [(x_pin, y_pin_rel, x_col_rel_slot, inst index, port)]
    maxpins = 0
    for ci, (cname, nets, cx) in enumerate(cinst):
        ports = cells.CELLS[cname][0]
        cv = cvar[cname]
        sig = sorted([(cv.pins[pn][1], pn, nets[ports.index(pn)]) for pn in ports
                      if pn not in ("VDD", "VSS")])
        maxpins = max(maxpins, len(sig))
        for k, (px, pn, net) in enumerate(sig):
            nets_pins.setdefault(net, []).append((cx + px, cv.pins[pn][2], cx + 0.45 + 0.9 * k, ci, k))
    spans = {}
    for net, lst in nets_pins.items():
        xs = [q[2] for q in lst]
        if net in buses:
            xs.append(buses[net][0])
        if net in pin_right:
            xs.append(x_end - 0.2)
        if len(xs) > 1:
            spans[net] = (min(xs), max(xs))
    tracks = []                    # last end per track
    track_of = {}
    for net, (a, b) in sorted(spans.items(), key=lambda kv: kv[1][0]):
        for ti, end in enumerate(tracks):
            if end + 0.8 < a:
                tracks[ti] = b
                track_of[net] = ti
                break
        else:
            tracks.append(b)
            track_of[net] = len(tracks) - 1
    jog_zone = 0.6 + 0.7 * maxpins + 0.4
    y_cell0 = snap(y_wd[-1] - 1.5 - (len(tracks) * 0.7 + 0.6) - jog_zone - hc_ctl)
    y_ctl_top = y_cell0 + hc_ctl
    y_track = {net: snap(y_ctl_top + jog_zone + 0.3 + 0.7 * ti) for net, ti in track_of.items()}
    for (cname, nets, cx) in cinst:
        place(T, cvar[cname], cx, y_cell0)
    for net, lst in nets_pins.items():
        yt = y_track.get(net)
        for (px, py, xcol, ci, k) in lst:
            ypin = y_cell0 + py
            yport = snap(y_ctl_top + 0.6 + 0.7 * k)
            via1(T, px, ypin)
            vbar(T, "m2", px, ypin - 0.115, yport + 0.115, 0.23)
            via2(T, px, yport)
            hbar(T, "m3", min(px, xcol) - 0.15, max(px, xcol) + 0.15, yport, 0.30)
            via3(T, xcol, yport)
            vbar(T, "m4", xcol, yport - 0.15, yt + 0.15 if yt else yport + 0.15, 0.30)
            if yt:
                via3(T, xcol, yt)
        if yt:
            a, b = spans[net]
            hbar(T, "m3", a - 0.15, b + 0.15, yt, 0.30)
            if net not in buses and net not in pin_right:
                T.label("m3", net, a, yt)
            if net in buses:
                bx = router.touch(net, yt)
                via3(T, bx, yt)
    return x_end, x_rd_pre, y_cell0, hc_ctl, y_track


def _route_globals(T, ag, hcm, mux, bits, G, CW, sa, wd, t_sa, t_wd, y_sa, y_wd, router,
                   x_end, x_rd_pre):
    """Global m3 lines through the bit slices and the vertical m4 buses. Returns (y_wen, y_pchb)."""
    for t in range(t_sa):
        ks = list(range(t, bits, t_sa))
        for pn, lay in (("SAE", "m1"), ("SAEB", "m2")):
            yl = y_sa[t] + sa.pins[pn][2]
            for k in ks:
                stack(T, k * G + sa.pins[pn][1], yl, lay, "m3")
            bx = router.touch(pn, yl)
            hbar(T, "m3", bx, x_end - 0.2, yl, 0.30)
            via3(T, bx, yl)
    y_wen = []
    for t in range(t_wd):
        ks = list(range(t, bits, t_wd))
        yl = y_wd[t] + wd.pins["WEN"][2]
        y_wen.append(yl)
        for k in ks:
            stack(T, k * G + wd.pins["WEN"][1], yl, "m2", "m3")
        hbar(T, "m3", ks[0] * G + wd.pins["WEN"][1] - 0.3, x_end - 0.2, yl, 0.30)
    if t_wd > 1:                                # tie the per-tier WEN lines at the right-hand end
        for yl in y_wen:
            via3(T, x_end - 0.2, yl)
        vbar(T, "m4", x_end - 0.2, min(y_wen) - 0.15, max(y_wen) + 0.15, 0.30)
    for m in range(mux):
        yl = -hcm + 1.55 + 0.7 * m
        if mux == 1:                            # no column select: the pass gates are tied to VDD
            hbar(T, "m3", 0, x_rd_pre, yl, 0.30)
            via3(T, x_rd_pre, yl)
            continue
        bx = router.touch(f"CS{m}", yl)
        hbar(T, "m3", bx, 0, yl, 0.30)
        via3(T, bx, yl)
    y_pchb = ag.height + 1.45
    hbar(T, "m3", CW, x_end - 0.2, y_pchb, 0.30)
    for nm, (bx, y0b, y1b) in router.buses.items():
        vbar(T, "m4", bx, y0b - 0.15, y1b + 0.15, 0.30)
        if nm != "SAE":                         # SAE is labelled once, at its macro pin
            T.label("m4", nm, bx, y0b + 0.5)
    return y_wen, y_pchb


def _route_supplies_and_pins(T, ag, g, CW, sa, wd, lanes, y_sa, y_wd, y_qd_top, y_cell0, hc_ctl,
                             x_end, y_track, y_wen, y_pchb):
    """Supply spines, right-hand VDD/VSS ring and macro pin export."""
    y_a = snap(y_qd_top + 1.2)
    y_b = snap(y_a + 0.8)
    x_rv, x_rd = snap(x_end + 2.0), snap(x_end + 3.6)
    for ln in lanes:
        for key, yb_ in (("vss", y_b), ("vdd", y_a)):
            vbar(T, "m2", ln[key], ag.row_y(0) - 0.3, yb_ + 0.4, 0.5)
            via2(T, ln[key], yb_)
    hbar(T, "m3", min(l["vdd"] for l in lanes) - 0.2, x_rd, y_a, 0.40)
    hbar(T, "m3", min(l["vss"] for l in lanes) - 0.2, x_rv, y_b, 0.40)
    hbar(T, "m3", CW, x_rd, ag.height + 2.30, 0.30)
    hbar(T, "m3", CW, x_rv, ag.height + 3.00, 0.30)
    for xr_, yr_ in ((x_rd, y_a), (x_rv, y_b), (x_rd, ag.height + 2.30), (x_rv, ag.height + 3.00)):
        via3(T, xr_, yr_)
    rows_y = ([(y, sa.size[1]) for y in y_sa] + [(y, wd.size[1]) for y in y_wd]
              + [(y_cell0, hc_ctl)])
    for y, h in rows_y:               # each cell row's rails run on to the right-hand ring
        for xring, yr in ((x_rv, y + 0.145), (x_rd, y + h - 0.145)):
            T.rect("m1", 0, yr - RAIL / 2, xring, yr + RAIL / 2)
            stack(T, xring, yr, "m1", "m4")
    y_bot = snap(y_cell0 - 1.0)
    y_top = snap(y_b + 0.8)
    for xr_ in (x_rv, x_rd):
        vbar(T, "m4", xr_, y_bot, y_top, 1.0)
    for nm, x in (("VSS", x_rv), ("VDD", x_rd)):
        T.label("m4", nm, x, (y_bot + y_top) / 2, drawing=True)
        T.pins[nm] = ("m4", x, (y_bot + y_top) / 2)
        T.pin_rects[nm] = ("m4", x - 0.5, y_bot, x + 0.5, y_top)
    for i in range(g["na"]):
        yt_ = y_track[f"A{i}"]
        T.label("m3", f"A{i}", x_end - 0.2, yt_, drawing=True)
        T.pins[f"A{i}"] = ("m3", x_end - 0.2, yt_)
        T.pin_rects[f"A{i}"] = ("m3", x_end - 1.0, yt_ - 0.15, x_end - 0.05, yt_ + 0.15)
    for nm, yv_ in (("WLEN", y_track["WLEN"]), ("SAE", y_sa[0] + sa.pins["SAE"][2]),
                    ("WEN", y_wen[0]), ("PCHB", y_pchb)):
        T.label("m3", nm, x_end - 0.2, yv_, drawing=True)
        T.pins[nm] = ("m3", x_end - 0.2, yv_)
        T.pin_rects[nm] = ("m3", x_end - 1.0, yv_ - 0.15, x_end - 0.2, yv_ + 0.15)


def build(words, bits, mux):
    """Place the macro layout for (words, bits, mux).

    Returns (ly, T, BuildGeom(ag=..., hcm=...)): the layout, its top-cell Pen,
    and the named geometry record — `ag`, the ArrayGeom (rows, cols, strap rows,
    height/width), and `hcm`, the column-mux cell height in um.
    """
    g = sc.geometry(words, bits, mux)
    rows, cols = g["rows"], g["cols"]
    name = sc.top_name(words, bits, mux)
    ly = db.Layout()
    ly.dbu = 0.001
    ly.read(str(BITCELL_GDS))
    bcc = ly.cell(BITCELL)
    bb = bcc.dbbox()
    assert abs(bb.width() - BC_W) < 1e-6 and abs(bb.height() - BC_H) < 1e-6, bb
    bc = _Ref(bcc)

    # ---- cells --------------------------------------------------------------------
    pc = cell_precharge(ly, "sram_precharge")
    cm = [cell_colmux(ly, f"sram_colmux_m{m}", m, mux) for m in range(mux)]
    sa = cell_senseamp(ly, "sram_senseamp")
    wd = cell_wdrv(ly, "sram_wdrv")
    T = Pen(ly, name, labels=True)
    ag = ArrayGeom(rows, cols)
    G = mux * BC_W

    # ---- array, precharge row (above), column-mux row (below) ----------------------
    build_array(T, bc, ag)
    place_array(T, pc, 0, ag.height, cols, 1, BC_W, 0)
    hcm = cm[0].size[1]
    for m in range(mux):
        place_array(T, cm[m], m * BC_W, -hcm, bits, 1, G, 0)
        y_cs = -hcm + 1.55 + 0.7 * m
        hbar(T, "m3", 0, ag.width, y_cs, 0.30)
    CW = ag.width

    for c in range(cols):                       # one label per net: anchors for LVS name hints
        T.label("m1", f"BL{c}", c * BC_W + BL_X, 0.1)
        T.label("m1", f"BLB{c}", c * BC_W + BLB_X, 0.1)
    for r in range(rows):
        T.label("m3", f"WL{r}", -0.40, ag.row_y(r) + 1.105)

    t_sa, t_wd, y_sa, y_wd, y_qd_top = _place_bit_slices(T, ag, hcm, G, mux, bits, pc, sa, wd)
    row_gate, _row_drv, ctl, gname, nin = _partition_logic(words, bits, mux, rows)
    lanes, router = _place_row_decoders(T, ly, ag, rows, row_gate, gname, nin)
    x_end, x_rd_pre, y_cell0, hc_ctl, y_track = _place_control_row(
        T, ly, g, mux, bits, G, CW, sa, wd, y_wd, ctl, router)
    y_wen, y_pchb = _route_globals(T, ag, hcm, mux, bits, G, CW, sa, wd, t_sa, t_wd, y_sa, y_wd,
                                   router, x_end, x_rd_pre)
    _route_supplies_and_pins(T, ag, g, CW, sa, wd, lanes, y_sa, y_wd, y_qd_top, y_cell0, hc_ctl,
                             x_end, y_track, y_wen, y_pchb)
    bb_all = T.cell.dbbox()
    T.rect("bound", bb_all.left, bb_all.bottom, bb_all.right, bb_all.top)
    T.size = (bb_all.width(), bb_all.height())
    return ly, T, BuildGeom(ag=ag, hcm=hcm)


# ---- bench slice (issue #209): the PEX top for the column transient benches ----------
SLICE_NAME = "sram_col_slice"
SLICE_ROWS, SLICE_COLS = 64, 4      # one bit slice of the 256 x 32 mux-4 reference


def build_bench_slice(rows=SLICE_ROWS, cols=SLICE_COLS):
    """Place the column-bench slice layout: the bit slice the transient benches measure.

    The same cells at the same pitches as bit 0 of sram_256x32_m4 (build()): a rows x cols
    bitcell array (cols = mux, one bit group), one precharge and one column-mux per column,
    one sense amplifier, one write driver, the SAEB inverter and the row-0 word-line driver,
    plus every row's word-line landing pads. Differences from the macro top, each of which
    the bench accounts for: rows 1.. are strapped into one WLO net (the benches drive them
    as one ideal line), the 124 absent columns' word-line gate load is NOT drawn (the bench
    adds XWLLOAD once, outside this top, on both klt pex legs) and there is no decoder or
    control logic beyond the row-0 driver and the SAEB inverter. Top-cell labels name every
    bench-visible pin and the four probed storage nodes (Q00/QB00/Q01/Q02), so a flat
    `klt pex --pins` extraction keeps each an addressable net with a clean name.
    """
    if cols != SLICE_COLS:
        raise GenError(f"bench slice: cols={cols}: the column benches measure one mux-4 bit group")
    mux = cols
    ly = db.Layout()
    ly.dbu = 0.001
    ly.read(str(BITCELL_GDS))
    bcc = ly.cell(BITCELL)
    bb = bcc.dbbox()
    assert abs(bb.width() - BC_W) < 1e-6 and abs(bb.height() - BC_H) < 1e-6, bb
    bc = _Ref(bcc)

    pc = cell_precharge(ly, "sram_precharge")
    cm = [cell_colmux(ly, f"sram_colmux_m{m}", m, mux) for m in range(mux)]
    sa = cell_senseamp(ly, "sram_senseamp")
    wd = cell_wdrv(ly, "sram_wdrv")
    inv = _mk_logic_cell(ly, "sram_inv", "slice_sram_inv", _nat_hc("sram_inv"), 0.9)
    T = Pen(ly, SLICE_NAME, labels=True)
    ag = ArrayGeom(rows, cols)
    G = mux * BC_W

    # ---- array, precharge row (above), column-mux row (below): as the macro ------------
    build_array(T, bc, ag)
    place_array(T, pc, 0, ag.height, cols, 1, BC_W, 0)
    hcm = cm[0].size[1]
    for m in range(mux):
        place(T, cm[m], m * BC_W, -hcm)          # bit-0 group: colmux variant m on column m
        hbar(T, "m3", 0, ag.width, -hcm + 1.55 + 0.7 * m, 0.30)
        T.label("m3", f"CS{m}", 0.5, -hcm + 1.55 + 0.7 * m)
    CW = ag.width
    for c in range(cols):                       # one label per net: anchors for LVS name hints
        T.label("m1", f"BL{c}", c * BC_W + BL_X, 0.1)
        T.label("m1", f"BLB{c}", c * BC_W + BLB_X, 0.1)

    # ---- bit-0 collectors, sense amp, write driver (one bit of _place_bit_slices) ------
    yc1, yc2 = -hcm - 0.7, -hcm - 1.4
    sa_x = {"SBL": sa.pins["SBL"][1], "SBLB": sa.pins["SBLB"][1], "Q": sa.pins["DOUT"][1]}
    wd_x = {"SBL": wd.pins["SBL"][1], "SBLB": wd.pins["SBLB"][1], "D": wd.pins["DIN"][1]}
    t_sa, t_wd, slots = _choose_slots(G, sa.size[0], wd.size[0], sa_x, wd_x)
    if t_sa != 1 or t_wd != 1:
        raise GenError(f"bench slice: a {sa.size[0]:.2f}/{wd.size[0]:.2f} um sense amp/write driver "
                       f"does not fit one {G:.2f} um bit group")
    y_sa = yc2 - 1.0 - sa.size[1]
    y_wd = y_sa - 1.0 - wd.size[1]
    y_qd_top = ag.height + pc.size[1] + 0.6
    place(T, sa, 0, y_sa)
    place(T, wd, 0, y_wd)
    sa_pin = lambda n: (sa.pins[n][1], y_sa + sa.pins[n][2], sa.pins[n][0])
    wd_pin = lambda n: (wd.pins[n][1], y_wd + wd.pins[n][2], wd.pins[n][0])
    col_spans = {}
    for xs, yc, nm in (([j * BC_W + BL_X for j in range(mux)], yc1, "SBL"),
                       ([j * BC_W + BLB_X for j in range(mux)], yc2, "SBLB")):
        for x in xs:
            vbar(T, "m1", x, yc, -hcm + 0.1, 0.14)
            stack(T, x, yc, "m1", "m3")
        col_spans[nm] = [yc, min(xs), max(xs)]
    for nm, yc in (("SBL", yc1), ("SBLB", yc2)):
        for (x, y, lay) in (sa_pin(nm), wd_pin(nm)):
            stack(T, x, y, lay, "m4")
            vbar(T, "m4", x, y, yc, 0.30)
            stack(T, x, yc, "m3", "m4")
            span = col_spans[nm]
            span[1], span[2] = min(span[1], x), max(span[2], x)
    for nm, pn in (("Q", "DOUT"), ("D", "DIN")):
        x, y, lay = sa_pin(pn) if nm == "Q" else wd_pin(pn)
        xv = slots[nm]
        if abs(xv - x) < 1e-9:
            stack(T, x, y, lay, "m4", ext=1)
        else:                    # jog on m3 at the pin's y to the free vertical slot
            stack(T, x, y, lay, "m3")
            hbar(T, "m3", min(x, xv) - PAD3 / 2, max(x, xv) + PAD3 / 2, y, PAD3)
            via3(T, xv, y)
        vbar(T, "m4", xv, y, y_qd_top, 0.30)
        T.label("m4", pn, xv, y_qd_top - 0.2)
    for nm, (yc, x0, x1) in col_spans.items():
        pad_ = max(0.2, (0.9 - (x1 - x0)) / 2)          # m3 area rule: bar at least 0.9 long
        hbar(T, "m3", x0 - pad_, x1 + pad_, yc, 0.30)
        T.label("m3", nm, x0, yc)

    # ---- SAEB inverter, right of both cells so its routes cross neither cell row -------
    hc_inv = inv.size[1]
    x_inv = snap(max(sa.size[0], wd.size[0]) + 2.0)
    y_inv = y_wd - 1.5 - hc_inv
    place(T, inv, x_inv, y_inv)
    x_end = snap(max(CW, x_inv + inv.size[0]) + 1.0)
    yl_sae = y_sa + sa.pins["SAE"][2]
    x, y, lay = sa_pin("SAE")
    stack(T, x, y, lay, "m3")
    hbar(T, "m3", sa.pins["SAE"][1] - 0.15, x_end - 0.2, yl_sae, 0.30)
    T.label("m3", "SAE", x_end - 0.5, yl_sae)
    ax, ay = x_inv + inv.pins["A"][1], y_inv + inv.pins["A"][2]
    stack(T, ax, ay, "m1", "m2")
    vbar(T, "m2", ax, ay - 0.115, yl_sae + 0.115, 0.23)
    via2(T, ax, yl_sae)                          # m2 riser lands on the SAE m3 bar
    yl_saeb = y_sa + sa.pins["SAEB"][2]
    x, y, lay = sa_pin("SAEB")
    stack(T, x, y, lay, "m3")
    # inv Y reaches the SA's SAEB pin through the left margin: a vertical between the cells
    # would cross the SAE and WEN m3 bars (same layer -> short), the left margin crosses nothing.
    yx, yy = x_inv + inv.pins["Y"][1], y_inv + inv.pins["Y"][2]
    stack(T, yx, yy, "m1", "m3")
    xL = -0.60
    hbar(T, "m3", xL - 0.15, yx + 0.15, yy, 0.30)
    vbar(T, "m3", xL, yy, yl_saeb, 0.30)
    hbar(T, "m3", xL - 0.15, sa.pins["SAEB"][1] + 0.15, yl_saeb, 0.30)
    yl_wen = y_wd + wd.pins["WEN"][2]
    x, y, lay = wd_pin("WEN")
    stack(T, x, y, lay, "m3")
    hbar(T, "m3", wd.pins["WEN"][1] - 0.3, x_end - 0.2, yl_wen, 0.30)
    T.label("m3", "WEN", x_end - 0.5, yl_wen)
    y_pchb = ag.height + 1.45
    hbar(T, "m3", CW, x_end - 0.2, y_pchb, 0.30)
    T.label("m3", "PCHB", x_end - 0.5, y_pchb)

    # ---- row-0 word-line driver (one decoder lane), WL0 route as the macro draws it ----
    hc_row = _nat_hc("sram_wldrv")
    wl_r = _mk_logic_cell(ly, "sram_wldrv", "slice_sram_wldrv", hc_row, 1.0)
    xl = snap(-(wl_r.size[0] + 1.4))
    y0 = ag.row_y(0)
    place(T, wl_r, xl, y0)
    ox, oy = xl + wl_r.pins["Y"][1], y0 + wl_r.pins["Y"][2]
    ywl = y0 + 1.105
    stack(T, ox, oy, "m1", "m3")
    vbar(T, "m3", ox, min(oy, ywl) - 0.15, max(oy, ywl) + 0.15, 0.30)
    hbar(T, "m3", -0.40 - 0.15, ox + 0.15, ywl, 0.30)
    axw, ayw = xl + wl_r.pins["A"][1], y0 + wl_r.pins["A"][2]
    via1(T, axw, ayw)
    ytop = snap(y0 + hc_row + 0.9)
    vbar(T, "m2", axw, ayw - 0.115, ytop + 0.115, 0.23)
    via2(T, axw, ytop)
    hbar(T, "m3", axw - 0.15, axw + 0.85, ytop, 0.30)
    T.label("m3", "WLIN0", axw + 0.45, ytop)
    T.label("m3", "WL0", -0.40, ywl)
    # rows 1.. strapped into the benches' one ideal word line
    vbar(T, "m3", -0.40, ag.row_y(1) + 1.105 - 0.15, ag.row_y(rows - 1) + 1.105 + 0.15, 0.30)
    T.label("m3", "WLO", -0.40, ag.row_y(rows // 2) + 1.105)
    # the four probed storage nodes, labelled where the bitcell's own li pin label sits
    for nm, c, qx in (("Q00", 0, 0.87), ("QB00", 0, 4.31), ("Q01", 1, 0.87), ("Q02", 2, 0.87)):
        T.label("li", nm, c * BC_W + qx, y0 + 0.775)

    # ---- supplies: lane spines, precharge-row buses out to a right-hand ring -----------
    y_a = snap(y_qd_top + 1.2)
    y_b = snap(y_a + 0.8)
    x_rv, x_rd = snap(x_end + 2.0), snap(x_end + 3.6)
    x_vss, x_vdd = snap(xl - 1.0), snap(xl - 2.2)
    for x, yb_ in ((x_vss, y_b), (x_vdd, y_a)):
        vbar(T, "m2", x, y0 - 0.3, yb_ + 0.4, 0.5)
        via2(T, x, yb_)
    hbar(T, "m3", x_vdd - 0.2, x_rd, y_a, 0.40)
    hbar(T, "m3", x_vss - 0.2, x_rv, y_b, 0.40)
    hbar(T, "m3", CW, x_rd, ag.height + 2.30, 0.30)
    hbar(T, "m3", CW, x_rv, ag.height + 3.00, 0.30)
    for xr_, yr_ in ((x_rd, y_a), (x_rv, y_b), (x_rd, ag.height + 2.30), (x_rv, ag.height + 3.00)):
        via3(T, xr_, yr_)
    for net, yr in (("VSS", y0 + 0.145), ("VDD", y0 + hc_row - 0.145)):
        xsp = x_vss if net == "VSS" else x_vdd
        hbar(T, "m1", xsp - 0.16, xl + 0.2, yr, RAIL)
        via1(T, xsp, yr)
    rows_y = [(y_sa, sa.size[1]), (y_wd, wd.size[1]), (y_inv, hc_inv)]
    for y, h in rows_y:               # each cell row's rails run on to the right-hand ring
        for xring, yr in ((x_rv, y + 0.145), (x_rd, y + h - 0.145)):
            T.rect("m1", 0, yr - RAIL / 2, xring, yr + RAIL / 2)
            stack(T, xring, yr, "m1", "m4")
    y_bot = snap(y_inv - 1.0)
    y_top = snap(y_b + 0.8)
    for xr_ in (x_rv, x_rd):
        vbar(T, "m4", xr_, y_bot, y_top, 1.0)
    for nm, x in (("VSS", x_rv), ("VDD", x_rd)):
        T.label("m4", nm, x, (y_bot + y_top) / 2, drawing=True)

    bb_all = T.cell.dbbox()
    T.rect("bound", bb_all.left, bb_all.bottom, bb_all.right, bb_all.top)
    T.size = (bb_all.width(), bb_all.height())
    return ly, T, BuildGeom(ag=ag, hcm=hcm)


# ---- outputs -------------------------------------------------------------------------
SNM_TOP = "sram_snm_halfcell_col64"
SNM_ROWS = 64


def build_snm_halfcell_column():
    """The DC SNM fixture's layout top: one column of SNM_ROWS rows, the decoupled half-cell in
    row 0, 63 bitcell_6t above it and one sram_precharge on top, all through build_array /
    cell_precharge exactly as the macro's columns. Ports (top-cell labels): BL0 BLB0 IN OUT
    WL0 (the half-cell's own word line) WL1..WL63 (the background rows') PCHB VDD VSS. Returns (ly, T, BuildGeom)."""
    import gen_bitcell as gb  # noqa: E402  (design/bitcell is put on sys.path below)
    ly = db.Layout()
    ly.dbu = 0.001
    ly.read(str(BITCELL_GDS))
    half_ly, half_info = gb.build(half=True)
    with tempfile.TemporaryDirectory() as tmp:
        hp = pathlib.Path(tmp) / "half.gds"
        write_gds(half_ly, hp)
        ly.read(str(hp))
    bcc, hcc = ly.cell(BITCELL), ly.cell(gb.HALF_CELL)
    for c in (bcc, hcc):
        bb = c.dbbox()
        assert abs(bb.width() - BC_W) < 1e-6 and abs(bb.height() - BC_H) < 1e-6, (c.name, bb)
    pc = cell_precharge(ly, "sram_precharge")
    T = Pen(ly, SNM_TOP, labels=True)
    ag = ArrayGeom(SNM_ROWS, 1)
    build_array(T, _Ref(bcc), ag, row0_cell=_Ref(hcc))
    place_array(T, pc, 0, ag.height, 1, 1, BC_W, 0)
    T.label("m1", "BL0", BL_X, 0.1)
    T.label("m1", "BLB0", BLB_X, 0.1)
    for r in range(SNM_ROWS):
        y = ag.row_y(r) + 1.105
        # the macro's row decoder gives each WL pad its m3 area; here the pad is the port, so give it
        # a 0.30 stub to the left (met3.area.1)
        T.rect("m3", -0.40 - PAD3 / 2 - 0.30, y - PAD3 / 2, -0.40 + PAD3 / 2, y + PAD3 / 2)
        T.label("m3", f"WL{r}", -0.40, y)
    y0 = ag.row_y(0)
    T.label("m1", "IN", half_info["in_xy"][0], y0 + half_info["in_xy"][1])
    T.label("li", "OUT", half_info["out_xy"][0], y0 + half_info["out_xy"][1])
    for name in ("PCHB", "VDD", "VSS"):          # BL/BLB are the bit-line labels above
        layer, x, y = pc.pins[name]
        T.pin(name, layer, x, ag.height + y)
    bb_all = T.cell.dbbox()
    T.rect("bound", bb_all.left, bb_all.bottom, bb_all.right, bb_all.top)
    T.size = (bb_all.width(), bb_all.height())
    return ly, T, BuildGeom(ag=ag, hcm=0.0)


def socket_descriptor(T, name):
    """klt socket descriptor for `klt lef-abstract`: outline plus every macro pin."""
    bb = T.cell.dbbox()
    pins = []
    for pn in sorted(T.pins, key=lambda n: (n.rstrip("0123456789"), int("".join(c for c in n if c.isdigit()) or 0))):
        lay, x, y = T.pins[pn]
        entry = {"name": pn, "layer": list(LAYERS[lay]), "x": round(x, 4), "y": round(y, 4),
                 "tolerance_um": 0.05, "metal_layer": list(LAYERS[lay])}
        if pn == "VDD":
            entry["use"] = "POWER"
        elif pn == "VSS":
            entry["use"] = "GROUND"
        else:
            entry["direction"] = "OUTPUT" if pn.startswith("Q") else "INPUT"
            entry["use"] = "SIGNAL"
        pins.append(entry)
    return {"schema": "klt.socket/1", "name": name,
            "outline": {"x0": round(bb.left, 4), "y0": round(bb.bottom, 4),
                        "x1": round(bb.right, 4), "y1": round(bb.top, 4)},
            "pins": pins}


def abstract_layout(T, name):
    """Blockage-style abstract of the macro for LEF generation: the pin metal as drawn, a
    corridor from each pin to the macro edge left free, every other m1..m4 area obstructed
    (a full per-shape OBS of the 8192-cell array would be ~19 MB of LEF)."""
    al = db.Layout()
    al.dbu = 0.001
    top = al.create_cell(name)
    bb = T.cell.dbbox()
    outline = db.Region(db.Box(u(bb.left), u(bb.bottom), u(bb.right), u(bb.top)))
    keep = {"m3": db.Region(), "m4": db.Region()}
    for pn, (lay, x0, y0, x1, y1) in sorted(T.pin_rects.items()):
        top.shapes(al.layer(*LAYERS[lay])).insert(db.Box(u(x0), u(y0), u(x1), u(y1)))
        _, x, y = T.pins[pn]
        top.shapes(al.layer(*LAYERS[lay])).insert(db.Text(pn, db.Trans(u(x), u(y))))
        if pn in ("VDD", "VSS"):
            k = db.Box(u(x0 - 0.3), u(bb.bottom), u(x1 + 0.3), u(bb.top))
        elif lay == "m3":
            k = db.Box(u(x0 - 0.3), u(y0 - 0.3), u(bb.right), u(y1 + 0.3))
        else:
            k = db.Box(u(x0 - 0.3), u(y0 - 0.3), u(x1 + 0.3), u(bb.top))
        keep[lay].insert(k)
    for lay in ("m1", "m2", "m3", "m4"):
        obs = outline - keep[lay] if lay in keep else outline
        for poly in obs.merged().each():            # rectangles, so no OBS bbox swallows a pin
            for piece in poly.decompose_trapezoids(db.Polygon.TD_simple):
                top.shapes(al.layer(*LAYERS[lay])).insert(piece)
    top.shapes(al.layer(*LAYERS["bound"])).insert(db.Box(u(bb.left), u(bb.bottom), u(bb.right), u(bb.top)))
    return al


def make_lef(T, name):
    """LEF text via `klt lef-abstract` on the abstract (needs klt, PDK_ROOT/PDK in the env)."""
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        abstract_layout(T, name).write(str(tmp / "abs.gds"))
        (tmp / "socket.json").write_text(json.dumps(socket_descriptor(T, name)))
        subprocess.run(["klt", "lef-abstract", str(tmp / "abs.gds"), "--socket", str(tmp / "socket.json"),
                        "--macro-name", name, "--cell-library", "sky130_fd_sc_hd", "--top", name,
                        "--require-power-pins", "-o", str(tmp / "out.lef")],
                       check=True, stdout=subprocess.DEVNULL)
        return (tmp / "out.lef").read_text()


def main(argv):
    args = argv[1:]
    snm = "--snm-halfcell" in args
    if snm:
        args.remove("--snm-halfcell")
    out = check = sock = lef = check_lef = check_sock = None
    bench_slice = check_bench_slice = None
    report = "--report" in args
    if report:
        args.remove("--report")
    for flag in ("-o", "--check", "--socket", "--lef", "--check-lef", "--check-socket",
                 "--bench-slice", "--check-bench-slice"):
        if flag in args:
            i = args.index(flag)
            val = args[i + 1]
            del args[i:i + 2]
            if flag == "-o":
                out = val
            elif flag == "--check":
                check = val
            elif flag == "--socket":
                sock = val
            elif flag == "--lef":
                lef = val
            elif flag == "--check-lef":
                check_lef = val
            elif flag == "--check-socket":
                check_sock = val
            elif flag == "--bench-slice":
                bench_slice = val
            else:
                check_bench_slice = val
    if bench_slice or check_bench_slice:
        if args or out or check or sock or lef or check_lef or check_sock:
            print(__doc__, file=sys.stderr)
            return 2
        try:
            ly, T, _geom = build_bench_slice()
        except (sc.RangeError, GenError, ValueError) as e:
            print(f"gen_layout: error: {e}", file=sys.stderr)
            return 1
        with tempfile.TemporaryDirectory() as tmp:
            fresh = pathlib.Path(tmp) / "fresh.gds"
            write_gds(ly, fresh)
            data = fresh.read_bytes()
        if bench_slice:
            pathlib.Path(bench_slice).write_bytes(data)
        if check_bench_slice:
            p = pathlib.Path(check_bench_slice)
            if not p.exists() or p.read_bytes() != data:
                print(f"gen_layout: {check_bench_slice} drifted from the generator", file=sys.stderr)
                return 3
        return 0
    if len(args) != (0 if snm else 3) or (snm and (sock or lef or check_lef or check_sock)):
        print(__doc__, file=sys.stderr)
        return 2
    try:
        if snm:
            top_name = SNM_TOP
            ly, T, geom = build_snm_halfcell_column()
        else:
            words, bits, mux = (int(a) for a in args)
            top_name = sc.top_name(words, bits, mux)
            ly, T, geom = build(words, bits, mux)
    except (sc.RangeError, GenError, ValueError) as e:
        print(f"gen_layout: error: {e}", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        fresh = pathlib.Path(tmp) / "fresh.gds"
        write_gds(ly, fresh)
        data = fresh.read_bytes()
    if out:
        pathlib.Path(out).write_bytes(data)
    if check:
        p = pathlib.Path(check)
        if not p.exists() or p.read_bytes() != data:
            print(f"gen_layout: {check} drifted from the generator", file=sys.stderr)
            return 3
    if sock or check_sock:
        text = json.dumps(socket_descriptor(T, top_name), indent=1) + "\n"
        if sock:
            pathlib.Path(sock).write_text(text)
        if check_sock:
            p = pathlib.Path(check_sock)
            if not p.exists() or p.read_text() != text:
                print(f"gen_layout: {check_sock} drifted from the generator", file=sys.stderr)
                return 3
    if lef or check_lef:
        text = make_lef(T, top_name)
        if lef:
            pathlib.Path(lef).write_text(text)
        if check_lef:
            p = pathlib.Path(check_lef)
            if not p.exists() or p.read_text() != text:
                print(f"gen_layout: {check_lef} drifted from the generator", file=sys.stderr)
                return 3
    if report:
        bb = T.cell.dbbox()
        print(json.dumps({"top": top_name, "sha256": hashlib.sha256(data).hexdigest(),
                          "width_um": round(bb.width(), 3), "height_um": round(bb.height(), 3),
                          "area_um2": round(bb.width() * bb.height(), 1),
                          "array_um": [round(geom.ag.width, 3), round(geom.ag.height, 3)],
                          "bitcell_pitch_um": [BC_W, PITCH_Y]}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
