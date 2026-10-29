#!/usr/bin/env python3
"""Assert that a single-corner (tt, 1.8 V, 25 C) probe report shows the behaviour its bench exists to detect.

Usage: check_probe.py <bench> <klt-sim-report.json>
A probe that merely ran proves little: each ladder bench must show BOTH a failing and a passing end (so a
broken stimulus that makes every trial pass or fail is caught), and the negative control must never flip.
Exit 0 = as expected, 1 = not.
"""
import json
import sys

bench, path = sys.argv[1], sys.argv[2]
r = json.load(open(path))
if r["status"] != "pass" or len(r["corners"]) != 1:
    sys.exit(f"check_probe: {bench}: klt sim status {r['status']!r}, {len(r['corners'])} corner(s)")
c = r["corners"][0]
vdd = c["supply_v"]["vvdd"]
m = {x["name"]: x["value"] for x in c["measurements"]}
if any(v is None for v in m.values()):
    sys.exit(f"check_probe: {bench}: measurement(s) without value: {[k for k, v in m.items() if v is None]}")


def ladder(prefix):
    return [m[k] for k in sorted(m) if k.startswith(prefix) and k[len(prefix):].isdigit()]


ok, why = True, ""
if bench in ("col_read0", "col_read1"):
    want = 1 if bench.endswith("1") else 0
    dout = [int(v > vdd / 2) for v in ladder("dout")]
    q = [int(v > vdd / 2) for v in ladder("q")]
    right = [d == want for d in dout]
    if not right[-1] or not all(right[len(right) // 2:]):
        ok, why = False, "the long-SAE-delay half of the ladder does not read the stored value"
    if bench.endswith("1") and right[0]:
        ok, why = False, "read-1 with SAE at WL (delay 0) reads correctly: the ladder has no failing end"
    if any(x != want for x in q):
        ok, why = False, "a read changed the stored value"
    dv = ladder("dv")
    if (dv[-1] > 0) != (want == 1):   # SBL - SBLB: positive when a 1 is read (BLB discharges)
        ok, why = False, f"differential sign at the long delay is wrong ({dv[-1]:.3f} V)"
elif bench in ("col_write0", "col_write1", "col_write0_nowen"):
    want = 0 if bench.startswith("col_write0") else 1
    q = [int(v > vdd / 2) for v in ladder("q")]
    if bench.endswith("nowen"):
        if any(x != 1 for x in q):
            ok, why = False, "negative control: the cell flipped with WEN never asserted"
    else:
        if q[0] == want:
            ok, why = False, "the shortest write pulse already flips the cell: no failing end"
        if not all(x == want for x in q[-3:]):
            ok, why = False, "the longest write pulses do not write the cell"
elif bench in ("col_read_snm", "col_hold_snm"):
    v = m["vtrip"]
    if not 0.2 < v < 0.7:
        ok, why = False, f"half-cell trip point {v:.3f} V is implausible"
else:
    sys.exit(f"check_probe: unknown bench {bench}")
if "hs1" in m and not (m["hs1"] > 0.8 * vdd or m["hs1"] < 0.2 * vdd) :
    ok, why = False, "half-selected cell left a rail"
print(f"check_probe: {bench}: {'OK' if ok else 'FAIL: ' + why}")
sys.exit(0 if ok else 1)
