#!/usr/bin/env python3
"""Run the cocotb bench for sram_ctrl with Icarus Verilog.

Usage: python3 -I rtl/tb/cocotb/run.py {rtl|synth|mutants|both}   (default: both = rtl + synth + mutants)
  rtl    DUT = rtl/sram_ctrl.v (parameterised; WORDS/BITS from SRAM_WORDS/SRAM_BITS, default 256 x 32)
  synth  DUT = rtl/synth/sram_ctrl_256x32_synth.v with the pinned sky130_fd_sc_hd Verilog models
  mutants negative control: three seeded faults in a scratch copy of sram_ctrl.v; each must FAIL the bench
Needs cocotb and iverilog; rtl/tb/cocotb/run.sh creates the venv and calls this. Exit 1 on any failure.
"""
import os
import pathlib
import sys

from cocotb_tools.runner import get_runner

here = pathlib.Path(__file__).resolve().parent
root = here.parents[2]
build = root / "sim/build/cocotb"


# Seeded faults (negative control): (name, original text, faulty text). Each must turn the bench red.
MUTANTS = [
    ("dout_inverted", "if (!we_q) dout <= sa_q;", "if (!we_q) dout <= ~sa_q;"),
    ("wen_on_read", "wen    <= we;", "wen    <= 1'b1;"),
    ("sae_during_write", "sae <= ~we_q;", "sae <= 1'b1;"),
]


def mutant_source(name, old, new):
    text = (root / "rtl/sram_ctrl.v").read_text()
    if text.count(old) != 1:
        sys.exit(f"mutant {name}: pattern {old!r} not found exactly once in rtl/sram_ctrl.v")
    out = build / "mutants" / f"sram_ctrl_{name}.v"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text.replace(old, new))
    return out


def run(target, ctrl_src=None):
    words = int(os.environ.get("SRAM_WORDS", "256"))
    bits = int(os.environ.get("SRAM_BITS", "32"))
    srcs, args = [], ["-g2005-sv", "-Wno-timescale"]
    if target == "rtl":
        srcs += [ctrl_src or root / "rtl/sram_ctrl.v"]
        params = {"WORDS": words, "BITS": bits}
    else:
        if (words, bits) != (256, 32):
            sys.exit("synth netlist is the 256 x 32 instance only")
        pdk = os.environ.get("SKY130_VARIANT_DIR")
        if not pdk:
            sys.exit("SKY130_VARIANT_DIR unset: source sim/env.sh first")
        lib = pathlib.Path(pdk) / "libs.ref/sky130_fd_sc_hd/verilog"
        srcs += [lib / "primitives.v", lib / "sky130_fd_sc_hd.v", root / "rtl/synth/sram_ctrl_256x32_synth.v"]
        args += ["-DFUNCTIONAL", "-DUNIT_DELAY=#0", "-DSYNTH_NETLIST"]
        params = {"WORDS": 256, "BITS": 32}
    srcs += [root / "rtl/sram_behav.v", here / "tb_top.v"]
    runner = get_runner("icarus")
    bdir = build / (target if ctrl_src is None else f"mutant_{ctrl_src.stem}")
    runner.build(sources=srcs, hdl_toplevel="tb_top", build_dir=bdir,
                 build_args=args, parameters=params, always=True, timescale=("1ns", "1ps"))
    result = runner.test(hdl_toplevel="tb_top", test_module="test_sram_ctrl", test_dir=here,
                         build_dir=bdir, results_xml=bdir / "results.xml",
                         extra_env={"SRAM_WORDS": str(words), "SRAM_BITS": str(bits)})
    return result


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which not in ("rtl", "synth", "mutants", "both"):
        sys.exit(__doc__)
    from cocotb_tools.runner import get_results
    bad = 0
    for t in (["rtl", "synth"] if which == "both" else [which]) if which != "mutants" else []:
        tests, failed = get_results(run(t))
        print(f"run.py: {t}: {tests - failed}/{tests} tests passed")
        bad += failed
    if which in ("mutants", "both"):
        for name, old, new in MUTANTS:
            tests, failed = get_results(run("rtl", mutant_source(name, old, new)))
            caught = failed > 0
            print(f"run.py: mutant {name}: {'CAUGHT' if caught else 'MISSED'} ({failed}/{tests} tests failed)")
            bad += 0 if caught else 1
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
