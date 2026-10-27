"""Periphery cell definitions shared by the schematic, netlist and macro generators.

Each cell is a port list plus a device list; sizes come from sizing.json (one
role per device class). Topology notes and the port names are documented in
design/compiler/README.md; the macro assembler (sram_compile.py) and later
layout/LVS work (#30, #33) depend on these port names, so keep them stable.

Run with `python3 -I` (no third-party imports).
"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
SIZING = json.loads((HERE / "sizing.json").read_text())

MODELS = {"nfet_01v8", "pfet_01v8"}  # the only devices the periphery may use


def _nand(k):
    ports = [f"A{i}" for i in range(k)] + ["Y", "VDD", "VSS"]
    devs = [(f"MP{i}", f"nand{k}_p", "Y", f"A{i}", "VDD", "VDD") for i in range(k)]
    chain = ["Y"] + [f"N{i}" for i in range(1, k)] + ["VSS"]
    devs += [(f"MN{i}", f"nand{k}_n", chain[i], f"A{i}", chain[i + 1], "VSS") for i in range(k)]
    return ports, devs


def _inv(role):
    return (["A", "Y", "VDD", "VSS"],
            [("MP", f"{role}_p", "Y", "A", "VDD", "VDD"), ("MN", f"{role}_n", "Y", "A", "VSS", "VSS")])


CELLS = {
    "sram_inv": _inv("inv"),
    "sram_nand2": _nand(2),
    "sram_nand3": _nand(3),
    "sram_nand4": _nand(4),
    # Wordline driver: an inverter sized to drive one row of bitcell access gates.
    "sram_wldrv": _inv("wldrv"),
    # Per physical column: precharge both bitlines high, equalise them.
    "sram_precharge": (
        ["BL", "BLB", "PCHB", "VDD"],
        [("MP1", "pch_p", "BL", "PCHB", "VDD", "VDD"),
         ("MP2", "pch_p", "BLB", "PCHB", "VDD", "VDD"),
         ("MEQ", "pch_eq", "BL", "PCHB", "BLB", "VDD")]),
    # Per physical column: NMOS pass pair onto the shared sense bitlines.
    "sram_colmux": (
        ["BL", "BLB", "SBL", "SBLB", "SEL", "VSS"],
        [("MN1", "cmux_n", "SBL", "SEL", "BL", "VSS"),
         ("MN2", "cmux_n", "SBLB", "SEL", "BLB", "VSS")]),
    # Per bit: isolated cross-coupled latch with tail enable; DOUT follows SBL.
    "sram_senseamp": (
        ["SBL", "SBLB", "SAE", "SAEB", "DOUT", "VDD", "VSS"],
        [("MIL", "sa_iso", "SAN", "SAEB", "SBL", "VSS"),
         ("MIR", "sa_iso", "SANB", "SAEB", "SBLB", "VSS"),
         ("MPL", "sa_p", "SAN", "SANB", "VDD", "VDD"),
         ("MPR", "sa_p", "SANB", "SAN", "VDD", "VDD"),
         ("MNL", "sa_n", "SAN", "SANB", "TAIL", "VSS"),
         ("MNR", "sa_n", "SANB", "SAN", "TAIL", "VSS"),
         ("MT", "sa_tail", "TAIL", "SAE", "VSS", "VSS"),
         ("MOP", "sa_out_p", "DOUT", "SANB", "VDD", "VDD"),
         ("MON", "sa_out_n", "DOUT", "SANB", "VSS", "VSS")]),
    # Per bit: pull the sense bitline for the 0 side low while WEN is high.
    "sram_wdrv": (
        ["SBL", "SBLB", "DIN", "WEN", "VDD", "VSS"],
        [("MIP", "wd_inv_p", "DINB", "DIN", "VDD", "VDD"),
         ("MIN", "wd_inv_n", "DINB", "DIN", "VSS", "VSS"),
         ("MW1", "wd_n", "SBL", "DINB", "X1", "VSS"),
         ("MW2", "wd_n", "X1", "WEN", "VSS", "VSS"),
         ("MW3", "wd_n", "SBLB", "DIN", "X2", "VSS"),
         ("MW4", "wd_n", "X2", "WEN", "VSS", "VSS")]),
}


def device(role):
    """Return (model, w, l) for a sizing role."""
    r = SIZING[role]
    assert r["model"] in MODELS, role
    return r["model"], r["w"], r["l"]


def logical_lines(text):
    """Netlist text with `+` continuation lines joined and blank lines dropped."""
    out = []
    for line in text.splitlines():
        if line.startswith("+") and out:
            out[-1] += " " + line[1:].strip()
        elif line.strip():
            out.append(line.rstrip())
    return out


def normalise_netlist(text):
    """Canonical logical form of a `klt netlist --block` output: the absolute
    `sch_path` line is dropped (it names the machine) and continuations joined."""
    return [ln for ln in logical_lines(text) if not ln.startswith("** sch_path")]
