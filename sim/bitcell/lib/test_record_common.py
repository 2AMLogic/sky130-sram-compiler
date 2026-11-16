#!/usr/bin/env python3
"""PDK-free tests for the write-trip ladder seam: python3 -I sim/bitcell/lib/test_record_common.py

The ladder length is a producer/consumer seam: make_tb.py emits the ladder, record_common.write_ladder
validates it, and a disagreement between the two used to be reported as a write-margin failure (a record
asserting the cell never flips) rather than as the tooling error it is. These tests hold both halves of
the fix: the length is declared once (issue #76), and a length that is not LADDER is loud.
"""
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))  # -I drops the script dir
import make_tb  # noqa: E402
import record_common as rc  # noqa: E402
import tb_common  # noqa: E402

# make_controls_record -> make_record -> snm_from_artifacts loads the pinned gf180-sram SNM extractor
# (sim/build/pinned/, fetched by fetch_pinned.sh), which has nothing to do with the write-trip ladder and
# is not available in a PDK-free checkout. An attribute-less stub keeps this suite PDK-free and still fails
# loudly if anything under test ever actually reaches for the extractor.
sys.modules.setdefault("snm_from_artifacts", types.ModuleType("snm_from_artifacts"))
import make_controls_record  # noqa: E402
import make_record  # noqa: E402
import make_write_mc_record  # noqa: E402

ref_kstar = make_controls_record.ref_kstar


def corner(values, corner_id="tt/1.800V/25C", vdd=1.8):
    """A `klt sim` report corner carrying `values` as the q00.. write-trip measurements."""
    return {"corner_id": corner_id, "supply_v": {"vvdd": vdd},
            "measurements": [{"name": f"q{k:02d}", "value": v} for k, v in enumerate(values)]}


def flips_at(n, kstar, vdd=1.8):
    """Ladder values for a cell that flips at levels 0..kstar and holds above (monotone)."""
    return [0.0 if k <= kstar else vdd for k in range(n)]


def mc_sample(n, proc, vdd, temp, kstar, i):
    """One Monte Carlo sample of a (process, VDD, T) point: a corner with a unique corner_id."""
    c = corner(flips_at(n, kstar, vdd), f"{proc}/{vdd:.3f}V/{temp}C#{i}", vdd)
    c["process"] = proc
    c["temperature_c"] = temp
    return c


def mc_report(corners):
    """A minimal write-trip report carrying the fields the record generators read."""
    return {"corners": corners, "environment": {"monte_carlo": {"n": len(corners)}}}


class DeclaredOnce(unittest.TestCase):
    """Issue #76: one declaration, so the emitter and the validator cannot drift apart."""

    def test_all_sides_share_one_object(self):
        self.assertIs(rc.LADDER, tb_common.LADDER)
        self.assertIs(make_tb.LADDER, tb_common.LADDER)

    def test_only_tb_common_assigns_ladder(self):
        assign = re.compile(r"^LADDER\s*=", re.M)
        self.assertTrue(assign.search((HERE / "tb_common.py").read_text()),
                        "tb_common.py must be the one place LADDER is assigned")
        for name in ("make_tb.py", "record_common.py", "make_record.py",
                     "make_write_mc_record.py", "make_controls_record.py"):
            with self.subTest(module=name):
                self.assertIsNone(assign.search((HERE / name).read_text()),
                                  f"{name} re-declares LADDER; it must import it")

    def test_committed_request_matches_the_declared_length(self):
        """The one gate CI runs over the benches (make_tb.py --check) now sees the same length as the records."""
        req = json.loads((REPO / "sim/bitcell/requests/write_trip_corners.request.json").read_text())
        names = sorted(m["name"] for m in req["measurements"])
        self.assertEqual(names, [f"q{k:02d}" for k in range(tb_common.LADDER)])
        self.assertEqual(req["analysis"]["args"], f"0.02n {tb_common.LADDER * make_tb.TRIAL_NS:g}n")


