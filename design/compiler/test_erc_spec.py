"""Tests for gen_erc_spec.py (needs klayout):
  uv run --no-project --with klayout python -I design/compiler/test_erc_spec.py
"""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import gen_erc_spec as ge  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


class ErcSpec(unittest.TestCase):
    def test_committed_reference(self):
        self.assertEqual((ROOT / "layout/erc/erc_macro_spec.json").read_text(), ge.render(ge.macro_spec(256, 32, 4)))
        self.assertEqual((ROOT / "layout/erc/erc_control_spec.json").read_text(), ge.render(ge.control_spec()))

    def test_supplies_are_vdd_vss_and_ties_declared(self):
        s = ge.macro_spec(256, 32, 4)
        self.assertEqual([(n["name"], n["kind"]) for n in s["nets"]], [("VDD", "supply"), ("VSS", "supply")])
        self.assertTrue(all(n["roles"] for n in s["nets"]))
        self.assertEqual([t["name"] for t in s["ties"]], ["nwell_tie", "psub_array_straps", "psub_colmux_taps"])

    def test_spec_follows_size(self):
        a, b = ge.macro_spec(256, 32, 4), ge.macro_spec(64, 8, 2)
        self.assertNotEqual(a, b)
        straps = lambda s: s["ties"][1]["well_boxes"]           # noqa: E731
        taps = lambda s: s["ties"][2]["well_boxes"]             # noqa: E731
        self.assertEqual(len(straps(a)), 5)                      # 64 rows: below row 0, every 16, above the last
        self.assertEqual(len(straps(b)), 3)                      # 32 rows
        self.assertEqual(len(taps(a)), 32 * 4 // 4 * 4)          # one bulk tap per column (bits * mux)
        self.assertEqual(len(taps(b)), 8 * 2)

    def test_control_spec_covers_pdn_straps(self):
        names = {s["name"] for s in ge.control_spec()["stackup"]}
        self.assertTrue({"met1", "met4", "met5"} <= names)       # P&R response power.straps layers


if __name__ == "__main__":
    unittest.main()
