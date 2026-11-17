"""PDK-free regression test: the `klt erc` evidence runner must gate `klt erc`
exit codes, and the `--write` copy of the four reports over the committed
evidence must sit behind a structural validation of every envelope.

Usage: python3 -I verification/hygiene/test_erc_exit_gate.py

Issue #185: layout/erc/run_erc.sh ran every `klt erc` call with a trailing
`|| true` -- the one klt evidence runner #183's exit gate
(test_drc_exit_gate.py) never reached -- and with `--write` it copied all four
reports over the committed layout/erc/*.json evidence BEFORE the verdict block
parsed them. A klt/deck crash (exit 1/2) thus produced empty or keyless
reports that were copied over attested evidence, clobbering it, with the
JSONDecodeError firing only afterwards.

klt erc exit contract (klayout-tools==0.9.0, docs/cli/erc.md): 0
clean/clean_partial, 3 violations, 4 not_checked -- and every --findings-only
run that completes exits 3 or 4, because --findings-only skips the antenna
accumulation outright (#2219), so a clean connectivity read is
`not_checked`/exit 4, never 0. Exit 1 (ErcError: bad file/spec, unresolvable
top cell) and 2 (argparse usage) are failures and abort the run with that
code. The connectivity verdict itself lives in the payload's `erc_status`,
which the runner's verdict block grades.

This suite stubs `uv` and `uvx` on PATH (no klayout module, no PDK -- the
test_drc_exit_gate.py shape; run_erc.sh reaches klt only through them) and
asserts, against the real script run inside a scratch copy of the tree it
writes into -- a SIGKILL or timeout mid-subtest can no longer leave stub
envelopes over the attested layout/erc/*.json evidence (#189):
  - the expected verdicts (clean macro/control, blocking severed-rail
    findings) complete with exit 0, and --write copies the envelopes
    unmodified over the committed evidence;
  - a klt failure (exit 1) aborts with that code, naming the .err file, with
    the committed evidence byte-identical;
  - crash debris (an empty or keyless "report" from a call that exited 4) is
    refused before any copy, with the committed evidence byte-identical;
  - a structurally valid envelope that fails its verdict (a severed control
    that blocked nothing) is still copied -- the verdict exit does not undo a
    copy of valid evidence, only the structural gate refuses one.
"""
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
RUN_ERC = REPO / "layout/erc/run_erc.sh"

EVIDENCE = ("erc_macro", "erc_control", "erc_macro_severed_vss", "erc_macro_severed_vdd")

# Structurally valid envelopes in the shape the verdict block grades: the clean
# one is what the macro and control runs must produce, the findings one what
# each severed-rail negative control must produce (erc_status is the
# connectivity verdict; top-level `status` is the antenna roll-up, always
# not_checked on a --findings-only run, and unread by the verdict block).
CLEAN_ENV = json.dumps({
    "schema_version": 1,
    "status": "not_checked",
    "erc_status": "clean",
    "erc_findings": [],
    "erc_coverage": {"missing_tie_checked": 2, "skipped": []},
})

FINDINGS_ENV = json.dumps({
    "schema_version": 1,
    "status": "violations",
    "erc_status": "violations",
    "erc_findings": [{"rule": 'erc.unconnected_net:["VSS"]', "net": "VSS"}],
    "erc_coverage": {"missing_tie_checked": 2, "skipped": []},
})

# klt stub, reached as `uvx --from <pin> klt erc <gds> <spec> --findings-only
# ...`: the severed-rail calls exit 3 (violations), the others 4 (not_checked,
# the clean --findings-only outcome), unless KLT_STUB_RC overrides every call.
# KLT_STUB_STDOUT, when set (even empty), replaces the envelope -- the crash
# debris a real klt writes before dying.
KLT_STUB = r"""#!/bin/sh
rc=${KLT_STUB_ERC_RC:-4}
name=KLT_STUB_CLEAN_ENV
case "$*" in
  *severed_vss*|*severed_vdd*) rc=${KLT_STUB_SEVERED_RC:-3}; name=KLT_STUB_FINDINGS_ENV ;;
esac
if [ -n "${KLT_STUB_RC:-}" ]; then rc=$KLT_STUB_RC; fi
if [ "${KLT_STUB_STDOUT+set}" = set ]; then
  printf '%s' "$KLT_STUB_STDOUT"
else
  eval "printf '%s\n' \"\${$name}\""
fi
exit "$rc"
"""

# uv stub for `uv run --no-project --with klayout python -I ...`: the two
# gen_erc_spec.py --check calls exit 0 (the committed specs exist; their
# content cannot matter here because klt itself is stubbed), and the
# severed-rail heredoc call fabricates the two GDS files the runner hands to
# the stubbed klt.
UV_STUB = r"""#!/bin/sh
for last; do :; done
case "$*" in
  *" -I - "*) : > "$last/severed_vss.gds"; : > "$last/severed_vdd.gds" ;;
esac
exit 0
"""


