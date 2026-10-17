"""Build the marker-state test layouts for the SRAM core-area marker study.

Usage:  <klt python> -I build_cases.py <pdk_sky130A_dir> <outdir>

Marker under test: areaid.ce = GDS 81/2 (the "core" area marker the foundry
SRAM bitcell carries; the PDK-native klayout deck keys relaxed rules off it).
Writes one single-top-cell GDS per case into <outdir>.
"""
import sys
import klayout.db as db

pdk, out = sys.argv[1], sys.argv[2]
MARK = (81, 2)          # areaid.ce
STDC = [(81, 4), (81, 23)]  # areaid.sc / areaid.sc-adjacent, std-cell ids


def load(path, cell):
    ly = db.Layout()
    ly.read(path)
    src = ly.cell(cell)
    new = db.Layout()
    new.dbu = ly.dbu
    top = new.create_cell(cell)
    top.copy_tree(src)  # preserves hierarchy
    return new, new.cell(cell)


def strip(layout, cell, lp):
    li = layout.find_layer(*lp)
    if li is None:
        return
    for c in layout.each_cell():
        c.shapes(li).clear()


def save(layout, name):
    layout.write(f"{out}/{name}.gds")


def add_marker(layout, top, box_um):
    li = layout.layer(*MARK)
    top.shapes(li).insert(db.DBox(*box_um))


# ---- foundry bitcell -------------------------------------------------------
sram = f"{pdk}/libs.ref/sky130_sram_macros/gds/sram_1rw1r_32_256_8_sky130.gds"
CELL = "sky130_fd_bd_sram__openram_dp_cell"

l, t = load(sram, CELL)
bb = t.dbbox()
save(l, "foundry_with_marker")

l, t = load(sram, CELL)
strip(l, t, MARK)
save(l, "foundry_marker_stripped")

# partial: marker clipped to the left half of the cell bbox
l, t = load(sram, CELL)
mid = (bb.left + bb.right) / 2
strip(l, t, MARK)
t.shapes(l.layer(*MARK)).insert(db.DBox(bb.left, bb.bottom, mid, bb.top))
save(l, "foundry_marker_partial")

# ---- logic-rule cell (stock hd std cell, std-cell id layers stripped) ------
hd = f"{pdk}/libs.ref/sky130_fd_sc_hd/gds/sky130_fd_sc_hd.gds"
LC = "sky130_fd_sc_hd__nand2_1"


def logic(name, box):
    l, t = load(hd, LC)
    for lp in STDC + [MARK]:
        strip(l, t, lp)
    b = t.dbbox()
    if box:
        add_marker(l, t, box(b))
    save(l, name)


logic("logic_nomarker", None)  # outside
logic("logic_inside_margin", lambda b: (b.left - 1, b.bottom - 1, b.right + 1, b.top + 1))
logic("logic_inside_abut", lambda b: (b.left, b.bottom, b.right, b.top))
logic("logic_edge_straddle", lambda b: (b.left - 1, b.bottom - 1, (b.left + b.right) / 2, b.top + 1))

# baseline: logic cell with its own std-cell ids intact, no 81/2
l, t = load(hd, LC)
save(l, "logic_stock_baseline")

# ---- synthetic li1 probe: legal only under the core-area li rules ----------
# Two li1 bars 0.15 wide with 0.15 gap: violates the periphery rule
# (li.1/li.3 = 0.17) but meets the areaid.ce core rule (li.7/li.8 = 0.14).
LI = (67, 20)


def probe(name, box):
    l = db.Layout()
    l.dbu = 0.001
    t = l.create_cell("probe")
    li = l.layer(*LI)
    t.shapes(li).insert(db.DBox(0.00, 0, 0.15, 1.0))
    t.shapes(li).insert(db.DBox(0.30, 0, 0.45, 1.0))
    if box:
        t.shapes(l.layer(*MARK)).insert(db.DBox(*box))
    save(l, name)


probe("probe_li_outside", None)
probe("probe_li_inside", (-1, -1, 2, 2))
probe("probe_li_inside_flush", (0, 0, 0.45, 1.0))
probe("probe_li_straddle_gap", (-1, -1, 0.225, 2))
probe("probe_li_straddle_bar", (-1, -1, 0.375, 2))