class WrongLengthIsLoud(unittest.TestCase):
    """A ladder of the wrong length is a tooling error, never a margin result."""

    def test_wrong_length_is_not_the_unit_failure_signal(self):
        """The defect this closes: a wrong length returned the same None that means "this unit failed",
        so a tooling mismatch was published as a write-margin failure (a record asserting no flip)."""
        n = rc.LADDER + 8
        try:
            got = rc.write_ladder(corner(flips_at(n, 10)))
        except ValueError:
            return  # distinguished from a unit failure
        self.fail(f"a {n}-level ladder returned {got!r}, the same signal a failed unit returns")

    def test_too_many_levels_raises(self):
        with self.assertRaises(rc.LadderLengthError) as cm:
            rc.write_ladder(corner(flips_at(rc.LADDER + 8, 10)))
        msg = str(cm.exception)
        self.assertIn(str(rc.LADDER + 8), msg)
        self.assertIn(f"LADDER={rc.LADDER}", msg)
        self.assertIn("not a write-margin failure", msg)

    def test_too_few_levels_raises(self):
        with self.assertRaises(rc.LadderLengthError):
            rc.write_ladder(corner(flips_at(rc.LADDER - 1, 10)))

    def test_is_a_value_error(self):
        """Subclassing ValueError keeps it an ordinary data error for anything catching broadly."""
        self.assertTrue(issubclass(rc.LadderLengthError, ValueError))


class MissingMeasurementIsAUnitFailure(unittest.TestCase):
    """The `None` contract the record generators rely on is unchanged: it means this unit failed."""

    def test_none_value_at_full_length_returns_none(self):
        q = flips_at(rc.LADDER, 10)
        q[17] = None
        self.assertIsNone(rc.write_ladder(corner(q)))

    def test_all_values_missing_returns_none(self):
        self.assertIsNone(rc.write_ladder(corner([None] * rc.LADDER)))


class ValidLadder(unittest.TestCase):
    def test_kstar_and_monotone(self):
        self.assertEqual(rc.write_ladder(corner(flips_at(rc.LADDER, 10))), (10, True, rc.LADDER))

    def test_no_flip_at_level_zero(self):
        self.assertEqual(rc.write_ladder(corner(flips_at(rc.LADDER, -1))), (-1, True, rc.LADDER))

    def test_non_monotone_is_reported_not_rejected(self):
        q = flips_at(rc.LADDER, 10)
        q[20] = 0.0  # flips again above the leading run
        self.assertEqual(rc.write_ladder(corner(q)), (10, False, rc.LADDER))

    def test_measurements_are_read_in_name_order_not_report_order(self):
        c = corner(flips_at(rc.LADDER, 10))
        c["measurements"].reverse()
        self.assertEqual(rc.write_ladder(c), (10, True, rc.LADDER))


class DeterminismReference(unittest.TestCase):
    """make_controls_record.ref_kstar subscripted write_ladder() unguarded; it now says what is wrong."""

    def test_complete_reference(self):
        ref = {"corners": [corner(flips_at(rc.LADDER, 10), "tt/1.800V/25C"),
                           corner(flips_at(rc.LADDER, 7), "ss/1.620V/125C")]}
        self.assertEqual(ref_kstar(ref), {"tt/1.800V/25C": 10, "ss/1.620V/125C": 7})

    def test_missing_measurement_is_named(self):
        q = flips_at(rc.LADDER, 10)
        q[3] = None
        with self.assertRaises(ValueError) as cm:
            ref_kstar({"corners": [corner(q, "ss/1.620V/125C")]})
        self.assertIn("ss/1.620V/125C", str(cm.exception))
        self.assertNotIsInstance(cm.exception, TypeError)

    def test_wrong_length_is_named(self):
        with self.assertRaises(rc.LadderLengthError):
            ref_kstar({"corners": [corner(flips_at(rc.LADDER + 1, 10), "ss/1.620V/125C")]})


