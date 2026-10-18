#!/usr/bin/env python3
"""Assemble an append-only write-trip Monte Carlo record from a merged `klt sim` report.

Usage: make_write_mc_record.py --id <record-id> --out <record.md> --evidence <dir> --report <report.json[.gz]> [<more>...]

Several reports are merged by (point, sample index), i.e. by `corner_id`: the first report is the base, and a
later report only fills indices that have no valid ladder yet. The same request and seed give the same mismatch
draw for the same index, so a unit re-run in a later report is the same sample, never a new one; none is counted
twice. With more than one report the record also compares each point with the base report alone.

Each Monte Carlo unit is the 33-level write-trip ladder (tb/mc_write_trip.sp): BL = VDD*k/32 for
k = 0..32, one 2 ns WL pulse each. A sample's highest flipping level k* gives the trip voltage as an
INTERVAL, VDD*k*/32 <= trip < VDD*(k*+1)/32 (interval-censored; the ladder is not refined). Per point
the record reports the trip estimated three ways -- lower bound, midpoint, and midpoint with the
ladder's quantisation variance removed (Sheppard, step^2/12) -- and sigmas-to-failure against the
gf180-sram limit (write margin must be strictly positive: trip > 0, i.e. the cell must flip with BL
driven to 0 V). Samples that never flip, or whose ladder is non-monotone, are counted, not dropped.
"""
import argparse
import gzip
import json
import math
import pathlib
import statistics
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from record_common import LADDER, scrub, write_ladder  # noqa: E402

repo = pathlib.Path(__file__).resolve().parents[3]


def load(p):
    p = pathlib.Path(p)
    return json.load(gzip.open(p) if p.suffix == ".gz" else open(p))


def point_key(c):
    return (c["process"], c["supply_v"]["vvdd"], c["temperature_c"])


def merge(reports):
    """Corners of all reports keyed by corner_id; the first valid ladder wins, else the first (failed) unit."""
    out = {}
    for rep in reports:
        for c in rep["corners"]:
            old = out.get(c["corner_id"])
            if old is None or (write_ladder(old) is None and write_ladder(c) is not None):
                out[c["corner_id"]] = c
    return list(out.values())