class StubEnv(unittest.TestCase):
    """Stubs on PATH, a scratch copy of the tree run_erc.sh writes into,
    a scratch outdir."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = pathlib.Path(tmp.name)
        repo = self.repo = self.root / "repo"
        (repo / "layout/erc").mkdir(parents=True)
        # The script itself (copy2 keeps the exec bit) and the four committed
        # evidence files: everything run_erc.sh opens or writes under its
        # resolved repo. The specs, generator and GDS inputs are only passed
        # as argv strings -- uv and uvx are stubbed below -- so the scratch
        # copy never needs them.
        shutil.copy2(RUN_ERC, repo / "layout/erc/run_erc.sh")
        self.before = {}
        for k in EVIDENCE:
            data = (REPO / f"layout/erc/{k}.json").read_bytes()
            (repo / f"layout/erc/{k}.json").write_bytes(data)
            self.before[k] = data
        self.bin = self.root / "bin"
        self.bin.mkdir()
        for name, body in (("uv", UV_STUB), ("uvx", KLT_STUB)):
            p = self.bin / name
            p.write_text(body)
            p.chmod(0o755)
        self.env = dict(os.environ)
        self.env["PATH"] = f"{self.bin}:{self.env.get('PATH', '')}"
        self.env["KLT_STUB_CLEAN_ENV"] = CLEAN_ENV
        self.env["KLT_STUB_FINDINGS_ENV"] = FINDINGS_ENV
        self.out = self.root / "out"

    def run_erc(self, write=True, **rc):
        self.env.update({k: str(v) for k, v in rc.items()})
        script = self.repo / "layout/erc/run_erc.sh"
        cmd = [str(script)] + (["--write"] if write else []) + [str(self.out)]
        return subprocess.run(cmd, env=self.env, capture_output=True,
                              text=True, timeout=120)

    def assert_evidence_untouched(self):
        for k in EVIDENCE:
            self.assertEqual((self.repo / f"layout/erc/{k}.json").read_bytes(),
                             self.before[k], k)


class ErcGate(StubEnv):
    def test_expected_outcomes_complete_and_write_copies(self):
        r = self.run_erc(write=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        for k in EVIDENCE:
            want = (FINDINGS_ENV if k.startswith("erc_macro_severed")
                    else CLEAN_ENV) + "\n"
            self.assertEqual(
                (self.repo / f"layout/erc/{k}.json").read_bytes().decode(),
                want, k)
            self.assertEqual(
                (self.out / f"{k}.json").read_bytes().decode(), want, k)

    def test_verdict_failure_still_reports_and_keeps_valid_evidence(self):
        # Every envelope clean, including both severed controls: a control
        # produced no blocking finding, verdict exit 4 -- and the copy of the
        # structurally valid evidence stands (the verdict exit does not undo
        # it; the evidence IS the finding).
        r = self.run_erc(write=True, KLT_STUB_RC=4,
                         KLT_STUB_FINDINGS_ENV=CLEAN_ENV)
        self.assertEqual(r.returncode, 4, r.stderr)
        self.assertEqual(
            (self.repo
             / "layout/erc/erc_macro_severed_vss.json").read_bytes().decode(),
            CLEAN_ENV + "\n")

    def test_klt_failure_aborts_with_that_code_evidence_untouched(self):
        for rc in (1, 2):
            with self.subTest(rc=rc):
                r = self.run_erc(write=True, KLT_STUB_RC=rc, KLT_STUB_STDOUT="")
                self.assertEqual(
                    r.returncode, rc,
                    f"klt erc exit {rc} was not propagated: the run completed "
                    f"(exit 0 would mean the report is crash debris)")
                self.assertIn("FAILED", r.stderr)
                self.assertIn(f"exit {rc}", r.stderr)
                self.assertFalse(
                    (self.out / "erc_control.json").exists(),
                    "the run continued past a failed klt erc call")
                self.assert_evidence_untouched()

    def test_crash_debris_refused_before_write_copy(self):
        # A call that exited 4 but wrote nothing, or keyless JSON: the old
        # order copied the debris over layout/erc/*.json and only then died on
        # json.load -- attested evidence gone. The structural gate must refuse
        # it before any copy, with --write and without.
        for write in (True, False):
            for debris, what in (("", "empty stdout"), ("{}", "keyless JSON")):
                with self.subTest(write=write, what=what):
                    r = self.run_erc(write=write, KLT_STUB_RC=4,
                                     KLT_STUB_STDOUT=debris)
                    self.assertNotEqual(
                        r.returncode, 0,
                        f"{what} accepted as a `klt erc` envelope")
                    self.assertIn("erc_macro.json", r.stderr)
                    self.assertNotIn("Traceback", r.stderr)
                    self.assert_evidence_untouched()


if __name__ == "__main__":
    unittest.main()
