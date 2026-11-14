"""sky130 PDK-derived constants shared by the bitcell and the compiler generators.

Imported by design/bitcell/gen_bitcell.py, design/bitcell/gen_schematic.py,
design/compiler/gen_layout.py and design/compiler/gen_schematic.py. Everything
here is a foundry fact rather than a design choice: the GDS layer numbers, the
rules used as drawing enclosures, and the ad/as/pd/ps/nrd/nrs formula the PDK
symbols would otherwise derive with expr(). Holding them once is what keeps
layout and netlist from drifting apart silently -- the same reason
design/compiler/gen_erc_spec.py takes its stackup from the layout generator's
table (gen_erc_spec.py:10-12) instead of restating it.

Only genuinely shared values live here. A constant used by exactly one generator
(the bitcell's cell-local origins, the compiler's pad and pitch dimensions) stays
in that generator.

These scripts run under `python3 -I` / `uv run --no-project --with klayout`,
which drops the script's own directory from sys.path, so each importer puts this
file's directory (design/) on sys.path itself before importing it.
"""

# ---- GDS layer numbers (layer, datatype) ------------------------------------------
# The union of what the two generators draw: the bitcell uses no met4 or via3, the
# compiler does not label poly. An entry a generator never draws on costs nothing --
# a klayout layer holding no shapes is not written to the GDS.
LAYERS = {
    "nwell": (64, 20), "diff": (65, 20), "tap": (65, 44), "poly": (66, 20),
    "licon": (66, 44), "li": (67, 20), "mcon": (67, 44), "m1": (68, 20),
    "via": (68, 44), "m2": (69, 20), "via2": (69, 44), "m3": (70, 20),
    "via3": (70, 44), "m4": (71, 20), "nsdm": (93, 44), "psdm": (94, 20),
    "npc": (95, 20), "bound": (235, 4),
    "poly_lbl": (66, 5), "li_lbl": (67, 5), "m1_lbl": (68, 5), "m2_lbl": (69, 5),
    "m3_lbl": (70, 5), "m4_lbl": (71, 5),
}

# ---- drawing constants (um), all multiples of the 0.005 grid ----------------------
LIC = 0.17           # licon / mcon edge
VIA = 0.15
DIFF_END = 0.06      # diff beyond licon along the strip
POLY_END = 0.13      # poly beyond diff at a gate
POLY_DIFF = 0.075    # poly to unrelated diff
IMPL = 0.125         # nsdm/psdm beyond diff/tap
NPC_ENC = 0.10
NW_P = 0.18          # nwell around p diff / n tap


# ---- device geometry written into the xschem symbol attributes --------------------
def device_geometry(w):
    """The nf=1 `ad/as/pd/ps/nrd/nrs sa sb sd` attribute string for drawn width `w` (um).

    The PDK symbols derive ad/as/pd/ps/nrd/nrs with expr(); xschem < 3.4.5 leaves
    that unevaluated and `klt netlist` refuses it, so the nf=1 values are written
    out with the same formulas (ad=as=W*0.29, pd=ps=2*(W+0.29), nrd=nrs=0.29/W).
    """
    w = float(w)
    return (f"ad={w * 0.29:.4g} as={w * 0.29:.4g} pd={2 * (w + 0.29):.4g} ps={2 * (w + 0.29):.4g} "
            f"nrd={0.29 / w:.4g} nrs={0.29 / w:.4g} sa=0 sb=0 sd=0")
