"""Tests for the layout generator (needs klayout's python module, no PDK):
  uv run --no-project --with klayout python -I design/compiler/test_layout.py
"""
import json
import pathlib
import sys
import tempfile
import unittest

import klayout.db as db

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I drops the script dir
import gen_layout as gl  # noqa: E402
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
        ly, T, env = gl.build(words, bits, mux)
        g = sc.geometry(words, bits, mux)
        self.assertEqual(count_instances(ly, T, gl.BITCELL), g["rows"] * g["cols"])
        self.assertEqual(count_instances(ly, T, "sram_precharge"), g["cols"])
        self.assertEqual(sum(count_instances(ly, T, f"sram_colmux_m{m}") for m in range(mux)), g["cols"])
        self.assertEqual(count_instances(ly, T, "sram_senseamp"), bits)
        self.assertEqual(count_instances(ly, T, "sram_wdrv"), bits)
        # macro pins are exactly the netlist ports
        self.assertEqual(sorted(T.pins), sorted(sc.top_ports(words, bits, mux)))
        # array height = rows * pitch + strap rows
        self.assertAlmostEqual(env["ag"].height,
                               g["rows"] * gl.PITCH_Y + len(env["ag"].B) * gl.STRAP_H, places=6)
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


unittest.main()
