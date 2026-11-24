#!/usr/bin/env python3
"""PDK-free tests for check_probe.py's requested-names completeness check (synthetic single-corner reports)."""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECK = os.path.join(HERE, "check_probe.py")
REQ = os.path.join(HERE, "..", "requests")


def names(bench):
    return [x["name"] for x in json.load(open(os.path.join(REQ, f"{bench}.probe.request.json")))["measurements"]]


def run(bench, values):
    rep = {"status": "pass", "corners": [{"supply_v": {"vvdd": 1.8},
                                          "measurements": [{"name": k, "value": v} for k, v in values.items()]}]}
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "r.json")
        json.dump(rep, open(p, "w"))
        c = subprocess.run([sys.executable, "-I", CHECK, bench, p], capture_output=True, text=True)
    return c.returncode, c.stdout + c.stderr


def main():
    ns = names("col_write0_nowen")
    good = {k: 1.8 for k in ns if k.startswith("q")}
    good.update({k: 1.8 for k in ns if k not in good})
    rc, out = run("col_write0_nowen", good)
    assert rc == 0, out
    for drop in [k for k in ns if k.startswith("q")] + ["hs1", "hs2"]:
        rc, out = run("col_write0_nowen", {k: v for k, v in good.items() if k != drop})
        assert rc != 0 and drop in out, (drop, rc, out)
    rc, out = run("col_write0_nowen", {k: v for k, v in good.items() if not k.startswith("q")})
    assert rc != 0, out                      # empty Q list must not pass
    flipped = dict(good, q05=0.0)
    assert run("col_write0_nowen", flipped)[0] != 0
    for bench in ("col_read0", "col_read1", "col_write0", "col_write1"):
        n = names(bench)
        rc, out = run(bench, {k: 0.9 for k in n[1:]})   # first requested sample absent
        assert rc != 0 and n[0] in out, (bench, out)
    print("test_check_probe: OK")


main()
