#!/usr/bin/env python3
"""PDK-free drift test: the format gate must actually bite.

Usage: python3 -I verification/hygiene/test_check_formats.py

CI (hygiene.yml) runs check_formats.py only in its passing direction -- exit
0 on a clean tree -- so an enumeration that silently drops tracked files from
the syntax-check set would stay green forever. This suite probes the
enumeration against a synthetic mini-repo: a throwaway git repo holding
fixture *.json / *.py files sized to the checker's MIN_JSON / MIN_PY floors,
with the checker copied in and run for real (its ROOT, git ls-files
enumeration and parse all exercised end to end). The probes use space-bearing
paths: an enumeration that splits on whitespace turns `my file.json` into the
fragment `file.json`, so the real file leaves the check set and a
non-existent path reaches read_text(), crashing the gate with a
FileNotFoundError traceback instead of a named finding. Each mode asserts
non-zero exit and that the offending path is named, never a traceback. The
real tree is asserted to pass in the same run, so a fixture that drifted away
from the checker's actual floors cannot mask a gate that no longer passes for
the reason under test.
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
CHECKER = pathlib.Path(__file__).with_name("check_formats.py")

# The fixture must meet the checker's coverage floors so that a clean fixture
# exits 0 and a failing fixture's only findings are the named files.
MIN_JSON = 61
MIN_PY = 31


def good_files():
    files = {}
    for i in range(MIN_JSON):
        files[f"data/fill_{i:02d}.json"] = '{"fill": %d}\n' % i
    for i in range(MIN_PY):
        files[f"src/fill_{i:02d}.py"] = "VALUE = %d\n" % i
    return files


def make_repo(files):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="checkformats-"))
    (tmp / "verification/hygiene").mkdir(parents=True)
    shutil.copy(CHECKER, tmp / "verification/hygiene/check_formats.py")
    for rel, content in files.items():
        target = tmp / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True,
                   capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True,
                   capture_output=True)
    return tmp


def run_checker(root):
    return subprocess.run(
        [sys.executable, "-I", "verification/hygiene/check_formats.py"],
        cwd=root, capture_output=True, text=True, timeout=120)


class CheckFormatsBites(unittest.TestCase):
    def test_clean_fixture_passes(self):
        result = self.run_fixture(good_files())
        self.assertEqual(
            result.returncode, 0,
            "checker exits %d on a fixture meeting its own floors\n%s%s"
            % (result.returncode, result.stdout, result.stderr))

    def test_space_bearing_valid_json_is_counted(self):
        # Exactly MIN_JSON valid JSON files, one of them space-bearing: the
        # floor is only met if `my data.json` is enumerated whole. A
        # whitespace-split enumeration reads the non-existent fragment
        # `data.json` instead and dies on a FileNotFoundError traceback.
        files = {}
        for i in range(MIN_JSON - 1):
            files[f"data/fill_{i:02d}.json"] = '{"fill": %d}\n' % i
        files["my data.json"] = '{"space bearing": true}\n'
        for i in range(MIN_PY):
            files[f"src/fill_{i:02d}.py"] = "VALUE = %d\n" % i
        result = self.run_fixture(files)
        self.assertEqual(
            result.returncode, 0,
            "checker exits %d with %d valid JSON files where one is "
            "space-bearing: the space-bearing path is not enumerated whole "
            "(whitespace-mangled enumeration?)\n%s%s"
            % (result.returncode, MIN_JSON, result.stdout, result.stderr))
        self.assertNotIn("Traceback", result.stderr,
                         "a counted fixture must not crash with a traceback")

    def test_invalid_space_bearing_json_reported_by_name(self):
        files = good_files()
        files["bad file.json"] = "{not json\n"
        result = self.run_fixture(files)
        self.assertNotEqual(
            result.returncode, 0,
            "checker exited 0 with an invalid committed space-bearing JSON "
            "file: it is not being validated at all")
        self.assertIn(
            "bad file.json", result.stderr,
            "failure does not name the space-bearing path verbatim "
            "(whitespace-mangled enumeration?)")
        self.assertNotIn(
            "Traceback", result.stderr,
            "a bad file must be a named finding, not a FileNotFoundError "
            "traceback from a whitespace-split fragment")

    def test_space_bearing_py_syntax_error_reported_by_name(self):
        files = good_files()
        files["bad module.py"] = "def f(:\n"
        result = self.run_fixture(files)
        self.assertNotEqual(
            result.returncode, 0,
            "checker exited 0 with a committed space-bearing Python source "
            "that does not compile: it is not being compiled at all")
        self.assertIn(
            "bad module.py", result.stderr,
            "failure does not name the space-bearing path verbatim "
            "(whitespace-mangled enumeration?)")
        self.assertNotIn(
            "Traceback", result.stderr,
            "a bad file must be a named finding, not a FileNotFoundError "
            "traceback from a whitespace-split fragment")

    def test_current_tree_passes(self):
        result = run_checker(REPO)
        self.assertEqual(
            result.returncode, 0,
            "checker exits %d on the committed tree\n%s%s"
            % (result.returncode, result.stdout, result.stderr))

    def run_fixture(self, files):
        tmp = make_repo(files)
        try:
            return run_checker(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
