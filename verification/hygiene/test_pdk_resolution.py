"""PDK-free regression test: the deck runners must resolve a variant DIR while
PDK keeps its variant-NAME meaning.

Usage: python3 -I verification/hygiene/test_pdk_resolution.py

Issue #131: design/bitcell/three_deck_drc.sh and verification/marker/
run_checks.sh each read ${PDK:-...} as a directory, which collided with
sim/env.sh exporting PDK=sky130A (the ciel/volare convention: PDK is the
variant NAME, PDK_ROOT its parent dir). Both runners now resolve

    PDK_DIR=${SKY130_VARIANT_DIR:-${PDK_ROOT:-$HOME/.ciel}/${PDK:-sky130A}}

This suite runs each runner's real code path against a stubbed `klt` on PATH
and a fake variant dir under a fake HOME, so it needs no PDK install and no
klayout engine. It asserts, in the exact #131 collision shape (PDK=sky130A
with PDK_ROOT and SKY130_VARIANT_DIR unset), that the resolved dir is absolute
and correct; that both legacy styles still resolve; and that the old dir-style
override and a non-absolute dir now fail loudly naming SKY130_VARIANT_DIR.

Unwired from .github/workflows/hygiene.yml / manifests/hygiene-inventory.json
on purpose: wiring costs an item-10 re-attestation (issue #88 owns that), so
run it by hand, as verification/hygiene/test_check_gates.py (#87) also is.
"""
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
THREE_DECK = REPO / "design/bitcell/three_deck_drc.sh"
RUN_CHECKS = REPO / "verification/marker/run_checks.sh"
DECK_REL = "libs.tech/klayout/drc/sky130A_mr.drc"

KLT_STUB = "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"${KLT_STUB_LOG:?}\"\nexit 0\n"
PY_STUB = "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"${KLT_PY_LOG:?}\"\nexit 0\n"


class PDKResolution(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = pathlib.Path(tmp.name)
        self.home = root / "home"
        self.variant = self.home / ".ciel" / "sky130A"
        deck = self.variant / DECK_REL
        deck.parent.mkdir(parents=True)
        deck.write_text("# stub deck\n")
        self.bin = root / "bin"
        self.bin.mkdir()
        (self.bin / "klt").write_text(KLT_STUB)
        (self.bin / "klt").chmod(0o755)
        self.klt_py = self.bin / "klt-python-stub"
        self.klt_py.write_text(PY_STUB)
        self.klt_py.chmod(0o755)
        self.klt_log = root / "klt.log"
        self.py_log = root / "klt_py.log"
        self.out = root / "out"

    def run_env(self, **over):
        e = {k: v for k, v in os.environ.items()
             if k not in ("PDK", "PDK_ROOT", "SKY130_VARIANT_DIR", "KLT_PY")}
        e["HOME"] = str(self.home)
        e["PATH"] = f"{self.bin}:{e.get('PATH', '')}"
        e["KLT_STUB_LOG"] = str(self.klt_log)
        e["KLT_PY_LOG"] = str(self.py_log)
        e.update(over)
        return e

    def run_three_deck(self, **over):
        return subprocess.run(
            [str(THREE_DECK), "dummy.gds", str(self.out)],
            env=self.run_env(**over), capture_output=True, text=True, timeout=120)

    def deck_file_args(self):
        return self.klt_log.read_text().splitlines()

    def test_collision_shape_resolves_absolute_dir(self):
        # The exact #131 shape: sim/env.sh sourced -> PDK=sky130A, PDK_ROOT and
        # SKY130_VARIANT_DIR unset. The old code read PDK as a directory and aborted.
        r = self.run_three_deck(PDK="sky130A")
        self.assertEqual(r.returncode, 0, r.stderr)
        mr = [l for l in self.deck_file_args() if "--deck-file" in l]
        self.assertEqual(len(mr), 1, self.klt_log.read_text())
        self.assertIn(f"--deck-file {self.variant / DECK_REL} ", mr[0])
        self.assertIn("--deck-var feol=true --deck-var beol=true --deck-var thr=1", mr[0])

    def test_nothing_sourced_falls_back_to_ciel_default(self):
        r = self.run_three_deck()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"--deck-file {self.variant / DECK_REL}",
                      self.deck_file_args()[2])

    def test_variant_dir_wins_over_disagreeing_pdk(self):
        # sky130B does not exist under the fake ciel root, so only the
        # SKY130_VARIANT_DIR leg can resolve.
        r = self.run_three_deck(SKY130_VARIANT_DIR=str(self.variant), PDK="sky130B")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f"--deck-file {self.variant / DECK_REL}",
                      self.deck_file_args()[2])

    def test_dir_style_pdk_override_fails_loudly(self):
        # Old README style: PDK=<.../sky130A> as a directory. Must fail loudly
        # naming SKY130_VARIANT_DIR, not silently mis-resolve.
        r = self.run_three_deck(PDK=str(self.variant))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("SKY130_VARIANT_DIR", r.stderr)

    def test_non_absolute_dir_fails_naming_override(self):
        r = self.run_three_deck(PDK_ROOT="relative/pdk", PDK="sky130A")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("SKY130_VARIANT_DIR", r.stderr)

    def test_run_checks_passes_absolute_dir_to_build_cases(self):
        r = subprocess.run(
            [str(RUN_CHECKS), str(self.out)],
            env=self.run_env(PDK="sky130A", KLT_PY=str(self.klt_py)),
            capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stderr)
        first = self.py_log.read_text().splitlines()[0]
        self.assertEqual(
            first, f"-I {REPO / 'verification/marker/build_cases.py'} "
                   f"{self.variant} {self.out}",
            "run_checks.sh did not pass an absolute variant dir to build_cases.py")


if __name__ == "__main__":
    unittest.main()
