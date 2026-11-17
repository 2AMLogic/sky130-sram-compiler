#!/usr/bin/env python3
"""PDK-free drift test: the Reproduce-coverage gate must actually bite.

Usage: python3 -I verification/hygiene/test_reproduce_coverage.py

CI (hygiene.yml) runs check_reproduce_coverage.py only in its passing
direction -- exit 0 on a fresh tree -- so a refactor that dropped one of its
failure modes would stay green forever, the shape #105 was filed about. This
suite probes every failure mode against a synthetic mini-repo: a throwaway
git repo holding a synthetic README fixture plus tracked records/ fixture
files, with the checker copied in and run for real (its ROOT, git ls-files
enumeration and parse all exercised end to end). Each mode asserts non-zero
exit and that the offending path is named. The real tree is asserted to pass
in the same run, so a fixture that drifted away from the README's actual
structure cannot mask a gate that no longer passes for the reason under
test.
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
CHECKER = pathlib.Path(__file__).with_name("check_reproduce_coverage.py")

GOOD_README = """\
# Block

## Reproduce

Every committed result is append-only evidence; each command below either
regenerates it into a new dated record or checks that the committed bytes
still match their generator. One exception is deliberate:
[`gone/records/`](gone/records/note.md) holds a historical development
record no single committed command regenerates, so it has no row below.

**PDK-free (run by CI, [`ci.yml`](.github/workflows/ci.yml)).**
Needs only `python3` and `git`.

```bash
python3 -I some/other_check.py
```

**Needs the PDK and/or simulators.** Not run in CI.