class RecordProseTracksLadder(unittest.TestCase):
    """Issue #91: a record's stated ladder methodology must track tb_common.LADDER, not a hardcoded 33.

    The stub-and-regenerate shape is the manipulation that found the defect: stub LADDER to a length
    with no digit overlap against the old literals (41 -> step /40), regenerate each record from a
    small fixture, and assert both directions -- the derived step appears, the old spellings do not.
    """

    STUB = 41

    def setUp(self):
        # LADDER is imported by value, so the stub must land on every module that reads it:
        # write_ladder validates through record_common's binding, the prose through the generators'.
        # create=True: pre-fix, make_record does not import LADDER at all -- part of the defect.
        for m in (tb_common, rc, make_write_mc_record, make_record, make_controls_record):
            p = mock.patch.object(m, "LADDER", self.STUB, create=True)
            p.start()
            self.addCleanup(p.stop)

    def step_mv(self, vdd):
        return f"{vdd / (self.STUB - 1) * 1000:.0f}"

    def regenerate_write_mc_record(self, n):
        corners = [mc_sample(n, "fs_mm", 1.62, -40, k, i) for i, k in enumerate((10, 12, 14))]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            rep = tmp / "mc_write_trip.report.json"
            rep.write_text(json.dumps(mc_report(corners)))
            out = tmp / "record.md"
            argv = ["make_write_mc_record.py", "--id", "prose-pin", "--out", str(out),
                    "--evidence", str(tmp / "ev"), "--report", str(rep)]
            with mock.patch.object(sys, "argv", argv):
                make_write_mc_record.main()
            return out.read_text()

    def test_write_mc_record_prose_reports_the_stubbed_step(self):
        text = self.regenerate_write_mc_record(self.STUB)
        self.assertIn(f"step VDD/{self.STUB - 1} = {self.step_mv(1.62)} mV at 1.62 V, "
                      f"{self.step_mv(1.98)} mV at 1.98 V", text)
        self.assertIn(f"[VDD*k*/{self.STUB - 1}, VDD*(k*+1)/{self.STUB - 1})", text)
        for old in ("/32", "33-level", "51 mV", "62 mV", "56 mV"):
            with self.subTest(literal=old):
                self.assertNotIn(old, text)

    def test_digit_overlap_stub_is_distinguished_from_the_old_literals(self):
        """Issue edge case: stub 34 makes the derived denominator 33, digits overlapping the old
        literals. The pin is the specific old spellings, not bare digits, so the derived /33 is
        asserted present while '33-level' and '/32' are still asserted absent."""
        for m in (tb_common, rc, make_write_mc_record, make_record, make_controls_record):
            p = mock.patch.object(m, "LADDER", 34, create=True)
            p.start()
            self.addCleanup(p.stop)
        text = self.regenerate_write_mc_record(34)
        self.assertIn("[VDD*k*/33, VDD*(k*+1)/33)", text)
        for old in ("/32", "33-level", "51 mV", "62 mV", "56 mV"):
            with self.subTest(literal=old):
                self.assertNotIn(old, text)

    def regenerate_margin_record(self):
        def snm_for(path, pair):
            return ((0.1, 0.2), (0.3, 0.4))

        p = mock.patch.object(sys.modules["snm_from_artifacts"], "snm_for", snm_for, create=True)
        p.start()
        self.addCleanup(p.stop)
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            files = {}
            for nm in ("read", "hold"):
                files[nm] = tmp / f"{nm}.json"
                files[nm].write_text(json.dumps({"corners": [{"corner_id": "tt/1.800V/25C"}],
                                                 "environment": {}}))
            files["write"] = tmp / "write.json"
            files["write"].write_text(json.dumps(mc_report([corner(flips_at(self.STUB, 10))])))
            out = tmp / "record.md"
            argv = ["make_record.py", "--id", "prose-pin", "--out", str(out),
                    "--evidence", str(tmp / "ev"),
                    "--read", str(files["read"]), str(tmp / "art-read"),
                    "--hold", str(files["hold"]), str(tmp / "art-hold"),
                    "--write", str(files["write"])]
            with mock.patch.object(sys, "argv", argv):
                make_record.main()
            return out.read_text()

    def test_margin_record_prose_reports_the_stubbed_step(self):
        text = self.regenerate_margin_record()
        self.assertIn(f"ladder step VDD/{self.STUB - 1}, so the true trip lies in the next "
                      f"{self.step_mv(1.8)} mV-class step above", text)
        self.assertIn(f"(resolution VDD/{self.STUB - 1})", text)
        for old in ("/32", "33-level", "51 mV", "62 mV", "56 mV"):
            with self.subTest(literal=old):
                self.assertNotIn(old, text)

    def regenerate_controls_record(self):
        # The `klt yield` step is stubbed into its error branch: the note quoting the failure is the
        # one place this generator names the no-flip ladder step. Issue #103's provenance lookups at
        # the top of main() go through the same stub as successes, so the suite stays hermetic (no
        # real klt on PATH, no real git needed) and still runs from a git-archive scratch checkout.
        fake = subprocess.CompletedProcess([], 1, stdout="", stderr="klt yield: stub failure")

        def run_stub(cmd, *args, **kwargs):
            if cmd[:2] == ["klt", "yield"]:
                return fake
            return subprocess.CompletedProcess([], 0, stdout="stub", stderr="")

        with mock.patch.object(subprocess, "run", side_effect=run_stub):
            with tempfile.TemporaryDirectory() as tmp:
                tmp = pathlib.Path(tmp)
                base = mc_report([mc_sample(self.STUB, "fs_mm", 1.62, -40, k, i)
                                  for i, k in enumerate((10, 12, 14))])
                det_ref = mc_report([corner(flips_at(self.STUB, 10), "fs/1.620V/-40C")])
                det = mc_report([mc_sample(self.STUB, "fs_mm", 1.62, -40, 10, i) for i in range(3)])
                neg = mc_report([mc_sample(self.STUB, "fs_mm", 1.62, -40, 5, i) for i in range(3)])
                files = {}
                for nm, rep in (("base", base), ("detref", det_ref), ("det", det), ("neg", neg)):
                    files[nm] = tmp / f"{nm}.json"
                    files[nm].write_text(json.dumps(rep))
                files["basemd"] = tmp / "base.md"
                files["basemd"].write_text("## stub\n")
                out = tmp / "record.md"
                argv = ["make_controls_record.py", "--id", "prose-pin", "--out", str(out),
                        "--evidence", str(tmp / "ev"), "--base-record", str(files["basemd"]),
                        "--base-reports", str(files["base"]), "--det-ref", str(files["detref"]),
                        "--det", str(files["det"]), "--neg", str(files["neg"])]
                with mock.patch.object(sys, "argv", argv):
                    make_controls_record.main()
                return out.read_text()

    def test_controls_record_prose_reports_the_stubbed_step(self):
        text = self.regenerate_controls_record()
        self.assertIn(f"a no-flip sample would enter as -VDD/{self.STUB - 1}", text)
        for old in ("/32", "33-level", "51 mV", "62 mV", "56 mV"):
            with self.subTest(literal=old):
                self.assertNotIn(old, text)

    def test_generator_sources_carry_no_ladder_literal(self):
        """The docstrings describe the bench, so they must name the declaration like make_tb.py's do;
        stub-and-regenerate covers the emitted prose, this covers the text beside it."""
        literals = ("/32", "33-level", "33-trial", "51 mV", "62 mV")
        for name in ("make_record.py", "make_write_mc_record.py", "make_controls_record.py",
                     "../README.md"):
            src = (HERE / name).resolve().read_text()
            for lit in literals:
                with self.subTest(module=name, literal=lit):
                    self.assertNotIn(lit, src)


