"""Tests for the layout generator (needs klayout's python module, no PDK):
  uv run --no-project --with klayout python -I design/compiler/test_layout.py
"""
import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

import klayout.db as db

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I drops the script dir
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "bitcell"))
import gen_layout as gl  # noqa: E402
import gen_bitcell as gb  # noqa: E402
import sram_compile as sc  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def gds_bytes(ly):
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp) / "x.gds"
        gl.write_gds(ly, p)
        return p.read_bytes()


def count_instances(ly, top, cell_name):
    """Instances of `cell_name` in the flattened hierarchy of `top` (arrays expanded)."""
    target = ly.cell(cell_name).cell_index()
    memo = {}

    def n(ci):
        if ci in memo:
            return memo[ci]
        total = 0
        c = ly.cell(ci)
        for inst in c.each_inst():
            k = max(1, inst.na) * max(1, inst.nb)
            child = inst.cell_index
            total += k * ((1 if child == target else 0) + n(child))
        memo[ci] = total
        return total

    return n(top.cell.cell_index())


class Layout(unittest.TestCase):
    def test_deterministic(self):
        a = gds_bytes(gl.build(16, 8, 2)[0])
        b = gds_bytes(gl.build(16, 8, 2)[0])
        self.assertEqual(a, b)

    def test_committed_reference(self):
        committed = ROOT / "layout/sram_256x32_m4.gds"
        if not committed.exists():
            self.skipTest("reference GDS not committed yet")
        self.assertEqual(gds_bytes(gl.build(256, 32, 4)[0]), committed.read_bytes())

    def test_bench_slice_deterministic(self):
        self.assertEqual(gds_bytes(gl.build_bench_slice()[0]), gds_bytes(gl.build_bench_slice()[0]))

    def test_committed_bench_slice(self):
        committed = ROOT / "layout/sram_col_slice.gds"
        if not committed.exists():
            self.skipTest("bench-slice GDS not committed yet")
        self.assertEqual(gds_bytes(gl.build_bench_slice()[0]), committed.read_bytes())

    def test_bench_slice_labels_name_every_pin(self):
        """Every pin the PEX benches declare is a top-cell label on the slice (extraction
        keeps each an addressable net; see sim/column/lib/make_column_tb.py SLICE_PINS)."""
        import pathlib
        pins = pathlib.Path(ROOT / "sim/column/tb/pex/sram_col_slice.spice")
        if not pins.exists():
            self.skipTest("generated slice DUT not present")
        header = next(l for l in pins.read_text().splitlines() if l.startswith(".subckt"))
        declared = set(header.split()[2:])
        ly, T, _ = gl.build_bench_slice()
        labelled = set()
        for li in ly.layer_indexes():
            it = T.cell.begin_shapes_rec(li)
            while not it.at_end():
                s = it.shape()
                if s.is_text():
                    labelled.add(s.text.string.split("|")[0])
                it.next()
        self.assertEqual(declared, declared & labelled, f"unlabelled pins: {sorted(declared - labelled)}")


    def test_bitcell_constants_sit_on_the_cell(self):
        """BL/BLB/VSS m1 columns and VDD m2 columns are where the generator assumes."""
        ly = db.Layout()
        ly.read(str(gl.BITCELL_GDS))
        c = ly.cell(gl.BITCELL)
        m1 = db.Region(c.begin_shapes_rec(ly.layer(*gl.LAYERS["m1"])))
        m2 = db.Region(c.begin_shapes_rec(ly.layer(*gl.LAYERS["m2"])))
        for x in (gl.BL_X, gl.BLB_X) + gl.VSS_XS:
            probe = db.Region(db.Box(round(x * 1000) - 50, 100, round(x * 1000) + 50, 200))
            self.assertTrue((m1 & probe).area() == probe.area(), x)
        for x in gl.VDD_XS:
            probe = db.Region(db.Box(round(x * 1000) - 140, 100, round(x * 1000) + 140, 200))
            self.assertTrue((m2 & probe).area() == probe.area(), x)
        bb = c.dbbox()
        self.assertEqual((round(bb.width(), 3), round(bb.height(), 3)), (gl.BC_W, gl.BC_H))

    def check_instance(self, words, bits, mux):
        ly, T, geom = gl.build(words, bits, mux)
        g = sc.geometry(words, bits, mux)
        self.assertEqual(count_instances(ly, T, gl.BITCELL), g["rows"] * g["cols"])
        self.assertEqual(count_instances(ly, T, "sram_precharge"), g["cols"])
        self.assertEqual(sum(count_instances(ly, T, f"sram_colmux_m{m}") for m in range(mux)), g["cols"])
        self.assertEqual(count_instances(ly, T, "sram_senseamp"), bits)
        self.assertEqual(count_instances(ly, T, "sram_wdrv"), bits)
        # macro pins are exactly the netlist ports
        self.assertEqual(sorted(T.pins), sorted(sc.top_ports(words, bits, mux)))
        # array height = rows * pitch + strap rows
        self.assertAlmostEqual(geom.ag.height,
                               g["rows"] * gl.PITCH_Y + len(geom.ag.B) * gl.STRAP_H, places=6)
        return T

    def test_instances(self):
        for spec in [(16, 8, 2), (64, 16, 2), (32, 9, 1), (256, 16, 8), (128, 8, 4)]:
            with self.subTest(spec=spec):
                self.check_instance(*spec)

    def test_size_scales_with_rows_and_columns(self):
        a = self.check_instance(16, 8, 2).size
        b = self.check_instance(64, 8, 2).size          # 4x the rows
        c = self.check_instance(16, 16, 2).size         # 2x the columns
        self.assertGreater(b[1], a[1] + 3 * 8 * gl.PITCH_Y * 0.9)
        self.assertGreater(c[0], a[0] + 8 * 2 * gl.BC_W * 0.9)

    def test_build_returns_named_geometry(self):
        """build()'s third value is the named geometry record, not a dict."""
        geom = gl.build(16, 8, 2)[2]
        self.assertEqual(sorted(vars(geom)), ["ag", "hcm"])
        self.assertEqual((geom.ag.rows, geom.ag.cols), (8, 16))
        self.assertGreater(geom.hcm, 0)

    def test_out_of_range_rejected(self):
        for bad in [(8, 32, 1), (256, 4, 1), (256, 32, 3)]:
            with self.assertRaises(sc.RangeError):
                gl.build(*bad)

    def test_pins_in_socket_descriptor(self):
        _, T, _ = gl.build(16, 8, 2)
        d = gl.socket_descriptor(T, "x")
        self.assertEqual(sorted(p["name"] for p in d["pins"]), sorted(sc.top_ports(16, 8, 2)))
        bb = d["outline"]
        for p in d["pins"]:
            self.assertTrue(bb["x0"] <= p["x"] <= bb["x1"] and bb["y0"] <= p["y"] <= bb["y1"], p["name"])
        json.dumps(d)


