#!/usr/bin/env python3
"""PDK-free unit tests for snm_pex.py, the opt-in extracted-DUT SNM harness (#210)."""
import contextlib
import io
import json
import math
import os
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import make_column_tb  # noqa: E402
import snm_pex as sp  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
REF_SPICE = ROOT / "design/macro/lvs/sram_snm_halfcell_col64.spice"
PINNED_EXTRACTOR = ROOT / "sim/build/pinned/snm_extract.py"
FOUR_FILES = ["col_hold_snm.probe.request.json", "col_hold_snm.sp",
              "col_read_snm.probe.request.json", "col_read_snm.sp"]


def synthetic_flat_extracted(with_star=True):
    """Minimal 64-row flat extracted netlist with lexicographic pin order (as klt extract emits)."""
    pins = sorted(sp.SNM_DUT_PINS)
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
    for r in range(1, sp.ROWS):
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


def _timeout(sim_out):
    raise subprocess.TimeoutExpired("klt sim", sp.SNM_TIMEOUT_S + 30)


def _sim_error(sim_out):
    return subprocess.CompletedProcess([], 3, stdout="", stderr="ngspice: bad\nklt sim: failed")


def _no_waveform(sim_out):
    return subprocess.CompletedProcess([], 0, stdout=json.dumps({"corners": [{"measurements": []}]}), stderr="")


def _one_waveform(sim_out, vtrip=0.9):
    wf_dir = sim_out / "tt"
    wf_dir.mkdir(parents=True)
    (wf_dir / "waveform.raw.json").write_text(json.dumps(
        {"variables": [{"name": "v(in)"}, {"name": "v(out)"}], "points": [[0.0, 1.8], [1.8, 0.0]]}))
    return subprocess.CompletedProcess([], 0, stdout=json.dumps({"corners": [
        {"corner_id": "tt/1.800V/25C", "measurements": [{"name": "vtrip", "value": vtrip}]}]}), stderr="")


def fake_klt(outcomes):
    """A subprocess.run stand-in for `klt sim`: outcomes[mode](sim_out) returns the CompletedProcess
    (stdout = the report) or raises, the way the real failures do."""
    def run(cmd, capture_output, text, timeout):
        req = pathlib.Path(cmd[cmd.index("sim") + 1]).name        # col_<mode>_snm.probe.request.json
        return outcomes[req.split("_")[1]](pathlib.Path(cmd[cmd.index("-o") + 1]))
    return run