class ProvenanceLookupsRefuse(unittest.TestCase):
    """git_short_sha / klt_version_local refuse instead of degrading (issue #103).

    A failed lookup returned "" (git) or a stderr diagnostic recorded as a "version" (klt), and both
    landed in append-only records that cannot be corrected in place. Every failure mode -- non-zero
    rc, rc 0 with empty stdout, binary missing from PATH -- must raise the one named ProvenanceError
    carrying the command, never a bare Exception or a blank field.
    """

    def stub_path(self, *scripts):
        """A temp dir on PATH holding stub executables: each script is a (name, body) pair."""
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        for name, body in scripts:
            p = pathlib.Path(d.name) / name
            p.write_text(body)
            p.chmod(0o755)
        return d.name

    def assert_refuses(self, fn, *args):
        """The helper raises the named error (not a bare Exception) for the failure under test."""
        with self.assertRaises(rc.ProvenanceError):
            fn(*args)

    def test_git_nonzero_rc_raises_named_error(self):
        """A real failing git: GIT_DIR pointing nowhere gives rc 128, empty stdout, a diagnostic on stderr."""
        with mock.patch.dict(os.environ, {"GIT_DIR": "/nonexistent"}):
            self.assert_refuses(rc.git_short_sha, REPO)

    def test_klt_nonzero_rc_raises_named_error(self):
        """The '- klt: ;' shape: a klt that runs and exits non-zero with its diagnostic on stderr."""
        path = self.stub_path(("klt", "#!/bin/sh\necho 'stub: broken klt' >&2\nexit 129\n"))
        with mock.patch.dict(os.environ, {"PATH": path}):
            self.assert_refuses(rc.klt_version_local)

    def test_rc0_empty_stdout_raises_for_both(self):
        """An exit-0 lookup with nothing on stdout is half the defect; it must refuse too."""
        path = self.stub_path(("git", "#!/bin/sh\nexit 0\n"), ("klt", "#!/bin/sh\nexit 0\n"))
        with mock.patch.dict(os.environ, {"PATH": path}):
            for fn, args in ((rc.git_short_sha, (REPO,)), (rc.klt_version_local, ())):
                with self.subTest(helper=fn.__name__):
                    self.assert_refuses(fn, *args)

    def test_missing_binary_raises_for_both(self):
        """An absent binary must be the one named error, not a FileNotFoundError traceback by accident."""
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        with mock.patch.dict(os.environ, {"PATH": empty.name}):
            for fn, args in ((rc.git_short_sha, (REPO,)), (rc.klt_version_local, ())):
                with self.subTest(helper=fn.__name__):
                    self.assert_refuses(fn, *args)

    def test_error_carries_command_and_stderr_tail(self):
        path = self.stub_path(("klt", "#!/bin/sh\necho 'stub: diagnostic tail' >&2\nexit 3\n"))
        with mock.patch.dict(os.environ, {"PATH": path}):
            with self.assertRaises(rc.ProvenanceError) as cm:
                rc.klt_version_local()
        msg = str(cm.exception)
        self.assertIn("klt --version", msg)
        self.assertIn("stub: diagnostic tail", msg)
        self.assertIn("rc 3", msg)

    def test_success_paths_still_return_values(self):
        """The guard changes failures only: a working lookup returns what it always returned."""
        path = self.stub_path(("klt", "#!/bin/sh\necho 'klt 1.2.3'\n"))
        with mock.patch.dict(os.environ, {"PATH": path}):
            self.assertEqual(rc.klt_version_local(), "klt 1.2.3")
        sha = rc.git_short_sha(REPO)
        self.assertTrue(re.fullmatch(r"[0-9a-f]{7,}", sha),
                        f"the real repo sha should resolve, got {sha!r}")


unittest.main()
