#!/usr/bin/env python3
"""PDK-free format gate: every committed evidence/request JSON parses and every
Python source compiles. Needs only the standard library; writes nothing.

Usage: python3 -I verification/hygiene/check_formats.py     (exit 0 clean, 1 on any failure)
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JSON_GLOBS = ("manifests/*.json", "sim/pdk.json", "sim/bitcell/requests/*.json",
              "design/*/sizing.json", "design/compiler/inventory.json",
              "design/compiler/evidence/*.json", "verification/hygiene/*.json")
PY_GLOBS = ("sim/bitcell/lib/*.py", "design/bitcell/*.py", "design/compiler/*.py",
            "verification/marker/*.py", "verification/hygiene/*.py")


def tracked(globs):
    out = subprocess.run(["git", "ls-files", "--", *globs], cwd=ROOT, check=True,
                         capture_output=True, text=True).stdout
    return sorted(out.split())


def main():
    bad = []
    jsons, pys = tracked(JSON_GLOBS), tracked(PY_GLOBS)
    for rel in jsons:
        try:
            json.loads((ROOT / rel).read_text())
        except ValueError as e:
            bad.append(f"{rel}: invalid JSON: {e}")
    for rel in pys:
        try:
            compile((ROOT / rel).read_text(), rel, "exec")
        except SyntaxError as e:
            bad.append(f"{rel}: {e}")
    if not jsons or not pys:
        bad.append("no files matched: globs are stale")
    for line in bad:
        print(line, file=sys.stderr)
    print(f"checked {len(jsons)} JSON and {len(pys)} Python files: {'FAIL' if bad else 'ok'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
