"""Netlist every periphery schematic (and check the bitcell's) with `klt netlist`.

Usage: python3 -I design/compiler/netlists.py [--check]
Writes design/compiler/netlist/<cell>.spice in canonical logical form (see
cells.normalise_netlist: no machine-specific `sch_path`, continuations joined).
--check regenerates into a temp dir and compares the *normalised* text, exiting 3
on drift; it also checks design/bitcell/netlist/bitcell_6t.spice the same way,
because plain `klt netlist --check` cannot (its output embeds an absolute
sch_path, so the committed, path-rewritten netlist always reads as drifted).
Needs xschem, the sky130 PDK (PDK_ROOT) and klt on PATH.
"""
import os
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I drops the script dir
import cells  # noqa: E402

here = pathlib.Path(__file__).resolve().parent
root = here.parent.parent


def klt_netlist(sch, rcfile, tmp):
    dst = pathlib.Path(tmp) / (sch.stem + ".spice")
    env = dict(os.environ, PDK=os.environ.get("PDK", "sky130A"))
    subprocess.run(["klt", "netlist", str(sch), "-o", str(dst), "--block", "--rcfile", str(rcfile),
                    "--timeout-s", "120"], check=True, env=env, stdout=subprocess.DEVNULL)
    return cells.normalise_netlist(dst.read_text())


def main():
    check = "--check" in sys.argv[1:]
    jobs = [(here / "cells" / f"{n}.sch", here / "xschemrc", here / "netlist" / f"{n}.spice", True)
            for n in sorted(cells.CELLS)]
    jobs.append((root / "design/bitcell/bitcell_6t.sch", root / "design/bitcell/xschemrc",
                 root / "design/bitcell/netlist/bitcell_6t.spice", False))
    drift = []
    with tempfile.TemporaryDirectory() as tmp:
        for sch, rc, spice, owned in jobs:
            fresh = klt_netlist(sch, rc, tmp)
            if check or not owned:
                if not spice.exists() or cells.normalise_netlist(spice.read_text()) != fresh:
                    drift.append(str(spice.relative_to(root)))
            else:
                spice.parent.mkdir(exist_ok=True)
                spice.write_text("\n".join(["** sch_path: " + str(sch.relative_to(root))] + fresh) + "\n")
                print("wrote", spice.relative_to(root))
    if drift:
        print("drifted:", " ".join(drift), file=sys.stderr)
        sys.exit(3)


main()
