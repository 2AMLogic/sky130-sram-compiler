#!/usr/bin/env python3
"""PDK-free unit tests for make_column_tb.py's opt-in extracted-DUT SNM path (#210)."""
import json
import math
import pathlib
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_column_tb as mct  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
REF_SPICE = ROOT / "design/macro/lvs/sram_snm_halfcell_col64.spice"
PINNED_EXTRACTOR = ROOT / "sim/build/pinned/snm_extract.py"


def synthetic_flat_extracted(with_star=True):
    """Minimal 64-row flat extracted netlist with lexicographic pin order (as klt extract emits)."""
    pins = sorted(mct.SNM_DUT_PINS)
    lines = [".GLOBAL vsubs", ".SUBCKT sram_snm_halfcell_col64 " + " ".join(pins[:12])]
    for i in range(12, len(pins), 12):
        lines.append("+ " + " ".join(pins[i:i + 12]))
    # Half-cell in row 0
    if with_star:
        lines += [
            "X$1 OUT__t2 IN__t0 VSS__t0 VSS__t127 sky130_fd_pr__nfet_01v8 L=0.15 W=0.84",
            "X$2 BL0__t0 WL0__t0 OUT__t1 VSS__t191 sky130_fd_pr__nfet_01v8 L=0.15 W=0.42",
            "X$255 OUT__t0 IN__t1 VDD__t0 VDD__t1 sky130_fd_pr__pfet_01v8 L=0.15 W=0.42",
            "RBL0_t0 BL0__t0 BL0 10.0",
            "RWL0_t0 WL0__t0 WL0 440.0",
        ]
    else:
        lines += [
            "X$1 OUT IN VSS VSS sky130_fd_pr__nfet_01v8 L=0.15 W=0.84",
            "X$2 BL0 WL0 OUT VSS sky130_fd_pr__nfet_01v8 L=0.15 W=0.42",
            "X$255 OUT IN VDD VDD sky130_fd_pr__pfet_01v8 L=0.15 W=0.42",
        ]
    # 63 background cells (rows 1..63)
    for r in range(1, mct.ROWS):
        suf = "" if r == 1 else f"${r - 1}"
        q_hub, qb_hub = f"Q{suf}", f"QB{suf}"
        if with_star:
            qt, qbt = f"Q__t4{r}", f"QB__t4{r}"
            blt, blbt, wlt = f"BL0__t{r}", f"BLB0__t{r}", f"WL{r}__t0"
            lines += [
                f"X$a{r} {blt} {wlt} {qt} VSS__t{r} sky130_fd_pr__nfet_01v8 L=0.15 W=0.42",
                f"X$b{r} {blbt} {wlt} {qbt} VSS__t{r} sky130_fd_pr__nfet_01v8 L=0.15 W=0.42",
                f"RBL0_t{r} {blt} BL0 12.0",
                f"RBLB0_t{r} {blbt} BLB0 12.0",
                f"RWL{r}_t0 {wlt} WL{r} 400.0",
                f"RQ_{r} {qt} {q_hub} 100.0",
                f"RQB_{r} {qbt} {qb_hub} 100.0",
            ]
        else:
            lines += [
                f"X$a{r} BL0 WL{r} {q_hub} VSS sky130_fd_pr__nfet_01v8 L=0.15 W=0.42",
                f"X$b{r} BLB0 WL{r} {qb_hub} VSS sky130_fd_pr__nfet_01v8 L=0.15 W=0.42",
            ]
    lines.append(".ENDS")
    return "\n".join(lines) + "\n"


