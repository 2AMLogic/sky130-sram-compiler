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
# loudly if anything under test ever actually reaches for the extractor -- except for the file access
# itself: snm_for keeps the real function's open/json.load so a missing or unparseable waveform.raw.json
# raises exactly what the real writer would (issue #174).
_stub_sfa = types.ModuleType("snm_from_artifacts")


def _stub_snm_for(path, pair):
    json.load(open(path))
    raise RuntimeError("stub snm_from_artifacts.snm_for: pinned extractor not under test")


_stub_sfa.snm_for = _stub_snm_for
sys.modules.setdefault("snm_from_artifacts", _stub_sfa)
sys.path.insert(0, str(HERE.parents[1] / "column/lib"))  # make_column_record's own directory
import make_column_record  # noqa: E402
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
        self.assertTrue(re.fullmatch(r"[0-9a-f]{7,}(-dirty)?", sha),
                        f"the real repo sha should resolve, got {sha!r}")


class DirtyTreeIsStamped(unittest.TestCase):
    """git_short_sha stamps a dirty tree `<sha>-dirty` instead of a commit that cannot reproduce the record (issue #151).

    A record generated from uncommitted code used to name plain HEAD -- a commit that does not
    contain the code that produced it -- and records are append-only, so the mis-attribution was
    permanent once merged (PR #139's `88af0fd` record is the concrete instance). Decision 0002:
    stamp the dirtiness visibly rather than refuse, so the fix+evidence-in-one-PR workflow keeps
    working and an un-reproducible stamp is honest about what it names.
    """

    def scratch_repo(self):
        """A throwaway git repo with one committed source file; returns its path."""
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        repo = pathlib.Path(d.name)
        git = ["git", "-C", str(repo)]
        subprocess.run(git + ["init", "-q"], check=True)
        (repo / "src").mkdir()
        (repo / "src" / "cell.py").write_text("a = 1\n")
        subprocess.run(git + ["add", "src"], check=True)
        subprocess.run(git + ["-c", "user.email=t@t", "-c", "user.name=t",
                              "commit", "-qm", "init"], check=True)
        return repo

    def rev_sha(self, repo):
        """HEAD's short sha, read directly rather than through the helper under test."""
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()

    def test_clean_tree_returns_bare_sha(self):
        repo = self.scratch_repo()
        self.assertEqual(rc.git_short_sha(repo), self.rev_sha(repo))

    def test_modified_tracked_file_stamps_dirty(self):
        """The defect this closes: an edit to a tracked source file changes the code HEAD names."""
        repo = self.scratch_repo()
        (repo / "src" / "cell.py").write_text("a = 2\n")
        self.assertEqual(rc.git_short_sha(repo), f"{self.rev_sha(repo)}-dirty")

    def test_untracked_source_file_stamps_dirty(self):
        """A new untracked source file is a real reproducibility gap; only gitignored scratch is exempt."""
        repo = self.scratch_repo()
        (repo / "src" / "new_cell.py").write_text("b = 1\n")
        self.assertEqual(rc.git_short_sha(repo), f"{self.rev_sha(repo)}-dirty")

    def test_user_config_cannot_silence_untracked_dirty(self):
        """status.showUntrackedFiles=no in ambient git config must not switch the untracked half of the check off (issue #186).

        The status probe inherited the ambient config's untracked-files default, so a user- or
        system-level `showUntrackedFiles = no` suppressed exactly the new-source-file half of the
        dirty decision and stamped a bare sha for a tree HEAD cannot reproduce -- the silent-clean
        direction the record stamps exist to make impossible. The helper passes
        --untracked-files=normal itself; the test proves the hostile config is live (a bare
        `git status --porcelain` under the same env lists nothing) and that the helper still
        stamps dirty. GIT_CONFIG_SYSTEM is pointed at /dev/null so the host's system config
        cannot mask the result either way.
        """
        repo = self.scratch_repo()
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        hostile = pathlib.Path(d.name) / "gitconfig"
        hostile.write_text("[status]\n\tshowUntrackedFiles = no\n")
        saved = {k: os.environ.get(k) for k in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM")}

        def restore_env():
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.addCleanup(restore_env)
        os.environ["GIT_CONFIG_GLOBAL"] = str(hostile)
        os.environ["GIT_CONFIG_SYSTEM"] = os.devnull
        (repo / "src" / "new_cell.py").write_text("b = 1\n")
        bare = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                              capture_output=True, text=True, check=True).stdout
        self.assertEqual(bare, "", "hostile config is not live: untracked files are listed anyway")
        self.assertEqual(rc.git_short_sha(repo), f"{self.rev_sha(repo)}-dirty")

    def test_gitignored_scratch_output_is_not_dirty(self):
        repo = self.scratch_repo()
        (repo / ".gitignore").write_text("out/\n")
        subprocess.run(["git", "-C", str(repo), "add", ".gitignore"], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
                        "commit", "-qm", "ignore scratch"], check=True)
        (repo / "out").mkdir()
        (repo / "out" / "waveform.raw").write_text("simulator noise\n")
        self.assertEqual(rc.git_short_sha(repo), self.rev_sha(repo))

    def test_uncommitted_record_does_not_stamp_dirty(self):
        """An earlier uncommitted record in the same PR must not mark the next one dirty."""
        repo = self.scratch_repo()
        (repo / "records").mkdir()
        (repo / "records" / "draft.md").write_text("evidence written after the last commit\n")
        self.assertEqual(rc.git_short_sha(repo), self.rev_sha(repo))

    def test_failing_status_refuses_rather_than_reads_clean(self):
        """A git whose `status` fails must raise, never degrade to a clean stamp (same refusal class as #103).

        `_checked_output` cannot probe the dirty/clean split itself -- empty stdout IS the clean
        case -- so the status lookup needs its own rc check; this stub returns a valid sha but
        fails on `status`, the shape that would silently degrade to clean if the rc were dropped.
        """
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        g = pathlib.Path(d.name) / "git"
        g.write_text("#!/bin/sh\n"
                     "for a in \"$@\"; do [ \"$a\" = status ] && "
                     "{ echo 'stub: broken status' >&2; exit 128; }; done\n"
                     "echo deadbee\n")
        g.chmod(0o755)
        with mock.patch.dict(os.environ, {"PATH": d.name}):
            with self.assertRaises(rc.ProvenanceError) as cm:
                rc.git_short_sha(REPO)
        msg = str(cm.exception)
        self.assertIn("status", msg)
        self.assertIn("rc 128", msg)
        self.assertIn("stub: broken status", msg)


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