class SnmPexTests(unittest.TestCase):
    def test_parse_subckt_pins_hierarchical_and_flat(self):
        ref_pins = sp.parse_subckt_pins(REF_SPICE.read_text())
        self.assertEqual(len(ref_pins), 71)
        self.assertEqual(ref_pins[:9], ["BL0", "BLB0", "IN", "OUT", "PCHB", "VDD", "VSS", "WL0", "WL1"])
        self.assertEqual(ref_pins[-1], "WL63")

        flat_pins = sp.parse_subckt_pins(synthetic_flat_extracted(True))
        self.assertEqual(len(flat_pins), 71)
        self.assertEqual(set(flat_pins), set(ref_pins))
        # Lexicographic order puts WL10 before WL2
        self.assertLess(flat_pins.index("WL10"), flat_pins.index("WL2"))

    def test_background_nodes_hierarchical_flat_and_device_only(self):
        hier = sp.snm_dut_background_nodes(REF_SPICE.read_text())
        self.assertEqual(len(hier), 63)
        self.assertEqual(hier[0], ("xdut.xc1_0.q", "xdut.xc1_0.qb"))
        self.assertEqual(hier[-1], ("xdut.xc63_0.q", "xdut.xc63_0.qb"))

        for with_star in (True, False):
            flat = sp.snm_dut_background_nodes(synthetic_flat_extracted(with_star))
            self.assertEqual(len(flat), 63)
            self.assertEqual(flat[0], ("xdut.q", "xdut.qb"))
            self.assertEqual(flat[1], ("xdut.q$1", "xdut.qb$1"))
            self.assertEqual(flat[-1], ("xdut.q$62", "xdut.qb$62"))

    def test_snm_dut_tb_binds_pins_by_name_and_matches_sweep(self):
        with tempfile.TemporaryDirectory() as td:
            flat_path = pathlib.Path(td) / "extracted.spice"
            flat_path.write_text(synthetic_flat_extracted(True))
            for mode, want_wl0 in (("hold", "0"), ("read", "vdd")):
                tb = sp.snm_dut_tb(mode, flat_path)
                self.assertIn("VNRM nrm 0 dc 0", tb)
                self.assertIn("BIN in 0 V='v(nrm)*v(vdd)'", tb)
                self.assertIn("VPCHB pchb 0 dc 0", tb)
                self.assertEqual(sum(1 for ln in tb.splitlines() if ln.startswith(".nodeset ")), 63)
                xdut = [ln for ln in tb.splitlines() if ln.startswith("XDUT ")][0]
                toks = xdut.split()
                pins = sp.parse_subckt_pins(flat_path.read_text())
                bound = dict(zip(pins, toks[1:-1]))
                self.assertEqual(bound["WL0"], want_wl0)
                self.assertEqual(bound["IN"], "in")
                self.assertEqual(bound["OUT"], "out")
                self.assertEqual(bound["PCHB"], "pchb")
                self.assertEqual(bound["VDD"], "vdd")
                self.assertEqual(bound["VSS"], "0")
                for r in range(1, sp.ROWS):
                    self.assertEqual(bound[f"WL{r}"], "0")

    def test_snm_dut_probe_req_matches_reference_budget_and_sweep(self):
        req = sp.snm_dut_probe_req("col_read_snm.sp")
        self.assertEqual(req["analysis"], {"kind": "dc", "args": "VNRM 0 1 0.005"})
        self.assertEqual(req["options"]["timeout_s"], 300)
        self.assertEqual(req["options"]["save_vectors"], ["v(in)", "v(out)"])
        self.assertEqual(req["backend"], "local")
        self.assertEqual(req["corners"], {"process": ["tt"], "supply_v": {"vvdd": [1.8]}, "temperature_c": [25]})

    def test_sweep_and_probe_definition_is_make_column_tb_s(self):
        """The extracted leg imports the committed benches' sweep, timeout, trip point, saved
        vectors and request helpers; it must never carry its own copy."""
        for name in ("ROWS", "SNM_SWEEP", "SNM_TIMEOUT_S", "SNM_TRIP", "SNM_SAVE", "base_req", "probe_of"):
            self.assertIs(getattr(sp, name), getattr(make_column_tb, name), name)

    def test_parse_subckt_pins_rejects_mismatch(self):
        with self.assertRaises(ValueError):
            sp.parse_subckt_pins(".SUBCKT sram_snm_halfcell_col64 BL0 IN OUT\n.ENDS\n")

    def test_mode_measurements_rows(self):
        """One helper for the five former row blocks: a value passes, a missing one is an error row.
        The vtrip row carries a message only when `klt sim` produced no report at all (vtrip_msg)."""
        rows = sp._mode_measurements("hold", msg="boom", vtrip_msg="boom")
        self.assertEqual(list(rows[0]), ["name", "value", "status", "unit", "message"])
        self.assertEqual([r["name"] for r in rows], ["hold_eye_snm", "hold_pinned_snm", "hold_vtrip"])
        self.assertEqual([(r["value"], r["status"], r["unit"], r["message"]) for r in rows],
                         [(None, "error", "V", "boom")] * 3)
        for vtrip, status in ((0.9, "pass"), (None, "error")):
            rows = sp._mode_measurements("read", vtrip=vtrip, msg="bad")
            self.assertEqual([(r["value"], r["status"], r.get("message")) for r in rows],
                             [(None, "error", "bad"), (None, "error", "bad"), (vtrip, status, None)])
        rows = sp._mode_measurements("read", eye=0.4, pinned=0.5)
        self.assertEqual([(r["value"], r["status"], "message" in r) for r in rows],
                         [(0.4, "pass", False), (0.5, "pass", False), (None, "error", False)])

    def test_measure_snm_dut_maps_every_outcome_to_its_rows(self):
        """No SPICE: `klt sim` is a stand-in. Each outcome yields its rows and summary status."""
        no_report = [(None, "error", True)] * 3          # klt sim produced nothing: the message is on every row
        cases = [  # (klt outcome, extraction, per-mode rows (value, status, has message), summary status, message)
            (_timeout, {"return_value": (0.4, 0.5)}, no_report, "timeout", "exceeded 300s budget"),
            (_sim_error, {"return_value": (0.4, 0.5)}, no_report, "sim_error", "klt sim exited 3: klt sim: failed"),
            (_no_waveform, {"return_value": (0.4, 0.5)},
             [(None, "error", True), (None, "error", True), (None, "error", False)], "waveform_error", "found 0"),
            (_one_waveform, {"side_effect": ValueError("not bistable")},
             [(None, "error", True), (None, "error", True), (0.9, "pass", False)], "snm_error", "SNM extraction failed"),
            (_one_waveform, {"return_value": (0.4, 0.5)},
             [(0.4, "pass", False), (0.5, "pass", False), (0.9, "pass", False)], "pass", None),
        ]
        with tempfile.TemporaryDirectory() as td:
            for case, (outcome, extraction, want_rows, want_status, want_msg) in enumerate(cases):
                out = pathlib.Path(td) / f"case{case}"
                with self.subTest(want_status), \
                        mock.patch.object(sp.subprocess, "run", side_effect=fake_klt({"hold": outcome, "read": outcome})), \
                        mock.patch.object(sp, "extract_single_curve_snm", **extraction):
                    doc = sp.measure_snm_dut(REF_SPICE, out)
                rows = doc["corners"][0]["measurements"]
                self.assertEqual([r["name"] for r in rows],
                                 [f"{m}_{k}" for m in ("hold", "read") for k in ("eye_snm", "pinned_snm", "vtrip")])
                self.assertEqual([(r["value"], r["status"], "message" in r) for r in rows], want_rows + want_rows)
                if want_msg is not None:
                    for r in rows:
                        if "message" in r:
                            self.assertIn(want_msg, r["message"])
                summary = json.loads((out / "snm_summary.json").read_text())
                self.assertEqual([summary["modes"][m]["status"] for m in ("hold", "read")], [want_status] * 2)
                self.assertEqual(summary["top"], sp.SNM_DUT_TOP)

    def test_cli_snmdut_writes_four_files_into_outdir_or_env(self):
        """--snm-dut: --outdir, else $KLT_PEX_ARTIFACTS_DIR (what klt pex exports); nothing is run."""
        with tempfile.TemporaryDirectory() as td:
            for out, argv in ((pathlib.Path(td) / "flag", ["--outdir", str(pathlib.Path(td) / "flag")]),
                              (pathlib.Path(td) / "env", [])):
                stdout = io.StringIO()
                with mock.patch.dict(os.environ, {"KLT_PEX_ARTIFACTS_DIR": str(pathlib.Path(td) / "env")}), \
                        mock.patch.object(sp.subprocess, "run", side_effect=AssertionError("must not run")), \
                        contextlib.redirect_stdout(stdout):
                    sp.main(["--snm-dut"] + argv + [str(REF_SPICE)])
                self.assertEqual(sorted(p.name for p in out.iterdir()), FOUR_FILES)
                self.assertIn(f"snm_pex: wrote 4 extracted-DUT SNM files under {out.resolve()}", stdout.getvalue())
                self.assertEqual((out / "col_hold_snm.sp").read_text(), sp.snm_dut_tb("hold", str(REF_SPICE)))
                self.assertEqual((out / "col_read_snm.probe.request.json").read_text(),
                                 json.dumps(sp.snm_dut_probe_req("col_read_snm.sp"), indent=2) + "\n")

    def test_cli_measure_wires_every_option(self):
        doc = {"corners": [{"corner_id": "tt/1.800V/25C", "measurements": []}]}
        stdout = io.StringIO()
        with mock.patch.object(sp, "measure_snm_dut", return_value=doc) as measure, \
                contextlib.redirect_stdout(stdout):
            sp.main(["--measure-snm-dut", "--klt", "uvx --from klayout-tools==0.9.0 klt", "--outdir", "/scratch/o",
                     "--top", "top_x", "--pdk-root", "/pdk", str(REF_SPICE)])
        measure.assert_called_once_with(str(REF_SPICE), "/scratch/o", klt_cmd="uvx --from klayout-tools==0.9.0 klt",
                                        top="top_x", pdk_root="/pdk")
        self.assertEqual(json.loads(stdout.getvalue()), doc)

    def test_cli_usage_lists_every_option(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout), self.assertRaises(SystemExit) as cm:
            sp.main(["--help"])
        self.assertEqual(cm.exception.code, 0)
        for opt in ("--snm-dut", "--measure-snm-dut", "--klt", "--outdir", "--top", "--pdk-root", "<dut.spice>"):
            self.assertIn(opt, stdout.getvalue())

    def test_cli_rejects_bad_invocations(self):
        """One mode is required, the two conflict, an option consumes the next word, and --outdir
        is mandatory unless klt pex exported KLT_PEX_ARTIFACTS_DIR: exit 2, nothing written."""
        bad = [[str(REF_SPICE)],                                     # no mode
               ["--snm-dut"],                                        # no DUT netlist
               ["--snm-dut", "--measure-snm-dut", str(REF_SPICE)],    # both modes
               ["--snm-dut", "--klt", str(REF_SPICE)],               # --klt takes the netlist: no positional left
               ["--snm-dut", "--outdir", str(REF_SPICE)]]            # --outdir takes the netlist
        with tempfile.TemporaryDirectory() as td, mock.patch.dict(os.environ, {"KLT_PEX_ARTIFACTS_DIR": td}), \
                contextlib.redirect_stderr(io.StringIO()):
            for argv in bad:
                with self.subTest(argv=argv), self.assertRaises(SystemExit) as cm:
                    sp.main(argv)
                self.assertEqual(cm.exception.code, 2)
            os.environ.pop("KLT_PEX_ARTIFACTS_DIR")
            with self.assertRaises(SystemExit) as cm:
                sp.main(["--snm-dut", str(REF_SPICE)])
            self.assertEqual(cm.exception.code, 2)
            self.assertEqual(list(pathlib.Path(td).iterdir()), [])

    def test_extract_snm_rejects_non_numeric_or_non_positive(self):
        """Even if an extractor returns NaN/0/error, extract_single_curve_snm must raise."""
        stub = types.ModuleType("snm_from_artifacts")
        for bad in (((float("nan"), 0.5), (0.5, 0.5)), ((0.5, 0.5), (0.0, 0.5))):
            stub.snm_for = lambda path, pair, val=bad: val
            with mock.patch.dict(sys.modules, {"snm_from_artifacts": stub}):
                with self.assertRaises(ValueError):
                    sp.extract_single_curve_snm("dummy.json")

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
                sp.extract_single_curve_snm(wf)

    @unittest.skipUnless(PINNED_EXTRACTOR.exists(), "pinned snm_extract.py not fetched")
    def test_extract_snm_accepts_valid_bistable_curve(self):
        with tempfile.TemporaryDirectory() as td:
            wf = pathlib.Path(td) / "waveform.raw.json"
            pts = [[x / 100.0 * 1.8, 1.8 / (1.0 + math.exp(20.0 * (x / 100.0 - 0.5)))] for x in range(101)]
            wf.write_text(json.dumps({
                "variables": [{"name": "v(in)"}, {"name": "v(out)"}],
                "points": pts,
            }))
            eye, pinned = sp.extract_single_curve_snm(wf)
            self.assertGreater(eye, 0.5)
            self.assertGreater(pinned, 0.5)
            self.assertTrue(math.isfinite(eye) and math.isfinite(pinned))


if __name__ == "__main__":
    unittest.main()
