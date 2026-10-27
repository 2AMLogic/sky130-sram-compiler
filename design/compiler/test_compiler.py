"""PDK-free tests for the SRAM compiler: python3 -I design/compiler/test_compiler.py"""
import pathlib
import re
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I drops the script dir
import cells  # noqa: E402
import sram_compile as sc  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent


def parse(text):
    """-> {subckt: (ports, [instance token lists])} from logical netlist lines."""
    subs, cur = {}, None
    for ln in cells.logical_lines(text):
        t = ln.split()
        if ln.startswith(".subckt"):
            cur = subs[t[1]] = (t[2:], [])
        elif ln.startswith(".ends"):
            cur = None
        elif cur is not None and t[0][0] == "X":
            cur[1].append(t)
    return subs


class Compiler(unittest.TestCase):
    def test_reference_matches_committed(self):
        text = sc.generate(256, 32, 4)
        self.assertEqual(text, sc.generate(256, 32, 4))
        self.assertEqual(text, (HERE / "macro/sram_256x32_m4.spice").read_text())

    def test_geometry(self):
        g = sc.geometry(256, 32, 4)
        self.assertEqual((g["rows"], g["cols"], g["nc"], g["nr"], g["na"]), (64, 128, 2, 6, 8))
        self.assertEqual(sc.geometry(1024, 8, 1)["rows"], 1024)
        self.assertEqual(sc.geometry(16, 64, 8)["rows"], 2)

    def test_range_rejected(self):
        for bad in [(8, 32, 1), (2048, 32, 1), (100, 32, 1), (256, 4, 1), (256, 65, 1),
                    (256, 32, 3), (256, 32, 16), (256, 32.0, 4)]:
            with self.assertRaises(sc.RangeError, msg=str(bad)):
                sc.generate(*bad)

    def check_instance(self, words, bits, mux):
        subs = parse(sc.generate(words, bits, mux))
        top = sc.top_name(words, bits, mux)
        g = sc.geometry(words, bits, mux)
        self.assertEqual(subs[top][0], sc.top_ports(words, bits, mux))
        count = {}
        for t in subs[top][1]:
            cell, nets = t[-1], t[1:-1]
            count[cell] = count.get(cell, 0) + 1
            self.assertIn(cell, subs, cell)
            self.assertEqual(len(nets), len(subs[cell][0]), t)
        self.assertEqual(count["bitcell_6t"], g["rows"] * g["cols"])
        self.assertEqual(count["sram_wldrv"], g["rows"])
        self.assertEqual(count["sram_senseamp"], bits)
        self.assertEqual(count["sram_wdrv"], bits)
        self.assertEqual(count["sram_precharge"], g["cols"])
        self.assertEqual(count["sram_colmux"], g["cols"])
        # every internal net is driven/used at least twice (no dangling name typos)
        uses = {}
        for t in subs[top][1]:
            for n in t[1:-1]:
                uses[n] = uses.get(n, 0) + 1
        for n, k in uses.items():
            self.assertTrue(k >= 2 or n in subs[top][0], f"dangling net {n}")

    def test_instances(self):
        for spec in [(256, 32, 4), (16, 8, 8), (1024, 64, 1), (64, 9, 2), (16, 33, 4), (512, 16, 8)]:
            with self.subTest(spec=spec):
                self.check_instance(*spec)

    def test_only_logic_devices(self):
        models = set(re.findall(r"sky130_fd_pr__(\w+)", sc.generate(256, 32, 4)))
        self.assertEqual(models, {"nfet_01v8", "pfet_01v8"})

    def test_cell_netlists_match_definitions(self):
        for name, (ports, devs) in cells.CELLS.items():
            subs = parse((HERE / "netlist" / f"{name}.spice").read_text())
            self.assertEqual(subs[name][0], ports)
            self.assertEqual(len(subs[name][1]), len(devs))


unittest.main()
