"""SRAM compiler entry point: (words, bits, mux) -> macro SPICE netlist.

Usage:
  python3 -I design/compiler/sram_compile.py WORDS BITS MUX [-o FILE | --check FILE]

Every size goes through generate(); there is no per-instance code. The output is
deterministic (no timestamps, no absolute paths) and self-contained: the bitcell
and periphery subckt bodies (from the committed netlists) followed by the macro
subckt. Pure Python, no PDK or xschem needed.

Architecture: rows = words/mux, cols = bits*mux, physical column c = bit*mux + m.
Address A0..A(nc-1) selects the column (nc = log2 mux), the rest the row. Row
decode = grouped predecode (groups of <=3 bits, WLEN gating group 0) -> NAND of
the group lines -> wordline driver. Column mux = NMOS pass pairs onto per-bit
sense bitlines, with a per-bit sense amp and write driver. See README.md.
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # -I drops the script dir
import cells  # noqa: E402

here = pathlib.Path(__file__).resolve().parent
root = here.parent.parent

# README target table (Compiler range). Ratification changes these, not the tests.
WORDS = (16, 1024)
BITS = (8, 64)
MUXES = (1, 2, 4, 8)
BITCELL_NETLIST = root / "design/bitcell/netlist/bitcell_6t.spice"


class RangeError(ValueError):
    pass


def validate(words, bits, mux):
    for name, v in (("words", words), ("bits", bits), ("mux", mux)):
        if not isinstance(v, int) or isinstance(v, bool):
            raise RangeError(f"{name} must be an integer, got {v!r}")
    if not WORDS[0] <= words <= WORDS[1] or words & (words - 1):
        raise RangeError(f"words={words}: must be a power of two in {WORDS[0]}..{WORDS[1]}")
    if not BITS[0] <= bits <= BITS[1]:
        raise RangeError(f"bits={bits}: must be in {BITS[0]}..{BITS[1]}")
    if mux not in MUXES:
        raise RangeError(f"mux={mux}: must be one of {MUXES}")
    if words // mux < 2:
        raise RangeError(f"words={words} mux={mux}: needs at least 2 rows")


def top_name(words, bits, mux):
    return f"sram_{words}x{bits}_m{mux}"


def geometry(words, bits, mux):
    validate(words, bits, mux)
    nc = mux.bit_length() - 1
    nr = (words // mux).bit_length() - 1
    return {"rows": words // mux, "cols": bits * mux, "nc": nc, "nr": nr,
            "na": nc + nr}


def top_ports(words, bits, mux):
    g = geometry(words, bits, mux)
    return ([f"A{i}" for i in range(g["na"])] + [f"D{b}" for b in range(bits)]
            + [f"Q{b}" for b in range(bits)] + ["WLEN", "PCHB", "SAE", "WEN", "VDD", "VSS"])


def _groups(nr):
    """Split nr row bits into balanced predecode groups of at most 3 bits."""
    n = -(-nr // 3)
    sizes = [nr // n + (1 if i < nr % n else 0) for i in range(n)]
    out, lo = [], 0
    for s in sizes:
        out.append((lo, s))
        lo += s
    return out


class _Body:
    def __init__(self):
        self.lines = []
        self.n = 0

    def inst(self, cell, nets):
        self.n += 1
        self.lines.append(f"X{self.n}_{cell[5:]} {' '.join(nets)} {cell}")


def _line(body, ins, out):
    """Active-high line = AND(ins): NAND(k) (inverter if k==1) then inverter."""
    k = len(ins)
    nb = f"{out}_b"
    if k == 1:
        body.inst("sram_inv", [ins[0], nb, "VDD", "VSS"])
    else:
        body.inst(f"sram_nand{k}", ins + [nb, "VDD", "VSS"])
    body.inst("sram_inv", [nb, out, "VDD", "VSS"])


def macro_body(words, bits, mux):
    g = geometry(words, bits, mux)
    rows, cols, nc, nr = g["rows"], g["cols"], g["nc"], g["nr"]
    b = _Body()
    abits = [f"A{i}" for i in range(g["na"])]
    for a in abits:
        b.inst("sram_inv", [a, f"{a}B", "VDD", "VSS"])
    b.inst("sram_inv", ["SAE", "SAEB", "VDD", "VSS"])

    def sel(i, v):  # net for address bit i being v
        return abits[i] if v else f"{abits[i]}B"

    # column select lines CS<m>
    if nc:
        for m in range(mux):
            _line(b, [sel(j, (m >> j) & 1) for j in range(nc)], f"CS{m}")
    # row predecode lines PD<g>_<v>, WLEN gating group 0
    groups = _groups(nr)
    for gi, (lo, size) in enumerate(groups):
        for v in range(1 << size):
            ins = [sel(nc + lo + j, (v >> j) & 1) for j in range(size)]
            if gi == 0:
                ins.append("WLEN")
            _line(b, ins, f"PD{gi}_{v}")
    # final row gate + wordline driver
    for r in range(rows):
        lines = [f"PD{gi}_{(r >> lo) & ((1 << size) - 1)}" for gi, (lo, size) in enumerate(groups)]
        if len(lines) == 1:
            b.inst("sram_inv", [lines[0], f"RWLB{r}", "VDD", "VSS"])
        else:
            b.inst(f"sram_nand{len(lines)}", lines + [f"RWLB{r}", "VDD", "VSS"])
        b.inst("sram_wldrv", [f"RWLB{r}", f"WL{r}", "VDD", "VSS"])
    # array
    for r in range(rows):
        for c in range(cols):
            b.lines.append(f"XC{r}_{c} BL{c} BLB{c} WL{r} VDD VSS bitcell_6t")
    # per-column precharge and column mux
    for c in range(cols):
        b.inst("sram_precharge", [f"BL{c}", f"BLB{c}", "PCHB", "VDD"])
    for c in range(cols):
        s = f"CS{c % mux}" if mux > 1 else "VDD"
        b.inst("sram_colmux", [f"BL{c}", f"BLB{c}", f"SBL{c // mux}", f"SBLB{c // mux}", s, "VSS"])
    # per-bit sense amp and write driver
    for k in range(bits):
        b.inst("sram_senseamp", [f"SBL{k}", f"SBLB{k}", "SAE", "SAEB", f"Q{k}", "VDD", "VSS"])
        b.inst("sram_wdrv", [f"SBL{k}", f"SBLB{k}", f"D{k}", "WEN", "VDD", "VSS"])
    return b.lines


def _wrap(line, width=100):
    """Wrap a long instance line with `+` continuations (same as klt netlist)."""
    toks, out, cur = line.split(), [], ""
    for t in toks:
        if cur and len(cur) + 1 + len(t) > width:
            out.append(cur)
            cur = "+ " + t
        else:
            cur = f"{cur} {t}" if cur else t
    out.append(cur)
    return out


def generate(words, bits, mux):
    validate(words, bits, mux)
    g = geometry(words, bits, mux)
    name = top_name(words, bits, mux)
    out = [f"** {name}: words={words} bits={bits} mux={mux} rows={g['rows']} cols={g['cols']}",
           "** generated by design/compiler/sram_compile.py; do not edit by hand"]
    srcs = [BITCELL_NETLIST] + [here / "netlist" / f"{n}.spice" for n in sorted(cells.CELLS)]
    for s in srcs:
        out += cells.normalise_netlist(s.read_text())
    out.append(f".subckt {name} {' '.join(top_ports(words, bits, mux))}")
    for ln in macro_body(words, bits, mux):
        out += _wrap(ln)
    out.append(".ends")
    return "\n".join(out) + "\n"


def main(argv):
    args = argv[1:]
    mode, target = None, None
    if "-o" in args:
        i = args.index("-o"); mode, target = "write", args[i + 1]; del args[i:i + 2]
    elif "--check" in args:
        i = args.index("--check"); mode, target = "check", args[i + 1]; del args[i:i + 2]
    if len(args) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        text = generate(*(int(a) for a in args))
    except (RangeError, ValueError) as e:
        print(f"sram_compile: error: {e}", file=sys.stderr)
        return 1
    if mode == "write":
        pathlib.Path(target).write_text(text)
    elif mode == "check":
        p = pathlib.Path(target)
        if not p.exists() or p.read_text() != text:
            print(f"sram_compile: {target} drifted from the generator", file=sys.stderr)
            return 3
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
