"""PDK-free drift test: every --check gate the hygiene inventory declares must
actually exit non-zero when each of its guarded artifacts drifts.

Usage: python3 -I verification/hygiene/test_check_gates.py

CI only ever exercises these gates in their passing direction (exit 0 on a
fresh tree), so a refactor that dropped or inverted a gate's comparison would
leave the artifact contract silently gone. This suite closes that hole.

Gates are selected from manifests/hygiene-inventory.json (entries whose argv
contains "--check"), so a gate added to the inventory is covered on the day it
lands, with no edit to this file. Each gate runs once on a pristine throwaway
copy of the repo (must exit 0), then once per guarded member -- each member
probed in its own fresh throwaway copy after one byte is appended to it (must
exit non-zero; the gates deliberately differ in their drift code, 1 vs 3, so
only non-zero is asserted). One copy per probe keeps every member isolated: a
perturb-and-restore inside a shared copy would turn one non-byte-exact restore
into spurious greens for every later member of that gate, the one shape this
suite must never produce. Nothing inside the repository is written, so there
is no restore logic to skip and no evidence input-set binding can go stale.

The one thing the inventory cannot say is which committed files each gate
guards: only macro-256x32-m4 and bitcell-layout name their artifacts in argv,
the other gates
derive their output paths internally from __file__. Those are mapped in
ARTIFACTS below as per-gate glob pattern lists, resolved against the repo copy
at run time. Patterns rather than a hardcoded path list give the member set
the same covered-on-the-day-it-lands property the inventory-driven gate
selection already has: the guarded set is 61 members across the 6 gates
(measured on 88af0fd, 2026-11-16), and a hardcoded list goes stale exactly
where it matters -- a 10th periphery cell or a new column request lands
unprobed and the suite stays green. A gate whose patterns resolve to zero
members fails the suite by name: that is the one failure mode globs add (a
renamed or moved directory), and an unasserted empty set would be the same
silently-passing-gate shape this suite exists to catch. A selected gate
without an ARTIFACTS entry likewise fails the suite loudly rather than
skipping, so adding an inventory --check gate without drift coverage turns
this suite red instead of silently passing.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
INVENTORY = REPO / "manifests/hygiene-inventory.json"

ARTIFACTS = {
    "compiler-schematics": ["design/compiler/cells/*.sch"],
    "bitcell-schematic": ["design/bitcell/bitcell_6t.sch"],
    "macro-256x32-m4": ["design/compiler/macro/sram_256x32_m4.spice"],
    "bitcell-sim-requests": ["sim/bitcell/tb/*.sp",
                             "sim/bitcell/requests/*.request.json"],
    "bitcell-layout": ["design/bitcell/bitcell_6t.gds"],
    "column-sim-requests": ["sim/column/tb/*.sp",
                            "sim/column/requests/*.request.json"],
}

COPY_IGNORE = shutil.ignore_patterns(".git", ".loom", ".snapshots", "__pycache__")


def selected_gates():
    inventory = json.loads(INVENTORY.read_text())
    return [c for c in inventory["checks"] if "--check" in c["argv"]]


def guarded_members(patterns):
    members = []
    for pattern in patterns:
        members.extend(sorted(
            p.relative_to(REPO).as_posix() for p in REPO.glob(pattern)))
    return members


def run_gate(argv, cwd):
    return subprocess.run([sys.executable, *argv[1:]], cwd=cwd,
                          capture_output=True, text=True, timeout=120)


class CheckGatesBite(unittest.TestCase):
    def test_selector_finds_gates(self):
        self.assertGreaterEqual(
            len(selected_gates()), 1,
            "no --check gate selected from %s: the selector is stale or the "
            "inventory lost its drift gates" % INVENTORY.relative_to(REPO))

    def test_every_selected_gate_is_covered(self):
        missing = sorted(c["name"] for c in selected_gates() if c["name"] not in ARTIFACTS)
        self.assertEqual(
            missing, [],
            "no ARTIFACTS entry for inventory --check gate(s) %s: add the committed "
            "artifact each one guards. A selected gate without drift coverage fails "
            "this suite by design -- it must never skip or pass silently." % missing)

    def test_clean_copy_passes_and_one_byte_drift_fails(self):
        for gate in selected_gates():
            with self.subTest(gate=gate["name"]):
                patterns = ARTIFACTS.get(gate["name"])
                if patterns is None:
                    self.fail("no ARTIFACTS entry for gate %s" % gate["name"])
                members = guarded_members(patterns)
                self.assertNotEqual(
                    members, [],
                    "ARTIFACTS patterns %s for gate %s matched zero committed files: "
                    "the gate's guarded paths moved or were renamed. Fix the patterns "
                    "so the gate is probed -- a zero-member gate must fail this suite "
                    "by name, never skip." % (patterns, gate["name"]))
                with tempfile.TemporaryDirectory() as tmp:
                    shutil.copytree(REPO, tmp, dirs_exist_ok=True, ignore=COPY_IGNORE)
                    clean = run_gate(gate["argv"], tmp)
                    self.assertEqual(
                        clean.returncode, 0,
                        "%s exits %d on an unperturbed copy of the tree\n%s%s"
                        % (gate["name"], clean.returncode, clean.stdout, clean.stderr))
                for member in members:
                    with self.subTest(member=member):
                        with tempfile.TemporaryDirectory() as tmp:
                            shutil.copytree(REPO, tmp, dirs_exist_ok=True,
                                            ignore=COPY_IGNORE)
                            target = pathlib.Path(tmp) / member
                            target.write_bytes(target.read_bytes() + b"\n")
                            drifted = run_gate(gate["argv"], tmp)
                            self.assertNotEqual(
                                drifted.returncode, 0,
                                "%s exited 0 after one byte was appended to %s: the gate "
                                "no longer bites for this member (drift stderr: %s)"
                                % (gate["name"], member, drifted.stderr.strip()))


if __name__ == "__main__":
    unittest.main()
