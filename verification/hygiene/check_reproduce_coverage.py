#!/usr/bin/env python3
"""PDK-free Reproduce-coverage gate: every committed */records/ directory must
be accounted for in README.md's Reproduce section -- named in a table row's
Writes cell, or carried as a backticked path in the section preamble (today
the one deliberate exception, layout/records/). The symmetric rot is checked
too: a preamble exception or a Writes cell naming a records/ path that is no
longer a committed directory fails, so a renamed or deleted record directory
cannot leave a stale row behind silently.

The README is the single source of truth: no allowlist lives here. The
preamble/table split is structural -- everything before the '**PDK-free'
heading is preamble, the '|' rows after it are the table -- so the exception
stays exactly as human-readable as it is today. A parse failure (no '##
Reproduce' section, no '**PDK-free' split, no table rows, no 'Writes' column)
is itself a failure: a section that cannot be read must never pass as
"everything is covered".

Table cells split on unescaped '|' only, so a Command cell like
`run.sh [rtl\\|synth\\|both]` cannot shift the Writes column.

Needs only the standard library and git; writes nothing.

Usage: python3 -I verification/hygiene/check_reproduce_coverage.py
       (exit 0 clean, 1 on any failure)
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"

SEPARATOR_CELL = re.compile(r"^:?-+:?$")
BACKTICKED = re.compile(r"`([^`\n]+)`")


class ParseError(Exception):
    pass


def committed_records_dirs():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True,
                         capture_output=True, text=True).stdout
    dirs = set()
    for f in out.split():
        parts = f.split("/")[:-1]
        for i, part in enumerate(parts):
            if part == "records":
                dirs.add("/".join(parts[:i + 1]))
    return dirs


def records_dirs_in(spans):
    found = set()
    for span in spans:
        path = span.strip().rstrip("/")
        if path == "records" or path.endswith("/records"):
            found.add(path)
    return found


def split_row(line):
    cells = re.split(r"(?<!\\)\|", line.strip())
    return [c.strip() for c in cells[1:-1]] if len(cells) >= 2 else []


def parse_reproduce(text):
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines)
                     if line.strip() == "## Reproduce")
    except StopIteration:
        raise ParseError("no '## Reproduce' section heading found")
    section = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        section.append(line)
    try:
        split = next(i for i, line in enumerate(section)
                     if line.startswith("**PDK-free"))
    except StopIteration:
        raise ParseError("no '**PDK-free' subsection: cannot tell the "
                         "preamble from the table")
    preamble = "\n".join(section[:split])
    rows = [split_row(line) for line in section[split:]
            if line.lstrip().startswith("|")]
    if not rows:
        raise ParseError("no '|' table rows after the '**PDK-free' "
                         "subsection: Reproduce table not found")
    header_i = next((i for i, cells in enumerate(rows)
                     if not all(SEPARATOR_CELL.match(c) for c in cells)), None)
    if header_i is None:
        raise ParseError("Reproduce table has separator rows only")
    header = rows[header_i]
    if "Writes" not in header:
        raise ParseError(f"Reproduce table header {header} has no 'Writes' "
                         "column")
    writes_i = header.index("Writes")
    writes_cells = [cells[writes_i] if len(cells) > writes_i else ""
                    for cells in rows[header_i + 1:]
                    if not all(SEPARATOR_CELL.match(c) for c in cells)]
    return preamble, writes_cells


def main():
    try:
        text = README.read_text()
    except OSError as e:
        print(f"cannot read README.md: {e}", file=sys.stderr)
        return 1
    try:
        preamble, writes_cells = parse_reproduce(text)
    except ParseError as e:
        print(f"README.md Reproduce section is unparseable: {e}",
              file=sys.stderr)
        print("reproduce coverage: FAIL (section unparseable)")
        return 1
    excepted = records_dirs_in(BACKTICKED.findall(preamble))
    writes_text = "\n".join(writes_cells)
    row_named = records_dirs_in(BACKTICKED.findall(writes_text))
    committed = committed_records_dirs()
    problems = []
    for d in sorted(committed - excepted - row_named):
        problems.append(f"committed records/ directory is neither named in a "
                        f"Reproduce Writes cell nor preamble-excepted: {d}/")
    for d in sorted(excepted - committed):
        problems.append(f"preamble-excepted records/ path is not a committed "
                        f"directory: {d}/")
    for d in sorted(row_named - committed):
        problems.append(f"Reproduce Writes cell names a records/ path that is "
                        f"not a committed directory: {d}/")
    for p in problems:
        print(p, file=sys.stderr)
    print(f"reproduce coverage: {len(committed)} committed records/ "
          f"directories ({len(committed & row_named)} row-covered, "
          f"{len(committed & excepted)} preamble-excepted): "
          f"{'FAIL' if problems else 'ok'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