class SnmPexTests(unittest.TestCase):
    def test_parse_subckt_pins_hierarchical_and_flat(self):
        ref_pins = mct.parse_subckt_pins(REF_SPICE.read_text())
        self.assertEqual(len(ref_pins), 71)
        self.assertEqual(ref_pins[:9], ["BL0", "BLB0", "IN", "OUT", "PCHB", "VDD", "VSS", "WL0", "WL1"])
        self.assertEqual(ref_pins[-1], "WL63")

        flat_pins = mct.parse_subckt_pins(synthetic_flat_extracted(True))
        self.assertEqual(len(flat_pins), 71)
        self.assertEqual(set(flat_pins), set(ref_pins))
        # Lexicographic order puts WL10 before WL2
        self.assertLess(flat_pins.index("WL10"), flat_pins.index("WL2"))

    def test_background_nodes_hierarchical_flat_and_device_only(self):
        hier = mct.snm_dut_background_nodes(REF_SPICE.read_text())
        self.assertEqual(len(hier), 63)
        self.assertEqual(hier[0], ("xdut.xc1_0.q", "xdut.xc1_0.qb"))
        self.assertEqual(hier[-1], ("xdut.xc63_0.q", "xdut.xc63_0.qb"))

        for with_star in (True, False):
            flat = mct.snm_dut_background_nodes(synthetic_flat_extracted(with_star))
            self.assertEqual(len(flat), 63)
            self.assertEqual(flat[0], ("xdut.q", "xdut.qb"))
            self.assertEqual(flat[1], ("xdut.q$1", "xdut.qb$1"))
            self.assertEqual(flat[-1], ("xdut.q$62", "xdut.qb$62"))

    def test_snm_dut_tb_binds_pins_by_name_and_matches_sweep(self):
        with tempfile.TemporaryDirectory() as td:
            flat_path = pathlib.Path(td) / "extracted.spice"
            flat_path.write_text(synthetic_flat_extracted(True))
            for mode, want_wl0 in (("hold", "0"), ("read", "vdd")):
                tb = mct.snm_dut_tb(mode, flat_path)
                self.assertIn("VNRM nrm 0 dc 0", tb)
                self.assertIn("BIN in 0 V='v(nrm)*v(vdd)'", tb)
                self.assertIn("VPCHB pchb 0 dc 0", tb)
                self.assertEqual(sum(1 for ln in tb.splitlines() if ln.startswith(".nodeset ")), 63)
                xdut = [ln for ln in tb.splitlines() if ln.startswith("XDUT ")][0]
                toks = xdut.split()
                pins = mct.parse_subckt_pins(flat_path.read_text())
                bound = dict(zip(pins, toks[1:-1]))
                self.assertEqual(bound["WL0"], want_wl0)
                self.assertEqual(bound["IN"], "in")
                self.assertEqual(bound["OUT"], "out")
                self.assertEqual(bound["PCHB"], "pchb")
                self.assertEqual(bound["VDD"], "vdd")
                self.assertEqual(bound["VSS"], "0")
                for r in range(1, mct.ROWS):
                    self.assertEqual(bound[f"WL{r}"], "0")

    def test_snm_dut_probe_req_matches_reference_budget_and_sweep(self):
        req = mct.snm_dut_probe_req("col_read_snm.sp")
        self.assertEqual(req["analysis"], {"kind": "dc", "args": "VNRM 0 1 0.005"})
        self.assertEqual(req["options"]["timeout_s"], 300)
        self.assertEqual(req["options"]["save_vectors"], ["v(in)", "v(out)"])
        self.assertEqual(req["backend"], "local")
        self.assertEqual(req["corners"], {"process": ["tt"], "supply_v": {"vvdd": [1.8]}, "temperature_c": [25]})

    def test_parse_subckt_pins_rejects_mismatch(self):
        with self.assertRaises(ValueError):
            mct.parse_subckt_pins(".SUBCKT sram_snm_halfcell_col64 BL0 IN OUT\n.ENDS\n")

    def test_extract_snm_rejects_non_numeric_or_non_positive(self):
        """Even if an extractor returns NaN/0/error, extract_single_curve_snm must raise."""
        stub = types.ModuleType("snm_from_artifacts")
        for bad in (((float("nan"), 0.5), (0.5, 0.5)), ((0.5, 0.5), (0.0, 0.5))):
            stub.snm_for = lambda path, pair, val=bad: val
            with mock.patch.dict(sys.modules, {"snm_from_artifacts": stub}):
                with self.assertRaises(ValueError):
                    mct.extract_single_curve_snm("dummy.json")

    @unittest.skipUnless(PINNED_EXTRACTOR.exists(), "pinned snm_extract.py not fetched")
    def test_extract_snm_rejects_flat_curve(self):
        """A non-bistable waveform must fail (never be accepted as a numeric eye_snm)."""
        with tempfile.TemporaryDirectory() as td:
            wf = pathlib.Path(td) / "waveform.raw.json"
            wf.write_text(json.dumps({
                "variables": [{"name": "v(in)"}, {"name": "v(out)"}],
                "points": [[0.0, 0.0], [0.9, 0.0], [1.8, 0.0]],
            }))
            with self.assertRaises(ValueError):
                mct.extract_single_curve_snm(wf)

    @unittest.skipUnless(PINNED_EXTRACTOR.exists(), "pinned snm_extract.py not fetched")
    def test_extract_snm_accepts_valid_bistable_curve(self):
        with tempfile.TemporaryDirectory() as td:
            wf = pathlib.Path(td) / "waveform.raw.json"
            pts = [[x / 100.0 * 1.8, 1.8 / (1.0 + math.exp(20.0 * (x / 100.0 - 0.5)))] for x in range(101)]
            wf.write_text(json.dumps({
                "variables": [{"name": "v(in)"}, {"name": "v(out)"}],
                "points": pts,
            }))
            eye, pinned = mct.extract_single_curve_snm(wf)
            self.assertGreater(eye, 0.5)
            self.assertGreater(pinned, 0.5)
            self.assertTrue(math.isfinite(eye) and math.isfinite(pinned))


if __name__ == "__main__":
    unittest.main()
