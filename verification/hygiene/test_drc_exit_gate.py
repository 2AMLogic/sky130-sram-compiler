"""PDK-free regression test: the graded DRC runner must gate `klt drc` exit
codes, and the evidence writer must validate the run's envelopes before copying
them over the committed evidence.

Usage: python3 -I verification/hygiene/test_drc_exit_gate.py

Issue #183: verification/drc/run_drc.sh ran its graded `klt drc` calls with a
trailing `|| true`, discarding every exit code, so a deck/klt crash (exit 1 or
2) silently produced an empty or partial report -- and verification/drc/
make_record.py copied those envelopes over design/compiler/evidence/item3.json
and evidence/item3-digital.json before parsing them, so the JSONDecodeError
fired with the committed evidence already clobbered. The three_deck_drc.sh
convention (0 clean, 3 violations and 4 coverage_unknown are normal outcomes;
any other exit aborts with that code) now applies to the graded runner, and
make_record.py parses and validates both graded envelopes before any copyfile.

This suite stubs `klt` and the klayout python on PATH (no PDK install, no
klayout engine -- the test_pdk_resolution.py shape) and asserts, against the
real scripts:
  - run_drc.sh completes on klt exits 0, 3 and 4 (the legitimate outcomes) and
    aborts with klt's exit code, naming the failure, on any other exit;
  - make_record.py refuses an empty, keyless or malformed envelope with both
    committed evidence files byte-identical and no record written;
  - a valid run still copies the envelopes unmodified and writes the record.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
RUN_DRC = REPO / "verification/drc/run_drc.sh"
MAKE_RECORD = REPO / "verification/drc/make_record.py"

GRADED_ENVELOPE = json.dumps({
    "schema_version": 3,
    "status": "clean",
    "violation_count": 0,
    "rule_counts": {},
    "violations": [],
    "provenance": {"deck": {"name": "sky130", "content_hash": "sha256:stub-deck",
                            "released": True},
                   "klayout_version": "0.30.12",
                   "input": {"content_hash": "sha256:stub-input"}},
    "negative_control": {"file": "verification/drc/neg_probe.gds", "status": "passed",
                         "violation_count": 2,
                         "rules_found": ["met1.area.1", "met1.width.1"]},
    "coverage": {"layers_in_stream_without_rules": [], "rules_skipped": [],
                 "deck_scope": [], "unchecked_rules": 0,
                 "marker_blind_layers_in_stream": 0},
})

SEAM_ENVELOPE = json.dumps({
    "status": "violations", "rule_counts": {"met1.width.1": 2},
    "violations": [{"rule": "met1.width.1", "bbox": [1, 2, 3, 4]},
                   {"rule": "met1.width.1", "bbox": [5, 6, 7, 8]}]})

SCAN_JSON = json.dumps({"cells": 1, "layer_81_shapes": [], "areaid_ce_shapes": 0})

# klt stub: `--version` succeeds (make_record.py provenance lookup); the graded
# runs (calls carrying --negative-control) exit KLT_STUB_GRADED_RC, the seam
# control exits KLT_STUB_SEAM_RC, everything else (three_deck_drc.sh) exits 0 --
# so a failure reached through one gate cannot be credited to another runner's.
KLT_STUB = """#!/bin/sh
if [ "$1" = "--version" ]; then echo "klt 0.0-test-stub"; exit 0; fi
rc=0
case "$*" in
  *--negative-control*) rc=${KLT_STUB_GRADED_RC:-0} ;;
  *macro_seam_probe*)   rc=${KLT_STUB_SEAM_RC:-0} ;;
esac
echo "$KLT_STUB_ENVELOPE"
exit "$rc"
"""

KLT_PY_STUB = f"""#!/bin/sh
echo '{SCAN_JSON}'
"""


class StubEnv(unittest.TestCase):
    """Stubs on PATH, a fake sky130A variant dir, and a scrubbed environment."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name, body in (("klt", KLT_STUB), ("klt-python-stub", KLT_PY_STUB)):
            p = self.bin / name
            p.write_text(body)
            p.chmod(0o755)
        variant = self.root / "sky130A"
        deck = variant / "libs.tech/klayout/drc/sky130A_mr.drc"
        deck.parent.mkdir(parents=True)
        deck.write_text("# stub deck\n")
        self.env = {k: v for k, v in os.environ.items()
                    if k not in ("PDK", "PDK_ROOT", "SKY130_VARIANT_DIR", "KLT_PY")}
        self.env["PATH"] = f"{self.bin}:{self.env.get('PATH', '')}"
        self.env["SKY130_VARIANT_DIR"] = str(variant)
        self.env["KLT_PY"] = str(self.bin / "klt-python-stub")
        self.env["KLT_STUB_ENVELOPE"] = GRADED_ENVELOPE


