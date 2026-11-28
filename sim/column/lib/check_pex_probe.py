#!/usr/bin/env python3
"""Run the ladder checks of check_probe.py on EACH leg of a `klt pex` report.

Usage: check_pex_probe.py <bench> <klt-pex-report.json> [request.json]

`klt pex` reports per-corner values only inside delta[] rows (schematic_value /
extracted_value), so this rebuilds the klt-sim-shaped report each check_probe.py
invocation expects -- one per side -- from the envelope itself and runs the very
same checks on both: the schematic leg must show the bench behaviour on the
pre-layout netlist, the extracted leg on the parasitic-annotated one. Exit 0 =
both legs as expected; 1 = not (either leg, named); 2 = the report does not carry
the per-side evidence (nothing simulated, or no delta rows for the bench).

Per-side execution is confirmed from the report's own testbenches[].sides blocks
(produced_value, diagnostics), never from a wrapper's summary line (#219 caveat).
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


def leg_report(r, bench, side, vdd):
    """A klt-sim-shaped report for one side, or an error string."""
    tb = next((t for t in r["testbenches"]
               if os.path.basename(t["request"]["path"]).startswith(f"{bench}.")), None)
    if tb is None:
        return None, f"no testbench matching {bench} in the report"
    s = (tb.get("sides") or {}).get(side)
    if s is None:
        return None, f"the {side} side was never simulated"
    bad = [c for c in s["corners"] if not c["produced_value"]]
    if len(s["corners"]) != 1 or bad:
        return None, (f"the {side} side has {len(s['corners'])} corner(s), "
                      f"{len(bad)} without a produced value")
    corner_id = s["corners"][0]["corner_id"]
    # with several testbenches in one report, spec_row carries the request stem as a
    # prefix ("col_read0.probe.request.dout00"); a single-testbench report uses bare names
    stem = os.path.basename(tb["request"]["path"])[:-len(".json")]
    pref = stem + "."
    values = {}
    for row in r["delta"]:
        if row["corner_id"] != corner_id:
            continue
        name = row["spec_row"]
        if name.startswith(pref):
            name = name[len(pref):]
        elif any(x["spec_row"].startswith(pref) for x in r["delta"]):
            continue            # this report prefixes rows: only prefixed ones are ours
        v = row.get(f"{side}_value")
        if v is not None:
            values[name] = v
    if not values:
        return None, f"no {side} delta values for {bench} at {corner_id}"
    return {"status": "pass", "corners": [{"supply_v": {"vvdd": vdd},
                                           "measurements": [{"name": k, "value": v}
                                                            for k, v in sorted(values.items())]}]}, None


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    bench, path = sys.argv[1], sys.argv[2]
    req_path = sys.argv[3] if len(sys.argv) > 3 else os.path.join(
        HERE, "..", "requests", "pex", f"{bench}.probe.request.json")
    vdd = json.load(open(req_path))["corners"]["supply_v"]["vvdd"][0]
    r = json.load(open(path))
    rc = 0
    with tempfile.TemporaryDirectory() as tmp:
        for side in ("schematic", "extracted"):
            rep, err = leg_report(r, bench, side, vdd)
            if rep is None:
                print(f"check_pex_probe: {bench}: {err}")
                rc = 1
                continue
            p = os.path.join(tmp, f"{side}.json")
            with open(p, "w") as f:
                json.dump(rep, f)
            out = subprocess.run([sys.executable, "-I", os.path.join(HERE, "check_probe.py"),
                                  bench, p, req_path], capture_output=True, text=True)
            # check_probe.py reports ladder verdicts on stdout but structural refusals
            # (sys.exit(msg)) on stderr; surface both, or the missing-sample name is lost
            msg = "\n".join(x for x in (out.stdout.strip(), out.stderr.strip()) if x)
            print(f"[{side}] " + msg)
            if out.returncode != 0:
                rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
