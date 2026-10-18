"""Generate the logic-rule 6T bitcell layout (GDS) for sky130.

Usage:  uv run --no-project --with klayout python -I gen_bitcell.py <out.gds>
        (any python with klayout.db works; the repo does not pin the runner)

The cell is drawn to the ordinary (periphery) sky130 rules and carries NO
areaid.ce (81/2) marker, so every rule checked is the strict outside-marker one
(see verification/marker/records/2026-10-17-f22b400.md).

Topology: vertical diffusion strips, horizontal poly. Left to right:
  nL (PD_L wide part + AX_L narrow part) | pL (PU_L) | pR (PU_R) | nR
Left inverter gate = PD_L + PU_L on one poly row, ending in a poly contact head
in the centre gap; likewise the right inverter. Q (nL storage node, pL drain,
right-inverter gate head) is routed entirely on li1; QB (nR node, pR drain,
left-inverter gate head) is li1 locally and one met1 strap across the centre.
Bit lines and VSS are vertical met1, VDD vertical met2, WL is the poly row.

All coordinates are um; the sizing block below is the only design input.
"""
import json
import pathlib
import sys

import klayout.db as db

# ---- sizing (drawn W/L, um): read from sizing.json, the single source of truth ----
_SZ = json.loads((pathlib.Path(__file__).resolve().parent / "sizing.json").read_text())
PD_W, PD_L = _SZ["pd"]["w"], _SZ["pd"]["l"]     # pull-down  nfet_01v8
AX_W, AX_L = _SZ["ax"]["w"], _SZ["ax"]["l"]     # access     nfet_01v8
PU_W, PU_L = _SZ["pu"]["w"], _SZ["pu"]["l"]     # pull-up    pfet_01v8
# ----------------------------------------------------------------------------

CELL = "sky130_sram_bitcell_6t"
L = {
    "nwell": (64, 20), "diff": (65, 20), "tap": (65, 44), "poly": (66, 20),
    "licon": (66, 44), "li": (67, 20), "mcon": (67, 44), "m1": (68, 20),
    "via": (68, 44), "m2": (69, 20), "nsdm": (93, 44), "psdm": (94, 20),
    "npc": (95, 20), "bound": (235, 4), "via2": (69, 44), "m3": (70, 20),
    "poly_lbl": (66, 5), "li_lbl": (67, 5), "m1_lbl": (68, 5), "m2_lbl": (69, 5),
}

# rules used as drawing constants
LIC = 0.17           # licon / mcon edge
VIA = 0.15
LIC_GATE = 0.055     # licon to poly gate
DIFF_END = 0.06      # diff beyond licon (along strip)
POLY_END = 0.13      # poly beyond diff
POLY_DIFF = 0.075    # poly to unrelated diff
POLY_POLY = 0.21
LI_ENC = 0.08        # li around licon, all sides
M1_ENC = 0.06        # m1 around mcon
PAD = 0.33           # m1/m2 pad around via, and li/poly pad around a licon
NW_N = 0.34          # nwell to n diff
NW_P = 0.18          # nwell around p diff
IMPL = 0.125         # nsdm/psdm beyond diff/tap
NPC_ENC = 0.1

Y0 = 0.20            # diff bottom (cell-local); keeps heads/diff off the boundary
A = 0.24             # nL left edge


def r(x0, y0, x1, y1):
    return db.DBox(round(x0, 4), round(y0, 4), round(x1, 4), round(y1, 4))


