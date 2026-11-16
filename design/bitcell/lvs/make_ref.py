#!/usr/bin/env python3
"""Reference and negative-control netlists for the bitcell LVS (step 1 of run_lvs.sh).

Usage: make_ref.py <sizing.json> <bitcell_6t.spice> <outdir>
Writes <outdir>/ref.spice (nfet bulk moved to vsubs) and <outdir>/ref_bad.spice
(MAL width perturbed). Exits 1 if the XMAL line does not carry the sizing width,
or if the perturbed width is not a plain numeric literal — an anchor-class
failure, so a formatter mismatch can never surface as the LVS verdict
(run_lvs.sh exit 5). Extracted from run_lvs.sh's heredoc so
test_make_ref.py can reach it without the PDK.
"""
import json
import pathlib
import re
import sys

# a plain numeric literal, the only parameter form klt lvs accepts for a device value
PLAIN_NUMERIC = re.compile(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


class AnchorError(Exception):
    """The XMAL line does not carry the sizing width, or the perturbed width is not numeric."""


def assert_plain_numeric(token):
    if not PLAIN_NUMERIC.fullmatch(token):
        raise AnchorError(
            f"make_ref.py: perturbed width token W={token} is not a single plain numeric literal"
        )


def perturb(ln, ax_w):
    """-> (line, nsub) with MAL's drawn width perturbed for the negative control."""
    # Match with str(ax_w) — the exact literal gen_schematic.py writes (W={w}) — escaped,
    # with (?![\d.]) so a longer token (W=0.425 vs 0.42) fails the anchor instead of matching
    # a prefix (:g would drop the .0 of an integer width and \b alone accepts the '.').
    # The emitted value keeps :g on purpose: str(0.7 + 0.1) is 0.7999999999999999, :g is 0.8.
    w = f"{ax_w + 0.1:g}"
    assert_plain_numeric(w)
    return re.subn(rf"\bW={re.escape(str(ax_w))}(?![\d.])", f"W={w}", ln)


def rewrite(ax_w, text):
    """-> (ref, ref_bad) netlist texts; raises AnchorError if the anchor fails."""
    good, bad, done = [], [], False
    for ln in text.splitlines():
        if ln.startswith(".subckt"):
            ln += " vsubs"
        m = re.match(r"^(X\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(sky130_fd_pr__nfet_01v8)(.*)$", ln)
        if m:
            ln = f"{m.group(1)} {m.group(2)} {m.group(3)} {m.group(4)} vsubs {m.group(6)}{m.group(7)}"
        good.append(ln)
        if ln.startswith("XMAL "):
            ln, n = perturb(ln, ax_w)
            done = done or bool(n)
        bad.append(ln)
    if not done:
        raise AnchorError(
            f"make_ref.py: negative-control anchor (XMAL W={ax_w}) not found in the rewritten reference"
        )
    return "\n".join(good) + "\n", "\n".join(bad) + "\n"


def main(argv):
    if len(argv) != 4:
        sys.exit(f"usage: {pathlib.Path(argv[0]).name} <sizing.json> <bitcell_6t.spice> <outdir>")
    sizing, src, out = argv[1], argv[2], argv[3]
    ax_w = json.load(open(sizing))["ax"]["w"]
    try:
        good, bad = rewrite(ax_w, open(src).read())
    except AnchorError as e:
        sys.exit(str(e))
    pathlib.Path(out).mkdir(parents=True, exist_ok=True)
    (pathlib.Path(out) / "ref.spice").write_text(good)
    (pathlib.Path(out) / "ref_bad.spice").write_text(bad)


if __name__ == "__main__":
    main(sys.argv)