| Record | Command | Writes | Detail |
|---|---|---|---|
| A record | `make a` | `kept/records/` | [`a/README.md`](a/README.md) |
| B record, `rtl\\|synth` switchable | `make b [rtl\\|synth]` | `also/kept/records/` | [`b/README.md`](b/README.md) |
"""

GOOD_FILES = {
    "kept/records/a.md": "record a\n",
    "also/kept/records/b.md": "record b\n",
    "gone/records/note.md": "historical note\n",
}


def make_repo(files, readme):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="reprocover-"))
    (tmp / "verification/hygiene").mkdir(parents=True)
    shutil.copy(CHECKER, tmp / "verification/hygiene/check_reproduce_coverage.py")
    for rel, content in files.items():
        target = tmp / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    (tmp / "README.md").write_text(readme)
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True,
                   capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp, check=True,
                   capture_output=True)
    return tmp


def run_checker(root, argv=None):
    return subprocess.run(
        [sys.executable, "-I", *(argv or ["verification/hygiene/"
                                          "check_reproduce_coverage.py"])],
        cwd=root, capture_output=True, text=True, timeout=120)


class ReproduceCoverageBites(unittest.TestCase):
    def test_clean_fixture_passes(self):
        result = self.run_fixture(GOOD_FILES, GOOD_README)
        self.assertEqual(
            result.returncode, 0,
            "checker exits %d on a fixture where every records/ directory is "
            "accounted for (including the escaped-'|' row: a naive cell split "
            "would shift that row's Writes cell)\n%s%s"
            % (result.returncode, result.stdout, result.stderr))

    def test_uncovered_directory_fails(self):
        files = dict(GOOD_FILES, **{"sneaky/records/x.md": "uncovered\n"})
        result = self.run_fixture(files, GOOD_README)
        self.assertNotEqual(result.returncode, 0,
                            "checker exited 0 with an uncovered committed "
                            "records/ directory: the enumeration or the "
                            "row/preamble classification no longer bites")
        self.assertIn("sneaky/records", result.stderr,
                      "failure does not name the offending directory")

    def test_space_bearing_uncovered_directory_fails(self):
        files = dict(GOOD_FILES,
                     **{"old notes/records/uncovered.md": "uncovered\n"})
        result = self.run_fixture(files, GOOD_README)
        self.assertNotEqual(result.returncode, 0,
                            "checker exited 0 with an uncovered space-bearing "
                            "committed records/ directory")
        self.assertIn("old notes/records", result.stderr,
                      "failure does not name the space-bearing directory "
                      "verbatim (whitespace-mangled enumeration?)")

    def test_whitespace_collision_fails_not_vacuous_pass(self):
        files = {"old notes/records/a.md": "record a\n",
                 "also/kept/records/b.md": "record b\n",
                 "gone/records/note.md": "historical note\n"}
        readme = GOOD_README.replace("`kept/records/`", "`notes/records/`")
        result = self.run_fixture(files, readme)
        self.assertNotEqual(
            result.returncode, 0,
            "checker exited 0 with a Writes cell naming `notes/records/` "
            "while the tree commits only `old notes/records/`: a "
            "whitespace-mangled enumeration fragment must not read as "
            "everything-covered")
        self.assertIn("old notes/records", result.stderr,
                      "failure does not name the real uncovered directory "
                      "verbatim")

    def test_non_ascii_uncovered_directory_fails(self):
        files = dict(GOOD_FILES,
                     **{"répertoire/records/x.md": "uncovered\n"})
        result = self.run_fixture(files, GOOD_README)
        self.assertNotEqual(result.returncode, 0,
                            "checker exited 0 with an uncovered non-ASCII "
                            "committed records/ directory")
        self.assertIn("répertoire/records", result.stderr,
                      "failure does not name the non-ASCII directory "
                      "unquoted/verbatim (C-quoted enumeration?)")

    def test_stale_preamble_exception_fails(self):
        files = {k: v for k, v in GOOD_FILES.items()
                 if not k.startswith("gone/")}
        result = self.run_fixture(files, GOOD_README)
        self.assertNotEqual(result.returncode, 0,
                            "checker exited 0 with a preamble exception "
                            "whose directory is no longer committed")
        self.assertIn("gone/records", result.stderr,
                      "failure does not name the offending directory")

    def test_stale_writes_row_fails(self):
        files = {k: v for k, v in GOOD_FILES.items()
                 if not k.startswith("also/")}
        result = self.run_fixture(files, GOOD_README)
        self.assertNotEqual(result.returncode, 0,
                            "checker exited 0 with a Writes cell naming a "
                            "records/ path that is not a committed directory")
        self.assertIn("also/kept/records", result.stderr,
                      "failure does not name the offending directory")

    def test_missing_section_fails(self):
        readme = GOOD_README.replace("## Reproduce\n", "## History\n")
        result = self.run_fixture(GOOD_FILES, readme)
        self.assertNotEqual(
            result.returncode, 0,
            "checker exited 0 with no '## Reproduce' section: a parse failure "
            "must never read as everything-is-covered")

    def test_missing_table_fails(self):
        readme = "\n".join(line for line in GOOD_README.splitlines()
                           if not line.lstrip().startswith("|"))
        result = self.run_fixture(GOOD_FILES, readme)
        self.assertNotEqual(
            result.returncode, 0,
            "checker exited 0 with the Reproduce table removed: a missing "
            "table must never read as everything-is-covered")

    def test_missing_pdkfree_split_fails(self):
        readme = "\n".join(line for line in GOOD_README.splitlines()
                           if not line.startswith("**PDK-free"))
        result = self.run_fixture(GOOD_FILES, readme)
        self.assertNotEqual(
            result.returncode, 0,
            "checker exited 0 with the '**PDK-free' split removed: without it "
            "the preamble cannot be told from the table")

    def test_missing_writes_column_fails(self):
        readme = GOOD_README.replace("| Record | Command | Writes | Detail |",
                                     "| Record | Command | Output | Detail |")
        result = self.run_fixture(GOOD_FILES, readme)
        self.assertNotEqual(
            result.returncode, 0,
            "checker exited 0 with no 'Writes' column in the table header")

    def test_current_tree_passes(self):
        result = run_checker(REPO, argv=[str(CHECKER)])
        self.assertEqual(
            result.returncode, 0,
            "checker exits %d on the committed tree\n%s%s"
            % (result.returncode, result.stdout, result.stderr))

    def run_fixture(self, files, readme):
        tmp = make_repo(files, readme)
        try:
            return run_checker(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