def build():
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell(CELL)
    li_ = {k: ly.layer(*v) for k, v in L.items()}

    def put(layer, box):
        top.shapes(li_[layer]).insert(box)

    def mirror_x(x):
        return 2 * XC - x

    def both(layer, x0, y0, x1, y1):
        put(layer, r(x0, y0, x1, y1))
        put(layer, r(mirror_x(x1), y0, mirror_x(x0), y1))

    # ---- y levels (absolute) ------------------------------------------------
    gate_b = Y0 + 0.285
    pd_t, pu_t = gate_b + PD_L, gate_b + PU_L
    gate_t = max(pd_t, pu_t)
    q_b = gate_t + LIC_GATE + 0.0            # Q-row licon bottom
    q_t = q_b + LIC
    pdiff_t = q_t + DIFF_END
    ax_b = q_b + 0.34                        # AX gate bottom (WL row)
    ax_t = ax_b + AX_L
    bl_b = ax_t + LIC_GATE
    bl_t = bl_b + LIC
    ndiff_t = bl_t + DIFF_END
    vss_b = Y0 + 0.06
    vss_t = vss_b + LIC
    H = ndiff_t + Y0
    ystep = ax_b - 0.08                      # wide->narrow step of the n strip

    # ---- x levels -----------------------------------------------------------
    nl_l, nl_r = A, A + PD_W                 # wide part
    nl_nr = A + AX_W                         # narrow part right edge
    bl_cx = A + AX_W / 2
    vss_cx = nl_r - IMPL - LIC / 2           # inner contact column (VSS and Q)
    nw_l = nl_r + NW_N
    pl_l = nw_l + NW_P
    pl_r = pl_l + PU_W
    pl_cx = (pl_l + pl_r) / 2
    head_w = PAD
    lh_l = pl_r + 0.135                      # left-inverter head (QB gate contact)
    lh_r = lh_l + head_w
    rh_l = lh_r + POLY_POLY
    rh_r = rh_l + head_w
    pr_l = rh_r + 0.135
    XC = (pl_r + pr_l) / 2                   # mirror axis
    W = mirror_x(0.0)

    # ---- diffusion ----------------------------------------------------------
    both("diff", nl_l, Y0, nl_r, ystep)              # PD wide part (to the step)
    both("diff", nl_l, Y0, nl_nr, ndiff_t)           # AX narrow part (full height)
    both("diff", pl_l, Y0, pl_r, pdiff_t)            # PU
    # n-tap in the nwell, above the WL row, under the VDD_L column
    tap_b = ax_t + 0.10
    tap_w = 0.29
    tap_l, tap_r = pl_cx - tap_w / 2, pl_cx + tap_w / 2
    put("tap", r(tap_l, tap_b, tap_r, H))
    tap_lic_b = tap_b + 0.075
    # ---- poly ---------------------------------------------------------------
    # left inverter row: from left of nL through pL to the head
    put("poly", r(nl_l - POLY_END, gate_b, lh_r, gate_b + PD_L))
    put("poly", r(pl_l - POLY_END, gate_b, pl_r + POLY_END, gate_b + PU_L))
    lh_b = Y0 - 0.09                                 # head bottom
    put("poly", r(lh_l, lh_b, lh_r, gate_b + PD_L))
    # right inverter row (mirror of nR/pR, head pad up)
    put("poly", r(rh_l, gate_b, mirror_x(nl_l - POLY_END), gate_b + PD_L))
    put("poly", r(mirror_x(pl_r + POLY_END), gate_b, mirror_x(pl_l - POLY_END), gate_b + PU_L))
    rh_t = gate_b + PAD
    put("poly", r(rh_l, gate_b, rh_r, rh_t))
    # wordline row
    put("poly", r(nl_l - POLY_END, ax_b, mirror_x(nl_l - POLY_END), ax_t))

    # ---- licon --------------------------------------------------------------
    def lic(cx, cy):
        put("licon", r(cx - LIC / 2, cy - LIC / 2, cx + LIC / 2, cy + LIC / 2))

    def lic_pair(cx, cy):
        lic(cx, cy)
        lic(mirror_x(cx), cy)

    cy_vss, cy_q, cy_bl = (vss_b + vss_t) / 2, (q_b + q_t) / 2, (bl_b + bl_t) / 2
    lic_pair(bl_cx, cy_bl)
    lic_pair(vss_cx, cy_vss)
    lic_pair(vss_cx, cy_q)               # Q / QB node on the n strip
    lic_pair(pl_cx, cy_vss)              # VDD
    lic_pair(pl_cx, cy_q)                # Q / QB node on the p strip
    lic(pl_cx, (tap_lic_b + tap_lic_b + LIC) / 2)  # n-tap
    lh_cx, lh_cy = (lh_l + lh_r) / 2, lh_b + 0.08 + LIC / 2
    rh_cx, rh_cy = (rh_l + rh_r) / 2, gate_b + 0.08 + LIC / 2
    lic(lh_cx, lh_cy)
    lic(rh_cx, rh_cy)

    # ---- li1 ----------------------------------------------------------------
    def li_pad(cx, cy, below=LI_ENC, above=LI_ENC):
        """li pad around the licon at (cx, cy): LI_ENC at the sides, `below`/`above` vertically."""
        put("li", r(cx - LIC / 2 - LI_ENC, cy - LIC / 2 - below,
                    cx + LIC / 2 + LI_ENC, cy + LIC / 2 + above))

    # pads on every contact; the contacts either side of the gate row keep their
    # vertical enclosure on the far side only, so li stays 0.17 apart across it
    for cx, cy, below, above in [(bl_cx, cy_bl, LI_ENC, LI_ENC),
                                 (vss_cx, cy_vss, LI_ENC, 0.0), (pl_cx, cy_vss, LI_ENC, 0.0),
                                 (vss_cx, cy_q, 0.0, LI_ENC), (pl_cx, cy_q, 0.0, LI_ENC)]:
        li_pad(cx, cy, below, above)
        li_pad(mirror_x(cx), cy, below, above)
    li_pad(pl_cx, tap_lic_b + LIC / 2)
    li_pad(lh_cx, lh_cy)
    li_pad(rh_cx, rh_cy)
    # Q net (left): nL node -> pL drain -> right-inverter head
    bar_h = LIC
    put("li", r(vss_cx, cy_q - bar_h / 2, rh_cx, cy_q + bar_h / 2))
    # QB net (right): mirror link nR node <- pR drain
    put("li", r(mirror_x(vss_cx), cy_q - bar_h / 2, mirror_x(pl_cx), cy_q + bar_h / 2))
    # mcon landing for the QB strap, on the right QB bar
    sx = mirror_x(pl_cx) + 0.30
    put("li", r(sx - LIC / 2, cy_q - bar_h / 2, sx + LIC / 2, cy_q + bar_h / 2))

    # ---- mcon / met1 --------------------------------------------------------
    def mcon(cx, cy):
        put("mcon", r(cx - LIC / 2, cy - LIC / 2, cx + LIC / 2, cy + LIC / 2))

    def m1_pad(cx, cy, s=LIC + 2 * M1_ENC):
        put("m1", r(cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2))

    # bit lines (vertical met1, full height) and VSS (vertical met1)
    for cx, cy, name in [(bl_cx, cy_bl, "BL"), (mirror_x(bl_cx), cy_bl, "BLB")]:
        mcon(cx, cy)
        m1_pad(cx, cy)
        put("m1", r(cx - 0.07, 0, cx + 0.07, H))
    for cx in (vss_cx, mirror_x(vss_cx)):
        mcon(cx, cy_vss)
        m1_pad(cx, cy_vss, PAD)
        put("m1", r(cx - 0.07, 0, cx + 0.07, H))
        # VSS up to a horizontal met3 rail that ties the two VSS columns together
        put("via", r(cx - VIA / 2, cy_vss - VIA / 2, cx + VIA / 2, cy_vss + VIA / 2))
        put("m2", r(cx - 0.185, cy_vss - 0.185, cx + 0.185, cy_vss + 0.185))
        put("via2", r(cx - 0.1, cy_vss - 0.1, cx + 0.1, cy_vss + 0.1))
    m3_h = 0.40
    put("m3", r(vss_cx - 0.1 - 0.085, cy_vss - m3_h / 2, mirror_x(vss_cx) + 0.1 + 0.085, cy_vss + m3_h / 2))
    # VDD: m1 pad + via + vertical m2
    for cx in (pl_cx, mirror_x(pl_cx)):
        mcon(cx, cy_vss)
        put("m1", r(cx - PAD / 2, cy_vss - VIA / 2 - 0.09, cx + PAD / 2, cy_vss + VIA / 2 + 0.055))
        put("via", r(cx - VIA / 2, cy_vss - VIA / 2, cx + VIA / 2, cy_vss + VIA / 2))
        put("m2", r(cx - PAD / 2, 0, cx + PAD / 2, H))
    # the two VDD columns are joined by a short met2 strap
    put("m2", r(pl_cx, cy_q - PAD / 2, mirror_x(pl_cx), cy_q + PAD / 2))
    # n-tap -> VDD_L
    tcy = tap_lic_b + LIC / 2
    mcon(pl_cx, tcy)
    m1_pad(pl_cx, tcy, PAD)
    put("via", r(pl_cx - VIA / 2, tcy - VIA / 2, pl_cx + VIA / 2, tcy + VIA / 2))
    # QB strap (met1): left-inverter head -> up over the Q row -> across -> down to QB bar
    mcon(lh_cx, lh_cy)
    m1_pad(lh_cx, lh_cy)
    mcon(sx, cy_q)
    m1_pad(sx, cy_q)
    sy = ax_t + 0.10 + 0.07
    put("m1", r(lh_cx - 0.07, lh_cy, lh_cx + 0.07, sy + 0.07))
    put("m1", r(lh_cx - 0.07, sy - 0.07, sx + 0.07, sy + 0.07))
    put("m1", r(sx - 0.07, cy_q, sx + 0.07, sy + 0.07))

    # ---- implants / well / npc ---------------------------------------------
    nwr = mirror_x(nw_l)
    put("nwell", r(nw_l, 0, nwr, H))
    for xl, xr in [(nl_l, nl_r)]:
        both("nsdm", xl - IMPL, Y0 - IMPL, xr + IMPL, ndiff_t + IMPL)
    both("psdm", pl_l - IMPL, Y0 - IMPL, pl_r + IMPL, pdiff_t + IMPL)
    put("nsdm", r(nl_r + IMPL, tap_b - IMPL, tap_r + IMPL, H))   # merged with nL implant
    put("npc", r(lh_cx - LIC / 2 - NPC_ENC, lh_cy - LIC / 2 - NPC_ENC,
                 rh_cx + LIC / 2 + NPC_ENC, rh_cy + LIC / 2 + NPC_ENC))

    # ---- labels / boundary ---------------------------------------------------
    def lbl(layer, text, cx, cy):
        top.shapes(li_[layer]).insert(db.DText(text, cx, cy))

    lbl("m1_lbl", "BL", bl_cx, cy_bl)
    lbl("m1_lbl", "BLB", mirror_x(bl_cx), cy_bl)
    lbl("m1_lbl", "VSS", vss_cx, cy_vss + 0.4)
    lbl("m1_lbl", "VSS", mirror_x(vss_cx), cy_vss + 0.4)
    lbl("m2_lbl", "VDD", pl_cx, H - 0.1)
    lbl("m2_lbl", "VDD", mirror_x(pl_cx), H - 0.1)
    lbl("poly_lbl", "WL", nl_l, (ax_b + ax_t) / 2)
    lbl("li_lbl", "Q", vss_cx, cy_q)
    lbl("li_lbl", "QB", mirror_x(vss_cx), cy_q)
    put("bound", r(0, 0, W, H))

    info = {"width_um": round(W, 4), "height_um": round(H, 4), "xc": round(XC, 4),
            "sizing": {"pd": [PD_W, PD_L], "ax": [AX_W, AX_L], "pu": [PU_W, PU_L]}}
    return ly, info


if __name__ == "__main__":
    out = sys.argv[1]
    layout, info = build()
    layout.write(out)
    print(json.dumps(info))