class SnmHalfcellColumn(unittest.TestCase):
    """--snm-halfcell: the dedicated DC SNM column top, through the same generator entry point."""

    def test_bitcell_generator_unchanged_by_half_mode(self):
        self.assertEqual(gds_bytes(gb.build()[0]), (ROOT / "design/bitcell/bitcell_6t.gds").read_bytes())

    def test_structure(self):
        ly, T, geom = gl.build_snm_halfcell_column()
        self.assertEqual((geom.ag.rows, geom.ag.cols), (64, 1))
        self.assertEqual(count_instances(ly, T, gl.BITCELL), 63)
        self.assertEqual(count_instances(ly, T, gb.HALF_CELL), 1)
        self.assertEqual(count_instances(ly, T, "sram_precharge"), 1)
        self.assertEqual(sorted(T.pins), ["PCHB", "VDD", "VSS"])
        texts = set()
        for lbl in ("li_lbl", "m1_lbl", "m3_lbl"):
            texts |= {sh.text.string for sh in ly.top_cell().shapes(ly.layer(*gl.LAYERS[lbl])).each()
                      if sh.is_text()}
        want = {"BL0", "BLB0", "IN", "OUT", "PCHB", "VDD", "VSS"} | {f"WL{r}" for r in range(64)}
        self.assertTrue(want <= texts, want - texts)

    def test_half_cell_is_cut_from_the_bitcell_devices(self):
        """Same footprint and sizing as the bitcell; only the left inverter + access device are drawn."""
        hly, info = gb.build(half=True)
        bb = hly.top_cell().dbbox()
        self.assertEqual((round(bb.width(), 3), round(bb.height(), 3)), (gl.BC_W, gl.BC_H))
        self.assertEqual(info["sizing"], gb.build()[1]["sizing"])
        full = gb.build()[0]
        for layer in ("poly", "diff", "licon"):
            n_half = db.Region(hly.top_cell().begin_shapes_rec(hly.layer(*gl.LAYERS[layer]))).count()
            n_full = db.Region(full.top_cell().begin_shapes_rec(full.layer(*gl.LAYERS[layer]))).count()
            self.assertLess(n_half, n_full, layer)

    def test_deterministic_and_same_entry_point(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = pathlib.Path(tmp) / "a.gds", pathlib.Path(tmp) / "b.gds"
            self.assertEqual(gl.main(["gen_layout.py", "--snm-halfcell", "-o", str(a)]), 0)
            self.assertEqual(gl.main(["gen_layout.py", "--snm-halfcell", "-o", str(b)]), 0)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(gl.main(["gen_layout.py", "--snm-halfcell", "--check", str(a)]), 0)
        self.assertEqual(gl.main(["gen_layout.py", "--snm-halfcell", "16", "8", "2"]), 2)

    def test_lvs_reference_is_current(self):
        r = subprocess.run([sys.executable, "-I", str(ROOT / "design/macro/lvs/make_snm_ref.py"), "--check"])
        self.assertEqual(r.returncode, 0)


class Usage(unittest.TestCase):
    """A malformed command line is a usage error: exit 2 with the usage text, never a traceback."""

    def test_value_taking_flag_given_last_is_usage_error(self):
        """Every value-taking flag as the last token exits 2 instead of indexing past the end of argv."""
        for argv in (["--check"], ["-o"], ["--bench-slice"], ["--check-bench-slice"],
                     ["--snm-halfcell", "--check"], ["--socket"], ["--lef"], ["--check-lef"], ["--check-socket"]):
            err = io.StringIO()
            with self.subTest(argv=argv), contextlib.redirect_stderr(err):
                self.assertEqual(gl.main(["gen_layout.py", *argv]), 2)
                self.assertEqual(err.getvalue(), gl.__doc__ + "\n")


unittest.main()