class RefusesBeforeWritingEvidence(unittest.TestCase):
    """Issue #129: every report a record needs is read before any evidence artifact is written.

    Three of the four writers used to interleave their report reads with their gzip writes, so a
    missing or unparseable report for bench N left the gzips for benches 0..N-1 on disk in the
    evidence directory the published record cites -- indistinguishable from a completed run until
    someone counts the files. The refusal must land zero .json.gz files; the pre-change
    interleaved shape leaves N-1 (the distinguishing measurement this class holds).

    Issue #172 extends the same refusal to the inputs that are not argv paths: the repo-tracked
    constants each writer still read after its gzip writes (design/bitcell/sizing.json in the two
    bitcell writers, the sim/column/requests/<bench>.request.json shas in the column writer).

    Issue #174 extends it once more to the per-corner waveform.raw.json artifacts the column
    writer reads through snm_rows after its eleven report gzips have landed.

    Issue #176 extends it to the read benches' waveform.raw.json (read_rows): present but
    unparseable refuses; absent stays a supported input (tsa=None), the wf.exists() guard.
    """

    def stub_provenance(self):
        """Hermetic provenance lookups (same shape as regenerate_controls_record): main()'s
        git/klt calls answer rc 0 with non-empty stdout so a refusal test fails on the report
        read it is about, never on a missing binary or a git-archive checkout."""
        fake = subprocess.CompletedProcess([], 0, stdout="stub", stderr="")
        p = mock.patch.object(subprocess, "run", return_value=fake)
        p.start()
        self.addCleanup(p.stop)

    def assert_refused(self, main_fn, argv, ev, exc):
        """main() refuses with `exc` and leaves zero .json.gz in the evidence directory."""
        self.stub_provenance()
        ev = pathlib.Path(ev)
        with mock.patch.object(sys, "argv", argv):
            with self.assertRaises(exc):
                main_fn()
        left = sorted(p.name for p in ev.glob("*.json.gz")) if ev.exists() else []
        self.assertEqual(left, [], f"refusal left evidence behind: {left}")

    @staticmethod
    def make_record_argv(tmp, mc_body):
        """Full make_record.py argv with an `--mc-report-read` file holding `mc_body`
        ('{' = truncated); the read/hold/write reports are minimal but parseable."""
        tmp = pathlib.Path(tmp)
        for nm in ("read", "hold"):
            (tmp / f"{nm}.json").write_text('{"corners": [], "environment": {}}')
        (tmp / "write.json").write_text('{"corners": [], "environment": {}}')
        if mc_body is not None:
            (tmp / "mc-read.json").write_text(mc_body)
        return ["make_record.py", "--id", "refuse", "--out", str(tmp / "record.md"),
                "--evidence", str(tmp / "ev"),
                "--read", str(tmp / "read.json"), str(tmp / "a-read"),
                "--hold", str(tmp / "hold.json"), str(tmp / "a-hold"),
                "--write", str(tmp / "write.json"),
                "--mc-report-read", str(tmp / "mc-read.json")], tmp / "ev"

    def test_make_record_missing_mc_report_writes_nothing(self):
        """The orphan window: three primary gzips used to land before the MC reports were read."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.make_record_argv(td, None)
            self.assert_refused(make_record.main, argv, ev, FileNotFoundError)

    def test_make_record_unparseable_mc_report_writes_nothing(self):
        """The other reachable shape: the MC report exists but is truncated JSON."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.make_record_argv(td, "{")
            self.assert_refused(make_record.main, argv, ev, json.JSONDecodeError)

    def controls_argv(self, tmp, base_body):
        """make_controls_record.py argv whose `--base-reports` file holds `base_body`
        (None = absent). det/neg/det-ref exist; --neg-read/--neg-hold are omitted."""
        tmp = pathlib.Path(tmp)
        for nm in ("det", "neg"):
            (tmp / f"{nm}.json").write_text('{"corners": [], "environment": {}}')
        (tmp / "detref.json").write_text('{"corners": [], "environment": {}}')
        (tmp / "base.md").write_text("## stub\n")
        if base_body is not None:
            (tmp / "base.json").write_text(base_body)
        return ["make_controls_record.py", "--id", "refuse", "--out", str(tmp / "record.md"),
                "--evidence", str(tmp / "ev"), "--base-record", str(tmp / "base.md"),
                "--base-reports", str(tmp / "base.json"),
                "--det-ref", str(tmp / "detref.json"),
                "--det", str(tmp / "det.json"), "--neg", str(tmp / "neg.json")], tmp / "ev"

    def test_controls_missing_base_report_writes_nothing(self):
        """--base-reports is read after every keep() pre-change: the det/neg gzips orphan."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.controls_argv(td, None)
            self.assert_refused(make_controls_record.main, argv, ev, FileNotFoundError)

    def test_controls_unparseable_det_ref_writes_nothing(self):
        """A truncated --det-ref (read last pre-change) must refuse with all gzips unwritten."""
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            argv, ev = self.controls_argv(td, '{"corners": [], "environment": {}}')
            (pathlib.Path(td) / "detref.json").write_text("{")
            self.assert_refused(make_controls_record.main, argv, ev, json.JSONDecodeError)

    def test_controls_missing_base_record_writes_nothing(self):
        """--base-record was still read after the mkdir until #168: the det/neg gzips orphan."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.controls_argv(td, '{"corners": [], "environment": {}}')
            (pathlib.Path(td) / "base.md").unlink()
            self.assert_refused(make_controls_record.main, argv, ev, FileNotFoundError)

    def test_controls_missing_job_log_writes_nothing(self):
        """A --job-log stderr file that does not exist must refuse before the mkdir (#168)."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.controls_argv(td, '{"corners": [], "environment": {}}')
            argv += ["--job-log", f"det={pathlib.Path(td) / 'det.log'}"]
            self.assert_refused(make_controls_record.main, argv, ev, FileNotFoundError)

    def test_controls_job_log_missing_last_file_writes_nothing(self):
        """Several --job-log files with only the last one missing: the earlier ones are read
        but no gzip may land (all reads complete before the mkdir)."""
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            argv, ev = self.controls_argv(td, '{"corners": [], "environment": {}}')
            for nm in ("det", "neg"):
                (tmp / f"{nm}.log").write_text("batch job klt-sim-deadbeef submitting\n")
            argv += ["--job-log", f"det={tmp / 'det.log'}", f"neg={tmp / 'neg.log'}",
                     f"neg-read={tmp / 'missing.log'}"]
            self.assert_refused(make_controls_record.main, argv, ev, FileNotFoundError)

    @staticmethod
    def column_argv(tmp, missing_or_body):
        """make_column_record.py argv over a scratch holding all 11 benches except that
        `col_write0.json` (bench 3 of 11) holds `missing_or_body` (None = absent, str = content)."""
        tmp = pathlib.Path(tmp)
        scratch = tmp / "scratch"
        scratch.mkdir()
        for b in ["col_read0", "col_read1", "col_write0", "col_write1", "col_write0_nowen",
                  "col_read_snm", "col_hold_snm", "col_mc_read_snm", "col_mc_hold_snm",
                  "col_mc_read_snm_neg", "col_mc_hold_snm_neg"]:
            body = missing_or_body if b == "col_write0" else '{"corners": [], "environment": {}}'
            if body is not None:
                (scratch / f"{b}.json").write_text(body)
        return ["make_column_record.py", "--id", "refuse", "--out", str(tmp / "record.md"),
                "--evidence", str(tmp / "ev"), "--scratch", str(scratch)], tmp / "ev"

    def test_column_missing_bench_writes_nothing(self):
        """The README's manual invocation against a scratch missing bench 3: pre-change leaves
        col_read0/col_read1 gzips behind."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.column_argv(td, None)
            self.assert_refused(make_column_record.main, argv, ev, FileNotFoundError)

    def test_column_unparseable_bench_writes_nothing(self):
        """A truncated bench report (present but malformed) refuses the same way."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.column_argv(td, "{")
            self.assert_refused(make_column_record.main, argv, ev, json.JSONDecodeError)

    @staticmethod
    def column_snm_argv(tmp, wf_body):
        """make_column_record.py argv over a complete scratch (all 11 bench reports present)
        whose `col_read_snm` report carries one corner, with the corner's `waveform.raw.json`
        artifact holding `wf_body` (None = absent, str = content). Every other bench is an
        empty-corner report, so the only reachable refusal is the SNM waveform read."""
        tmp = pathlib.Path(tmp)
        scratch = tmp / "scratch"
        scratch.mkdir()
        corner = ('{"corner_id": "tt/1.800V/25C", "process": "tt", "supply_v": {"vvdd": 1.8},'
                  ' "temperature_c": 25, "measurements": []}')
        for b in ["col_read0", "col_read1", "col_write0", "col_write1", "col_write0_nowen",
                  "col_read_snm", "col_hold_snm", "col_mc_read_snm", "col_mc_hold_snm",
                  "col_mc_read_snm_neg", "col_mc_hold_snm_neg"]:
            body = f'{{"corners": [{corner}], "environment": {{}}}}' if b == "col_read_snm" \
                else '{"corners": [], "environment": {}}'
            (scratch / f"{b}.json").write_text(body)
        d = scratch / "col_read_snm" / rc.dirname("tt/1.800V/25C")
        d.mkdir(parents=True)
        if wf_body is not None:
            (d / "waveform.raw.json").write_text(wf_body)
        return ["make_column_record.py", "--id", "refuse", "--out", str(tmp / "record.md"),
                "--evidence", str(tmp / "ev"), "--scratch", str(scratch)], tmp / "ev"

    def test_column_missing_snm_waveform_writes_nothing(self):
        """A missing SNM-corner waveform.raw.json is an input too: pre-#174 it raised after
        all eleven report gzips had landed (the distinguishing measurement: 11 left)."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.column_snm_argv(td, None)
            self.assert_refused(make_column_record.main, argv, ev, FileNotFoundError)

    def test_column_unparseable_snm_waveform_writes_nothing(self):
        """A truncated waveform artifact (present but malformed) refuses the same way."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.column_snm_argv(td, "{")
            self.assert_refused(make_column_record.main, argv, ev, json.JSONDecodeError)

    @staticmethod
    def column_read1_argv(tmp, wf_body):
        """make_column_record.py argv over a complete scratch (all 11 bench reports present)
        whose `col_read1` report carries one corner with a full passing read-1 measurement set
        over `gen.READ_D` (so `ladder_min(ok)` is 0 and `read_rows` reaches the corner's
        `waveform.raw.json` artifact, holding `wf_body`: None = absent, str = content). Every
        other bench is an empty-corner report, so the only reachable refusal on the read benches
        is this waveform read (`col_read0` cannot reach it: the `want == 1` guard)."""
        tmp = pathlib.Path(tmp)
        scratch = tmp / "scratch"
        scratch.mkdir()
        vdd, n = 1.8, len(make_column_record.gen.READ_D)
        ms = [{"name": f"dout{k:02d}", "value": 1.0} for k in range(n)]
        ms += [{"name": f"q{k:02d}", "value": 1.0} for k in range(n)]
        ms += [{"name": f"dv{k:02d}", "value": 0.1} for k in range(n)]
        ms += [{"name": nm, "value": v} for nm, v in (("bump", 0.0), ("hs1", vdd), ("hs2", vdd))]
        corner = ('{"corner_id": "tt/1.800V/25C", "process": "tt", "supply_v": {"vvdd": 1.8},'
                  f' "temperature_c": 25, "measurements": {json.dumps(ms)}}}')
        for b in ["col_read0", "col_read1", "col_write0", "col_write1", "col_write0_nowen",
                  "col_read_snm", "col_hold_snm", "col_mc_read_snm", "col_mc_hold_snm",
                  "col_mc_read_snm_neg", "col_mc_hold_snm_neg"]:
            body = f'{{"corners": [{corner}], "environment": {{}}}}' if b == "col_read1" \
                else '{"corners": [], "environment": {}}'
            (scratch / f"{b}.json").write_text(body)
        d = scratch / "col_read1" / rc.dirname("tt/1.800V/25C")
        d.mkdir(parents=True)
        if wf_body is not None:
            (d / "waveform.raw.json").write_text(wf_body)
        return ["make_column_record.py", "--id", "refuse", "--out", str(tmp / "record.md"),
                "--evidence", str(tmp / "ev"), "--scratch", str(scratch)], tmp / "ev"

    def test_column_unparseable_read1_waveform_writes_nothing(self):
        """A truncated read-1 waveform artifact (present but malformed) is an input too (#176):
        the read_rows hoist makes it refuse before any of the eleven report gzips land."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.column_read1_argv(td, "{")
            self.assert_refused(make_column_record.main, argv, ev, json.JSONDecodeError)

    def test_column_read1_absent_waveform_yields_tsa_none(self):
        """The positive counterpart the wf.exists() guard exists for (#176): a read-1 corner
        with NO waveform artifact is a supported input, not a refusal -- the row lands with
        tsa=None and the rest of the measurement set intact."""
        with tempfile.TemporaryDirectory() as td:
            argv, _ = self.column_read1_argv(td, None)
            scratch = pathlib.Path(argv[argv.index("--scratch") + 1])
            rep, rows = make_column_record.read_rows(scratch, "col_read1")
            (cid, x), = rows
            self.assertEqual(cid, "tt/1.800V/25C")
            self.assertEqual(x["dmin"], make_column_record.gen.READ_D[0])
            self.assertIsNone(x["tsa"])
            self.assertFalse(x["low_fail"])
            self.assertTrue(x["all_state_ok"])
            self.assertEqual(x["dv"], 0.1)
            self.assertEqual(x["bump"], 0.0)
            self.assertEqual(x["hs"], (1.8, 1.8))
            self.assertEqual(x["vdd"], 1.8)

    @staticmethod
    def sizing_repo(tmp, body):
        """A stub repo whose tracked `design/bitcell/sizing.json` holds `body` ('{' = truncated):
        the constant all three other writers read for the provenance lines."""
        repo = pathlib.Path(tmp) / "stub-repo"
        (repo / "design" / "bitcell").mkdir(parents=True)
        (repo / "design" / "bitcell" / "sizing.json").write_text(body)
        return repo

    def test_make_record_unparseable_sizing_writes_nothing(self):
        """The repo-tracked sizing constant is still read after the mkdir pre-#172: the four
        report gzips orphan even with every report input present and parseable."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.make_record_argv(td, '{"corners": [], "environment": {}}')
            with mock.patch.object(make_record, "repo", self.sizing_repo(td, "{")):
                self.assert_refused(make_record.main, argv, ev, json.JSONDecodeError)

    def test_make_record_missing_request_writes_nothing(self):
        """The three sim/bitcell/requests/<bench>.request.json sha lookups ran after the gzip
        writes too (pre-#172, missed by the issue's sizing-only enumeration): one missing
        request file orphans all four report gzips."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.make_record_argv(td, '{"corners": [], "environment": {}}')
            repo = self.sizing_repo(td, (REPO / "design" / "bitcell" / "sizing.json").read_text())
            requests = repo / "sim" / "bitcell" / "requests"
            requests.mkdir(parents=True)
            for req in ("read_snm_corners", "hold_snm_corners"):  # write_trip_corners missing
                (requests / f"{req}.request.json").write_text("{}")
            with mock.patch.object(make_record, "repo", repo):
                self.assert_refused(make_record.main, argv, ev, FileNotFoundError)

    @staticmethod
    def write_mc_argv(tmp):
        """make_write_mc_record.py argv with two parseable reports: the base plus one new one
        (a single report writes no gzip at all, so the orphan would go unnoticed)."""
        tmp = pathlib.Path(tmp)
        body = '{"corners": [], "environment": {}}'
        (tmp / "base.json").write_text(body)
        (tmp / "new.json").write_text(body)
        return ["make_write_mc_record.py", "--id", "refuse", "--out", str(tmp / "record.md"),
                "--evidence", str(tmp / "ev"),
                "--report", str(tmp / "base.json"), str(tmp / "new.json")], tmp / "ev"

    def test_write_mc_unparseable_sizing_writes_nothing(self):
        """Same shape one writer later: the sizing constant is read after the new report's gzip
        landed pre-#172, so that gzip orphans."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.write_mc_argv(td)
            with mock.patch.object(make_write_mc_record, "repo", self.sizing_repo(td, "{")):
                self.assert_refused(make_write_mc_record.main, argv, ev, json.JSONDecodeError)

    def test_column_missing_request_writes_nothing(self):
        """One `sim/column/requests/<bench>.request.json` missing among eleven: its sha256
        lookup ran after all eleven bench gzips landed pre-#172 (the issue's edge case)."""
        with tempfile.TemporaryDirectory() as td:
            argv, ev = self.column_argv(td, '{"corners": [], "environment": {}}')
            repo = self.sizing_repo(td, "{}")
            requests = repo / "sim" / "column" / "requests"
            requests.mkdir(parents=True)
            for b in ["col_read0", "col_read1", "col_write1", "col_write0_nowen", "col_read_snm",
                      "col_hold_snm", "col_mc_read_snm", "col_mc_hold_snm", "col_mc_read_snm_neg",
                      "col_mc_hold_snm_neg"]:  # col_write0's request file is the missing one
                (requests / f"{b}.request.json").write_text("{}")
            with mock.patch.object(make_column_record, "repo", repo):
                self.assert_refused(make_column_record.main, argv, ev, FileNotFoundError)


unittest.main()