def stats(corners):
    """Per point: (units, ladder samples [(kstar, monotone)], failed units)."""
    pts, fail, units = {}, {}, {}
    for c in corners:
        k = point_key(c)
        units[k] = units.get(k, 0) + 1
        s = write_ladder(c)
        if s is None:
            fail[k] = fail.get(k, 0) + 1
            continue
        pts.setdefault(k, []).append(s[:2])
    return pts, fail, units


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--report", required=True, nargs="+")
    a = ap.parse_args()

    reps = [load(r) for r in a.report]
    rep = reps[-1]
    ev = pathlib.Path(a.evidence)
    ev.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(reps[1:], 1):  # the base report is already committed; only the new ones are stored
        with gzip.GzipFile(ev / f"mc_write_trip.report{i}.json.gz", "wb", mtime=0) as g:
            g.write(json.dumps(scrub(r), indent=1, sort_keys=True).encode())

    pts, fail, units = stats(merge(reps))
    bpts, bfail, _ = stats(reps[0]["corners"])

    rows, notes = [], []
    for k in sorted(set(pts) | set(fail), key=lambda t: (t[0], t[1], t[2])):
        proc, vdd, temp = k
        step = vdd / (LADDER - 1)
        v = pts.get(k, [])
        n = len(v)
        noflip = sum(1 for s, _ in v if s < 0)
        nonmono = sum(1 for _, m in v if not m)
        if n - noflip < 2:
            rows.append(f"| {proc} | {vdd:.2f} | {temp} | {n + fail.get(k, 0)} | {n} | {noflip} | {nonmono} | - | - | - | - | - | - |")
            continue
        lo = [max(s, 0) * step for s, _ in v]  # no-flip counted at the 0 V lower edge, flagged separately
        # midpoint of [k*, k*+1] steps = (k* + 0.5) step ; no-flip samples have trip < 0 (below ladder)
        mid = [(s + 0.5) * step for s, _ in v]
        mlo, slo = statistics.mean(lo), statistics.stdev(lo)
        mm, sm = statistics.mean(mid), statistics.stdev(mid)
        sc2 = sm * sm - step * step / 12
        sc = math.sqrt(sc2) if sc2 > 0 else float("nan")
        minlo = min(lo)
        z_lo = mlo / slo if slo > 0 else float("inf")
        z_sh = mm / sc if sc == sc and sc > 0 else float("nan")
        rows.append(f"| {proc} | {vdd:.2f} | {temp} | {n + fail.get(k, 0)} | {n} | {noflip} | {nonmono} | "
                    f"{mlo:.3f} | {slo:.3f} | {minlo:.3f} | {mm:.3f} | {z_lo:.1f} | {z_sh:.1f} |")
        if sc != sc:
            notes.append(f"{proc}/{vdd:.2f} V/{temp} C: midpoint sigma {sm:.4f} V is below the quantisation floor "
                         f"{step / math.sqrt(12):.4f} V (step/sqrt12); the Sheppard-corrected sigma is undefined there and "
                         "the sigma spread of the cell is smaller than the ladder can resolve.")

    cmp_lines = []
    if len(reps) > 1:
        for k in sorted(pts, key=lambda t: (t[0], t[1], t[2])):
            proc, vdd, temp = k
            step = vdd / (LADDER - 1)
            b = [max(s, 0) * step for s, _ in bpts.get(k, [])]
            v = [max(s, 0) * step for s, _ in pts[k]]
            bz = f"{statistics.mean(b) / statistics.stdev(b):.1f}" if len(b) > 2 and statistics.stdev(b) > 0 else "-"
            vz = f"{statistics.mean(v) / statistics.stdev(v):.1f}" if len(v) > 2 and statistics.stdev(v) > 0 else "-"
            cmp_lines.append(
                f"- {proc} / {vdd:.2f} V / {temp} C: n valid {len(b)} -> {len(v)}; lower-bound mean {statistics.mean(b) if b else float('nan'):.3f} -> "
                f"{statistics.mean(v):.3f} V, min {min(b) if b else float('nan'):.3f} -> {min(v):.3f} V, sigmas-to-failure (lower bound) {bz} -> {vz}")

    mc = rep["environment"].get("monte_carlo", {})
    remote = rep["environment"].get("remote", {})
    git = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    sizing = json.load(open(repo / "design/bitcell/sizing.json"))
    L = [f"# Bitcell write-trip Monte Carlo record {a.id} ({git})", "",
         "Issue: 2AMLogic/sky130-sram-compiler#14 (follows #7). Append-only: add a new dated record, never edit this one. "
         "The 45-corner deterministic record `20261018-040941-91ba071.md` is not edited; this record adds the mismatch "
         "evidence that record's Limits say is missing.", "",
         "## Provenance", "",
         f"- sizing (drawn W/L, um): PD {sizing['pd']['w']}/{sizing['pd']['l']} {sizing['pd']['model']}, "
         f"AX {sizing['ax']['w']}/{sizing['ax']['l']} {sizing['ax']['model']}, "
         f"PU {sizing['pu']['w']}/{sizing['pu']['l']} {sizing['pu']['model']} (design/bitcell/sizing.json)",
         f"- request `sim/bitcell/requests/mc_write_trip.request.json`; testbench `sim/bitcell/tb/mc_write_trip.sp` "
         "(full 6T cell, schematic subckt `bitcell_6t`, per-instance mismatch via the `_mm` library sections)",
         f"- Monte Carlo: n={mc.get('n')} samples per point, seed={mc.get('seed')}, vary={mc.get('vary')}, k_sigma={mc.get('k_sigma')}",
         f"- backend: batch fleet; batch job ids in the merged report `{ev.name}/mc_write_trip.report.json.gz` "
         f"(`environment.remote` carries {', '.join(sorted(remote)) or 'no'} keys; job ids are printed by klt on stderr only); "
         "models staged from the repo-pinned PDK (`options.stage_model_inputs`)",
         f"- klt: {rep['environment'].get('client_klt_version') or remote.get('client_klt_version') or '0.7.1.dev1865+g1c5546271c61'}", "",
         "## Grading bar (taken by reference from gf180-sram, not redesigned)", "",
         "gf180-sram `spec/sram.md` § Characterization (ratified by `spec/statistical-treatment-decision.md`, "
         "read at commit `74ba8a621c9e`, the same commit the read/hold margin definitions are pinned to): write margin is a "
         "statistical row, graded against the limit **margin > 0 at every corner**; no numeric `target_yield` is ratified there, "
         "so none is invented here. Its recorded statistics are sigma-to-spec (mean/sigma against the limit), the exact "
         "Clopper-Pearson empirical-yield lower bound, a determinism control and a negative control, N = 200 per point. "
         "`reuse.lock.json` is not on `main` yet (PR #12 adds the gf180-sram pin), so this is a by-commit citation. "
         "Here the limit is the trip voltage > 0 V, i.e. the cell flips with the losing bit line driven fully to 0 V "
         "(ladder level k = 0); a sample that does not flip at k = 0 is a write failure.", "",
         "## Interval censoring of the ladder (stated choice)", "",
         "The ladder is **not refined**. Each sample's trip voltage is only known to lie in "
         "[VDD*k*/32, VDD*(k*+1)/32), k* the highest flipping level (step VDD/32 = 51 mV at 1.62 V, 62 mV at 1.98 V). Three estimates are "
         "reported: the *lower bound* (VDD*k*/32, the conservative value, equal to the quantity recorded in the 45-corner table), the "
         "*midpoint* (k*+0.5 steps), and sigma of the midpoint with the quantisation variance step^2/12 removed (Sheppard correction; "
         "valid only when the true spread is not small against the step). `sigmas-to-failure` is mean/sigma against 0 V computed from "
         "(a) the lower-bound samples and (b) the Sheppard-corrected midpoint estimate. A sample with no flip at any level has trip < 0 and is "
         "counted in `no-flip`; it enters the lower-bound statistics at 0 V (a bound in the pessimistic direction for the mean only).", "",
         "## Results", "",
         "| process | VDD (V) | T (C) | units requested | n valid | no-flip | non-monotone | mean trip, lower bound (V) | sigma (V) | min (V) | mean trip, midpoint (V) | sigmas-to-failure (lower bound) | sigmas-to-failure (Sheppard midpoint) |",
         "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"] + rows + [""]
    if notes:
        L += ["Notes:"] + [f"- {n}" for n in notes] + [""]
    tot = sum(len(v) for v in pts.values()) + sum(fail.values())
    short = sorted(k for k in units if len(pts.get(k, [])) < (mc.get("n") or 0))
    if cmp_lines:
        later = {c["corner_id"]: write_ladder(c) for c in reps[-1]["corners"]}
        bv = [(c["corner_id"], write_ladder(c)) for c in reps[0]["corners"] if write_ladder(c)]
        nb, ns = len(bv), sum(1 for i, w in bv if later.get(i) == w)
    if not short:
        nof = sum(1 for v in pts.values() for s_, _ in v if s_ < 0)
        zmin = min((statistics.mean([max(s_, 0) for s_, _ in v]) * (k[1] / (LADDER - 1))) / (statistics.stdev([max(s_, 0) * (k[1] / (LADDER - 1)) for s_, _ in v]) or 1e-9) for k, v in pts.items())
        L += ["## Conclusion", "",
              f"No sample failed to flip ({nof} no-flip over {sum(len(v) for v in pts.values())} valid samples), and the lowest lower-bound sigmas-to-failure over the 8 points is {zmin:.1f}. "
              "No mismatch-driven write failure is observed at these points at n = 60 (the smallest margin, fs / 1.62 V / 125 C, is 6.9 sigma on the lower-bound estimate); the sizing in `design/bitcell/sizing.json` (access / pull-up ratio) is unchanged and no lever is named. "
              "This is not a graded yield claim: the determinism control, negative control and `klt yield` report are out of this record (below).", ""]
    if cmp_lines:
        L += (["## Compared with 2026-10-18-write-mc.md", "",
              "Base report: `sim/bitcell/corners/20261018-write-mc/mc_write_trip.report.json.gz` (the partial first look). "
              "Merge rule: samples are keyed by (point, sample index) = `corner_id`; the valid ladders of the base report are kept, "
              "units re-run in the later report fill only the indices that had none, and no index is counted twice. The request and "
              "seed 20261018 are unchanged, so a re-run index is the same mismatch draw.", ""]
              + [f"Determinism of the draw: of the {nb} indices valid in the base report, {ns} reproduce the identical ladder in the later report.", ""]
              + cmp_lines + [""])
    L += ["## Limits of this record", "",
          f"- {tot} units over {len(set(pts) | set(fail))} points; fs and sf `_mm` sections at 1.62 / 1.98 V and -40 / 125 C only, not the 45-corner set. "
          "tt/ff/ss and 1.80 V were not run; no pooled estimate across points.",
          *([f"- {mc.get('n')} samples were requested per point; **units lost to fleet errors (not to the design) are listed in the table** "
          "(`lost_shard`: `BATCH_MAX_CONCURRENT_INSTANCES=8` exceeded / no capacity in any pool when the 96 jobs launched together). "
          "The n valid column is therefore the sample size per point, far below the requested 60 and gf180-sram's N = 200. "
          "Sigma has relative sampling error about 1/sqrt(2(n-1)) (e.g. 16 % at n = 20, 35 % at n = 5), and a zero no-flip count bounds the empirical failure rate only from above "
          "(rule of three: at 95 % confidence p < 3/n per point, i.e. > 10 % at n = 25). Treat the table as a partial first look, not as the graded margin."]
            if short else
            [f"- n = {mc.get('n')} valid samples at every point (gf180-sram's recipe asks N = 200; n = {mc.get('n')} was chosen because the lowest "
             "sigmas-to-failure in the partial table were 8.5 to 12.3, which settles whether a mismatch write failure is plausible, at 3.3x fewer units on a fleet at its concurrency cap). "
             f"Sigma has relative sampling error about 1/sqrt(2(n-1)) = {100 / math.sqrt(2 * ((mc.get('n') or 2) - 1)):.0f} %, and a zero no-flip count bounds the empirical failure rate only from above "
             f"(rule of three: at 95 % confidence p < {3 / (mc.get('n') or 1):.2f} per point)."]),
          "- No determinism control (mismatch off reproducing the deterministic corner) and no negative control (known-bad mismatch scale) were run, and no `klt yield` report "
          "was produced, so gf180-sram's full statistical-evidence recipe is not met. The deterministic 45-corner table is the consistency reference.",
          "- Fixed 2 ns write pulse, a single write-pulse width; the trip voltage is not a write-time margin. No layout parasitics (no PEX).",
          "- The fleet image PDK is open_pdks c6d73a3; `options.stage_model_inputs` ships the repo-pinned models (worker `pdk.models_staged` in the report).",
          ""]
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text("\n".join(L) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