class RunDrcGate(StubEnv):
    def run_drc(self, **rc):
        self.env.update({k: str(v) for k, v in rc.items()})
        return subprocess.run([str(RUN_DRC), str(self.root / "out")],
                              env=self.env, capture_output=True, text=True, timeout=120)

    def test_klt_exit_0_completes(self):
        r = self.run_drc()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('"status": "clean"', (self.root / "out/digital/curated.json").read_text())

    def test_violations_and_coverage_unknown_are_normal_outcomes(self):
        # The over-gating direction of the fix: 3 (violations) and 4
        # (coverage_unknown) are legitimate klt drc outcomes and must complete,
        # not abort -- the envelopes carry the verdict, the exit code is not one.
        for rc, what in ((3, "violations"), (4, "coverage_unknown")):
            with self.subTest(rc=rc, what=what):
                self.root.mkdir(exist_ok=True)
                r = self.run_drc(KLT_STUB_GRADED_RC=rc, KLT_STUB_SEAM_RC=rc)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn('"status": "clean"',
                              (self.root / "out/analog/curated-graded.json").read_text())
                times = (self.root / "out/times.txt").read_text()
                self.assertIn("klt drc layout/sram_256x32_m4.gds", times)

    def test_deck_failure_exit_aborts_with_that_code(self):
        for rc in (1, 2):
            with self.subTest(rc=rc):
                self.root.mkdir(exist_ok=True)
                r = self.run_drc(KLT_STUB_GRADED_RC=rc)
                self.assertEqual(
                    r.returncode, rc,
                    f"klt drc exit {rc} was not propagated: the run completed "
                    f"(exit 0 would mean the graded report is crash debris)")
                self.assertIn("FAILED", r.stderr)
                self.assertIn(f"exit {rc}", r.stderr)
                self.assertFalse(
                    (self.root / "out/seam/curated.json").exists(),
                    "the run continued past a failed graded deck call")

    def test_seam_control_failure_aborts(self):
        self.root.mkdir(exist_ok=True)
        r = self.run_drc(KLT_STUB_SEAM_RC=2)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("FAILED", r.stderr)


class MakeRecordValidate(unittest.TestCase):
    """make_record.py against a throwaway copy of the tree it writes into."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        repo = self.repo = self.root / "repo"
        for d in ("sim/bitcell/lib", "verification/drc/records",
                  "design/compiler/evidence", "evidence"):
            (repo / d).mkdir(parents=True)
        for f in ("record_common.py", "tb_common.py"):
            shutil.copy2(REPO / "sim/bitcell/lib" / f, repo / "sim/bitcell/lib" / f)
        shutil.copy2(MAKE_RECORD, repo / "verification/drc/make_record.py")
        self.before = {}
        for ev in ("design/compiler/evidence/item3.json", "evidence/item3-digital.json"):
            data = (REPO / ev).read_bytes()
            (repo / ev).write_bytes(data)
            self.before[ev] = data
        bin = self.root / "bin"
        bin.mkdir()
        (bin / "klt").write_text(KLT_STUB)
        (bin / "klt").chmod(0o755)
        self.env = dict(os.environ)
        self.env["PATH"] = f"{bin}:{self.env.get('PATH', '')}"
        self.out = self.root / "run"
        git = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True,
                                        capture_output=True, text=True)
        git("init", "-q")
        git("add", "-A")
        git("-c", "user.name=t", "-c", "user.email=t@example.com",
            "-c", "commit.gpgsign=false", "commit", "-q", "-m", "fixture")

    def write_outdir(self, analog=GRADED_ENVELOPE, digital=GRADED_ENVELOPE,
                     seam=SEAM_ENVELOPE):
        for d in ("analog", "digital", "seam"):
            (self.out / d).mkdir(parents=True, exist_ok=True)
        (self.out / "analog/curated-graded.json").write_text(analog)
        (self.out / "digital/curated.json").write_text(digital)
        (self.out / "seam/curated.json").write_text(seam)
        for name in ("scan-macro.json", "scan-control.json", "scan-positive-control.json"):
            (self.out / name).write_text(SCAN_JSON)
        (self.out / "times.txt").write_text("klt drc x : 1 s\n")
        (self.out / "analog/summary.txt").write_text("curated clean\n")

    def run_writer(self):
        return subprocess.run(
            [sys.executable, "-I", str(self.repo / "verification/drc/make_record.py"),
             str(self.out)],
            env=self.env, capture_output=True, text=True, timeout=120)

    def assert_evidence_untouched(self):
        for ev, data in self.before.items():
            self.assertEqual((self.repo / ev).read_bytes(), data,
                             f"{ev} was overwritten by an aborted run")
        self.assertEqual(sorted(p.name for p in
                                (self.repo / "verification/drc/records").glob("*.md")),
                         [], "an aborted run still wrote a record")

    def test_valid_run_copies_envelopes_and_writes_record(self):
        self.write_outdir()
        r = self.run_writer()
        self.assertEqual(r.returncode, 0, r.stderr)
        for src, ev in (("analog/curated-graded.json", "design/compiler/evidence/item3.json"),
                        ("digital/curated.json", "evidence/item3-digital.json")):
            self.assertEqual((self.repo / ev).read_bytes(),
                             (self.out / src).read_bytes(),
                             f"{ev} is not the unmodified envelope")
        self.assertEqual(len(list((self.repo / "verification/drc/records").glob("*.md"))), 1)

    def test_empty_graded_envelope_leaves_evidence_identical(self):
        # The exact #183 shape: a klt crash left an empty report; the writer must
        # abort with the committed evidence byte-identical, not copy then crash.
        self.write_outdir(analog="")
        r = self.run_writer()
        self.assertNotEqual(r.returncode, 0,
                            "an empty graded envelope was copied over the evidence")
        self.assertIn("curated-graded.json", r.stderr)
        self.assert_evidence_untouched()

    def test_keyless_graded_envelope_leaves_evidence_identical(self):
        self.write_outdir(digital="{}")
        r = self.run_writer()
        self.assertNotEqual(r.returncode, 0,
                            "a keyless graded envelope was copied over the evidence")
        self.assertIn("curated.json", r.stderr)
        self.assert_evidence_untouched()

    def test_malformed_seam_envelope_leaves_evidence_identical(self):
        self.write_outdir(seam="")
        r = self.run_writer()
        self.assertNotEqual(r.returncode, 0,
                            "an unparseable seam envelope was copied over the evidence")
        self.assert_evidence_untouched()


if __name__ == "__main__":
    unittest.main()
