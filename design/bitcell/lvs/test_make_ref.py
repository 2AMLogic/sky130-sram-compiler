"""PDK-free tests for the bitcell LVS negative-control rewrite:
python3 -I design/bitcell/lvs/test_make_ref.py"""
import json
import pathlib
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I drops the script dir
import make_ref  # noqa: E402


def netlist(w_token):
    """A minimal committed-netlist-shaped input (see netlist/bitcell_6t.spice)."""
    return "\n".join([
        ".subckt bitcell_6t BL BLB WL VDD VSS",
        "XMPL Q QB VDD VDD sky130_fd_pr__pfet_01v8 L=0.15 W=0.42 nf=1 ad=0.1218 as=0.1218 pd=1.42 ps=1.42",
        "XMNL Q QB VSS VSS sky130_fd_pr__nfet_01v8 L=0.15 W=0.84 nf=1 ad=0.2436 as=0.2436 pd=2.26 ps=2.26",
        f"XMAL BL WL Q VSS sky130_fd_pr__nfet_01v8 L=0.15 W={w_token} nf=1 ad=0.1218 as=0.1218 pd=1.42 ps=1.42",
        "+ nrd=0.6905 nrs=0.6905 sa=0 sb=0 sd=0 mult=1 m=1",
        ".ends",
    ]) + "\n"


def w_tokens(line):
    return [t for t in line.split() if t.startswith("W=")]


def xmal(text):
    return next(l for l in text.splitlines() if l.startswith("XMAL "))


# (ax_w, netlist W token, expected perturbed W token)
CASES = [
    (0.42, "0.42", "0.52"),  # status quo
    (1.0, "1.0", "1.1"),     # :g drops the .0 the netlist carries; the old anchor matched a prefix
    (2.0, "2.0", "2.1"),
    (0.5, "0.5", "0.6"),
    (0.7, "0.7", "0.8"),     # emit-side float noise: str(0.7 + 0.1) is 0.7999999999999999
    (0.84, "0.84", "0.94"),
]

# (ax_w, netlist W token): a stale or partial-width netlist must raise, not perturb
STALE = [
    (1.0, "0.42"),
    (0.42, "0.425"),  # longer token
    (0.42, "0.4"),    # shorter token
]


class MakeRef(unittest.TestCase):
    def test_perturbs_to_a_single_valid_numeric_literal(self):
        for ax_w, token, want in CASES:
            with self.subTest(ax_w=ax_w, token=token):
                _, bad = make_ref.rewrite(ax_w, netlist(token))
                self.assertEqual(w_tokens(xmal(bad)), [f"W={want}"])

    def test_stale_netlist_raises_the_anchor_error(self):
        for ax_w, token in STALE:
            with self.subTest(ax_w=ax_w, token=token):
                with self.assertRaises(make_ref.AnchorError):
                    make_ref.rewrite(ax_w, netlist(token))

    def test_anchor_error_names_the_token_the_pattern_searches(self):
        # the pre-fix message formatted with :g and named `XMAL W=1` for ax.w = 1.0
        with self.assertRaises(make_ref.AnchorError) as cm:
            make_ref.rewrite(1.0, netlist("0.42"))
        self.assertIn("XMAL W=1.0", str(cm.exception))

    def test_reference_keeps_the_sizing_width_and_moves_the_bulk(self):
        good, _ = make_ref.rewrite(1.0, netlist("1.0"))
        lines = good.splitlines()
        self.assertEqual(lines[0], ".subckt bitcell_6t BL BLB WL VDD VSS vsubs")
        self.assertIn(" vsubs ", xmal(good))
        self.assertEqual(w_tokens(xmal(good)), ["W=1.0"])
        xmnl = next(l for l in lines if l.startswith("XMNL "))
        self.assertTrue(xmnl.startswith("XMNL Q QB VSS vsubs "))

    def test_perturbed_value_must_be_a_plain_numeric_literal(self):
        make_ref.assert_plain_numeric("1.1")
        make_ref.assert_plain_numeric("0.52")
        for token in ("1.1.0", "0.52um", ""):
            with self.subTest(token=token):
                with self.assertRaises(make_ref.AnchorError):
                    make_ref.assert_plain_numeric(token)

    def test_main_writes_both_netlists_and_exits_1_on_a_stale_netlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            (tmp / "sizing.json").write_text(json.dumps({"ax": {"w": 0.42}}))
            (tmp / "cell.spice").write_text(netlist("0.42"))
            make_ref.main(["make_ref.py", str(tmp / "sizing.json"), str(tmp / "cell.spice"), str(tmp / "out")])
            self.assertEqual(w_tokens(xmal((tmp / "out/ref_bad.spice").read_text())), ["W=0.52"])
            self.assertIn(" vsubs ", xmal((tmp / "out/ref.spice").read_text()))

            (tmp / "stale.spice").write_text(netlist("0.43"))
            with self.assertRaises(SystemExit) as cm:
                make_ref.main(["make_ref.py", str(tmp / "sizing.json"), str(tmp / "stale.spice"), str(tmp / "out2")])
            self.assertNotEqual(cm.exception.code, 0)  # sys.exit(msg): interpreter exits 1
            self.assertIn("negative-control anchor", str(cm.exception.code))


unittest.main()
