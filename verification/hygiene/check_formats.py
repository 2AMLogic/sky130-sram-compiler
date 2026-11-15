#!/usr/bin/env python3
"""PDK-free format gate: every committed evidence/request JSON parses and every
Python source compiles. Needs only the standard library; writes nothing.

Coverage is a sweep over every tracked *.json / *.py minus one shared exclusion
list, with the expected counts asserted as floors (MIN_JSON / MIN_PY): adding a
tracked project file is covered automatically, and a count that falls below a
floor means the sweep or its exclusions broke and files lost coverage silently.

Usage: python3 -I verification/hygiene/check_formats.py     (exit 0 clean, 1 on any failure)
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Vendored tooling and workspace state, never this block's evidence:
# .loom/ (orchestration runtime; its test fixtures may be deliberately
# malformed), .claude/ and .agents/ (vendored assistant tooling), and the
# npm manifest package.json.
EXCLUDED_PREFIXES = (".loom/", ".claude/", ".agents/")
EXCLUDED_FILES = ("package.json",)

# Coverage floors. The sweep covers every tracked project file by construction,
# so a real count can only grow; falling below a floor means the mechanism broke.
MIN_JSON = 61
MIN_PY = 31


def tracked_files():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True,
                         capture_output=True, text=True).stdout
    files = out.split()
    return [f for f in files
            if (f.endswith(".json") or f.endswith(".py"))
            and not f.startswith(EXCLUDED_PREFIXES)
            and f not in EXCLUDED_FILES]


def main():
    bad = []
    files = tracked_files()
    jsons = sorted(f for f in files if f.endswith(".json"))
    pys = sorted(f for f in files if f.endswith(".py"))
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
    if len(jsons) < MIN_JSON:
        bad.append(f"JSON coverage regressed: {len(jsons)} files, floor is {MIN_JSON}")
    if len(pys) < MIN_PY:
        bad.append(f"Python coverage regressed: {len(pys)} files, floor is {MIN_PY}")
    for line in bad:
        print(line, file=sys.stderr)
    print(f"checked {len(jsons)} JSON and {len(pys)} Python files: {'FAIL' if bad else 'ok'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
