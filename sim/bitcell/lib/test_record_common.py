#!/usr/bin/env python3
"""PDK-free tests for the write-trip ladder seam: python3 -I sim/bitcell/lib/test_record_common.py

The ladder length is a producer/consumer seam: make_tb.py emits the ladder, record_common.write_ladder
validates it, and a disagreement between the two used to be reported as a write-margin failure (a record
asserting the cell never flips) rather than as the tooling error it is. These tests hold both halves of
the fix: the length is declared once (issue #76), and a length that is not LADDER is loud.
"""
import gzip
import json
import os
import pathlib
import re
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
from make_controls_record import ref_kstar  # noqa: E402


def corner(values, corner_id="tt/1.800V/25C", vdd=1.8):
    """A `klt sim` report corner carrying `values` as the q00.. write-trip measurements."""
    return {"corner_id": corner_id, "supply_v": {"vvdd": vdd},
            "measurements": [{"name": f"q{k:02d}", "value": v} for k, v in enumerate(values)]}


def flips_at(n, kstar, vdd=1.8):
    """Ladder values for a cell that flips at levels 0..kstar and holds above (monotone)."""
    return [0.0 if k <= kstar else vdd for k in range(n)]


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


class SaveGzJsonIsByteReproducible(unittest.TestCase):
    """Issue #104: the deterministic gzip-JSON write lives in one place and is held by tests.

    `mtime=0` plus sort_keys/indent is what makes a committed record artifact reproducible from
    its input; that invariant used to be spelled out inline in four generators and asserted
    nowhere, so a change to any part of it could land in some copies and not others. These tests
    hold the shared helper: every committed fixture replays byte-identically through it (at
    GzipFile's default compression level, which is part of the format -- no compresslevel argument
    exists to silently change the evidence bytes), the payload is exactly
    `json.dumps(scrub(obj), indent=1, sort_keys=True)`, and two writes of one object agree.
    """

    def replay(self, src):
        """save_gz_json(load(src)) into a temp dir -> bytes. The temp file keeps src's basename:
        GzipFile embeds the output basename in the header, so a differently named destination
        would differ in bytes without any format change."""
        with tempfile.TemporaryDirectory() as td:
            dst = pathlib.Path(td) / src.name
            rc.save_gz_json(dst, rc.load(src))
            return dst.read_bytes()

    def test_every_committed_artifact_replays_byte_identically(self):
        """The append-only evidence contract: committed artifacts are re-derivable from their inputs."""
        artifacts = sorted((REPO / "sim/bitcell/corners").glob("**/*.json.gz"))
        self.assertTrue(artifacts, "fixture discovery found nothing; the glob pattern broke")
        for src in artifacts:
            with self.subTest(artifact=str(src.relative_to(REPO))):
                self.assertEqual(self.replay(src), src.read_bytes())

    def test_payload_is_scrubbed_sorted_indent1(self):
        """The write is exactly the former inline shape, scrub included: host-absolute artifact
        paths are rewritten, dicts are key-sorted, indent is 1."""
        obj = {"b": [1, {"z": 2, "y": 3}], "a": {"k": 4},
               "p": "/tmp/scratch/klt-sim-x/waveform.raw.json", "q": "/home/u/klt-sim-run/report.json"}
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / "o.json.gz"
            rc.save_gz_json(p, obj)
            raw = gzip.open(p).read().decode()
        self.assertEqual(raw, json.dumps(rc.scrub(obj), indent=1, sort_keys=True))
        self.assertNotIn("/tmp/scratch", raw)
        self.assertNotIn("/home/u/", raw)

    def test_two_writes_of_one_object_are_identical_bytes(self):
        """The mtime=0 guarantee held directly: no wall-clock timestamp ever reaches the header."""
        with tempfile.TemporaryDirectory() as td:
            p = pathlib.Path(td) / "o.json.gz"
            rc.save_gz_json(p, {"k": [1, 2, 3]})
            first = p.read_bytes()
            rc.save_gz_json(p, {"k": [1, 2, 3]})
            self.assertEqual(p.read_bytes(), first)


unittest.main()
