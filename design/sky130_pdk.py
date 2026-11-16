"""sky130 PDK-derived constants shared by the bitcell and the compiler generators.

Imported by design/bitcell/gen_bitcell.py, design/bitcell/gen_schematic.py,
design/compiler/gen_layout.py and design/compiler/gen_schematic.py. Everything
here is a foundry fact rather than a design choice -- the GDS layer numbers, the
rules used as drawing enclosures, and the ad/as/pd/ps/nrd/nrs formula the PDK
symbols would otherwise derive with expr() -- except for the repo write
conventions, which live here so their consumers share them: write_gds()
(deterministic, byte-reproducible GDS output) for every GDS writer in the
tree, and SchematicWriter for the transistor-plus-stub block both schematic
generators emit. Holding
the facts once is what keeps
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


# ---- xschem schematic writing ------------------------------------------------------
class SchematicWriter:
    """Accumulates the component and wire lines of one xschem .sch cell.

    A repo write convention, not a foundry fact: both schematic generators
    (design/bitcell/gen_schematic.py, design/compiler/gen_schematic.py) emit
    the same transistor-plus-stub block, so it is written once here and the
    two .sch families stay byte-identical under their --check gates.
    """

    def __init__(self):
        self.lines = []
        self._labels = 0

    def pin(self, x, y, net):
        self._labels += 1
        self.lines.append(
            f"C {{devices/lab_pin.sym}} {x} {y} 0 0 {{name=l{self._labels} lab={net}}}"
        )

    def wire(self, x0, y0, x1, y1):
        self.lines.append(f"N {x0} {y0} {x1} {y1} {{}}")

    def device(self, name, model, x, y, d, g, s, b, w, l):
        """Emit one sky130_fd_pr transistor plus the stubs to its four pins.

        The stub offsets assume the PDK symbol pin placement: drain/source
        stubs run vertically (pfets drain up, nfets drain down), gate/bulk
        stubs horizontally. The nf=1 ad/as/pd/ps/nrd/nrs attribute string
        comes from device_geometry().
        """
        geo = device_geometry(w)
        self.lines.append(
            f"C {{sky130_fd_pr/{model}.sym}} {x} {y} 0 0 "
            f"{{name={name} L={l} W={w} nf=1 mult=1 {geo} model={model} spiceprefix=X}}"
        )
        dy, sy = (30, -30) if model.startswith("pfet") else (-30, 30)
        # drain / source stubs (vertical), gate / bulk stubs (horizontal)
        self.wire(x + 20, y + dy, x + 20, y + dy * 5 // 3)
        self.pin(x + 20, y + dy * 5 // 3, d)
        self.wire(x + 20, y + sy, x + 20, y + sy * 5 // 3)
        self.pin(x + 20, y + sy * 5 // 3, s)
        self.wire(x - 20, y, x - 40, y)
        self.pin(x - 40, y, g)
        self.wire(x + 20, y, x + 40, y)
        self.pin(x + 40, y, b)


# ---- GDS write convention ---------------------------------------------------------
def write_gds(ly, path):
    """Write `ly` to `path` with the repo's deterministic GDS options.

    Zeroes the BGNLIB/BGNSTR header timestamps and pins the library name so a
    regeneration is byte-identical to the committed artifact. This is a write
    convention, not a foundry fact (see the module docstring).

    The klayout import is function-local on purpose: the two schematic
    generators import this module without klayout installed and run under bare
    `python3 -I`, and a module-scope import would couple them to klayout.
    """
    import klayout.db as db
    opt = db.SaveLayoutOptions()
    opt.format = "GDS2"
    opt.gds2_write_timestamps = False
    opt.gds2_libname = "sky130_sram_compiler"
    ly.write(str(path), opt)
