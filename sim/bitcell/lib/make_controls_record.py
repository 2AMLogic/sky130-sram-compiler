#!/usr/bin/env python3
"""Assemble the append-only Monte Carlo controls record (issue #19) from collected `klt sim` runs.

Usage: make_controls_record.py --id <id> --out <record.md> --evidence <dir> --base-record <baseline.md>
         --base-reports <write-mc report> [<rerun>...] --det-ref <45-corner write report>
         --det <report> --neg <report>
         [--neg-read <artifacts-dir> <report> --neg-hold <artifacts-dir> <report>]

Also writes the n=60 baseline lower-bound trip voltages as a `klt yield` sample-set document next to the record
evidence and runs `klt yield` on it; if klt reports an error (e.g. the missing native extension), the record quotes it
and carries no yield numbers -- nothing is hand-computed in its place.

Detection criterion (fixed before any control result was read; applied per point, never tuned):
  a negative-control point is DETECTED as degraded iff
    (a) sigma(control) >= 2 x sigma(baseline)   AND
    (b) sigmas-to-failure(control) <= 0.5 x sigmas-to-failure(baseline),
  sigmas-to-failure = mean / sigma against the 0 limit (write: lower-bound trip voltage; read/hold: eye SNM).
  The mismatch sigma is scaled by NEG_SCALE, so (a) and (b) both expect a ratio of about NEG_SCALE; the 2x / 0.5x
  thresholds leave room for nonlinearity and the 9 % / 16 % sampling error of sigma at n = 60 / 20.
Determinism criterion: with mismatch switched off every sample at a point has the same highest flipping level k*,
and it equals k* of the matching deterministic (non-`_mm`) corner in the 45-corner write table.
"""
import argparse
import gzip
import json
import pathlib
import re
import statistics
import subprocess
import sys

here = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(here))
import make_record as mr  # noqa: E402
from make_tb import DET_N, NEG_N, NEG_SCALE, NEG_SEED  # noqa: E402
from make_write_mc_record import load, merge, point_key, stats  # noqa: E402
from record_common import LADDER, git_short_sha, klt_version_of, scrub, write_ladder  # noqa: E402

repo = here.parents[2]
SIGMA_RATIO_MIN = 2.0
Z_RATIO_MAX = 0.5


def lower_bounds(samples, step):
    """Lower-bound trip voltages; a no-flip sample (k* = -1) enters at 0 V, as in the baseline record."""
    return [max(k, 0) * step for k, _ in samples]


def mean_sigma(v):
    return statistics.mean(v), statistics.stdev(v)


def detected(base_sigma, base_z, ctl_sigma, ctl_z):
    return ctl_sigma >= SIGMA_RATIO_MIN * base_sigma and ctl_z <= Z_RATIO_MAX * base_z


def parse_base_snm(record):
    """{(section, point): (mean, sigma)} from the '### read SNM' / '### hold SNM' MC tables of a margin record."""
    out, sec = {}, None
    for line in pathlib.Path(record).read_text().splitlines():
        m = re.match(r"### (read|hold) SNM", line)
        if m:
            sec = m.group(1)
            continue
        if line.startswith("## "):
            sec = None
        cells = [c.strip() for c in line.strip("|").split("|")]
        if sec and len(cells) >= 5 and re.match(r"[a-z]{2}_mm_\dp\d+V_\d+C$", cells[0]):
            out[(sec, cells[0])] = (float(cells[3]), float(cells[4]))
    return out


def klt_version():
    r = subprocess.run(["klt", "--version"], capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()


def ref_kstar(det_ref):
    return {c["corner_id"]: write_ladder(c)[0] for c in det_ref["corners"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--base-record", required=True)
    ap.add_argument("--base-reports", required=True, nargs="+")
    ap.add_argument("--det-ref", required=True)
    ap.add_argument("--det", required=True)
    ap.add_argument("--neg", required=True)
    ap.add_argument("--job-log", nargs="*", default=[], metavar="NAME=KLT_STDERR_FILE",
                    help="klt stderr of each run; its `batch job <id> submitting` lines give the fleet job ids")
    ap.add_argument("--neg-read", nargs=2)
    ap.add_argument("--neg-hold", nargs=2)
    a = ap.parse_args()

    ev = pathlib.Path(a.evidence)
    ev.mkdir(parents=True, exist_ok=True)

    def keep(src, name):
        with gzip.GzipFile(ev / f"{name}.json.gz", "wb", mtime=0) as g:
            g.write(json.dumps(scrub(load(src)), indent=1, sort_keys=True).encode())

    keep(a.det, "mc_write_trip_det.report")
    keep(a.neg, "mc_write_trip_neg.report")
    extra = [("read", a.neg_read), ("hold", a.neg_hold)]
    for nm, x in extra:
        if x:
            keep(x[1], f"mc_{nm}_snm_neg.report")

    base_reps = [load(r) for r in a.base_reports]
    bpts, _, _ = stats(merge(base_reps))
    det_rep, neg_rep = load(a.det), load(a.neg)
    dpts, dfail, _ = stats(det_rep["corners"])
    npts, nfail, _ = stats(neg_rep["corners"])
    ref = ref_kstar(load(a.det_ref))

    # --- determinism
    drows, dok = [], True
    for k in sorted(bpts):
        proc, vdd, temp = k
        rid = f"{proc.replace('_mm', '')}/{vdd:.3f}V/{temp}C"
        ks = sorted(s for s, _ in dpts.get(k, []))
        same = bool(ks) and len(set(ks)) == 1 and ks[0] == ref.get(rid) and not dfail.get(k)
        dok &= same
        drows.append(f"| {proc} | {vdd:.2f} | {temp} | {len(ks) + dfail.get(k, 0)} | {ks} | {ref.get(rid)} | {'yes' if same else 'NO'} |")

    # --- write-trip negative control
    nrows, ndet = [], {}
    for k in sorted(bpts):
        proc, vdd, temp = k
        step = vdd / (LADDER - 1)
        b = lower_bounds(bpts[k], step)
        c = lower_bounds(npts.get(k, []), step)
        noflip = sum(1 for s, _ in npts.get(k, []) if s < 0)
        nonmono = sum(1 for _, m in npts.get(k, []) if not m)
        if len(c) < 3:
            nrows.append(f"| {proc} | {vdd:.2f} | {temp} | {len(c) + nfail.get(k, 0)} | - | - | - | - | - | - | - | NO (too few valid samples) |")
            ndet[k] = False
            continue
        bm, bs = mean_sigma(b)
        cm, cs = mean_sigma(c)
        bz, cz = bm / bs, (cm / cs if cs > 0 else float("inf"))
        d = detected(bs, bz, cs, cz)
        ndet[k] = d
        nrows.append(f"| {proc} | {vdd:.2f} | {temp} | {len(c) + nfail.get(k, 0)} | {len(c)} | {noflip} | {nonmono} | "
                     f"{bm:.3f} / {bs:.3f} | {cm:.3f} / {cs:.3f} | {bz:.1f} | {cz:.1f} | {'yes' if d else 'NO'} |")

    # --- read / hold negative control
    base_snm = parse_base_snm(a.base_record)
    snm_blocks, snm_det = [], {}
    for nm, x in extra:
        if not x:
            continue
        pts = mr.mc_stats(sorted(pathlib.Path(x[0]).glob("klt-sim-*")))  # one artifacts dir per batch job
        rows = ["| point | n | extract fail | baseline mean / sigma (V) | control mean / sigma (V) | baseline sigmas to 0 | control sigmas to 0 | control min (V) | detected |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
        for p, v in sorted(pts.items()):
            ok = [e for e, _ in v if e is not None]
            bm, bs = base_snm[(nm, p)]
            if len(ok) < 3:
                rows.append(f"| {p} | {len(v)} | {len(v) - len(ok)} | {bm:.4f} / {bs:.4f} | - | - | - | - | NO (too few valid samples) |")
                snm_det[(nm, p)] = False
                continue
            cm, cs = mean_sigma(ok)
            d = detected(bs, bm / bs, cs, cm / cs)
            snm_det[(nm, p)] = d
            rows.append(f"| {p} | {len(v)} | {len(v) - len(ok)} | {bm:.4f} / {bs:.4f} | {cm:.4f} / {cs:.4f} | {bm / bs:.1f} | {cm / cs:.1f} | "
                        f"{min(ok):.4f} | {'yes' if d else 'NO'} |")
        snm_blocks += [f"### {nm} SNM", ""] + rows + [""]

    # --- klt yield on the baseline: sample-set document (lower-bound trip V per point, limit trip > 0 V)
    ydoc = {"measurements": [
        {"name": f"write_trip_lb_V/{p}/{v:.2f}V/{t}C",
         "samples": [round(x, 6) if k >= 0 else -(v / (LADDER - 1)) for (k, _), x in
                     zip(bpts[(p, v, t)], lower_bounds(bpts[(p, v, t)], v / (LADDER - 1)))],
         "limits": {"min": 0.0}} for (p, v, t) in sorted(bpts)]}
    ypath = ev / "write_trip_baseline.samples.json"
    ypath.write_text(json.dumps(ydoc, indent=1) + "\n")
    yr = subprocess.run(["klt", "yield", str(ypath), "--format", "json"], capture_output=True, text=True)
    yout = {"error": {"message": (yr.stderr or yr.stdout).strip()[-400:]}}
    for txt in (yr.stdout, yr.stderr):  # klt writes its JSON envelope to either stream
        try:
            yout = json.loads(txt)
            break
        except ValueError:
            pass
    if "error" in yout:
        yield_note = (f"`klt yield` did not run: `{yout['error']['message']}` (klt `{klt_version()}`). No yield, interval or Cpk is "
                      "reported here and none is hand-computed in its place. Known gap: 2AMLogic/klayout-tools#2900 (the documented "
                      "`klayout-tools[yield]` install path does not resolve; `klt-yield-native` is not on the package index). "
                      f"The input is committed (`{ev.name}/{ypath.name}`: the {len(ydoc['measurements'])} points x "
                      f"{len(ydoc['measurements'][0]['samples'])} lower-bound trip voltages of the n=60 baseline, seed 20261018, limit min 0 V; "
                      "a no-flip sample would enter as -VDD/32; there are none) so the report can be produced where the extension is installed: "
                      f"`klt yield {ev.name}/{ypath.name} --format json`. Known related: klayout-tools#2909 (quantised sample sets, "
                      "relevant here because the ladder values take few distinct levels).")
    else:
        keep_yield = ev / "write_trip_baseline.yield.json"
        keep_yield.write_text(json.dumps(yout, indent=1) + "\n")
        yield_note = (f"`klt yield` (klt `{klt_version()}`) ran on `{ev.name}/{ypath.name}` (n=60 per point, seed 20261018, limit min 0 V); "
                      f"full output in `{ev.name}/{keep_yield.name}`:\n\n```json\n{json.dumps(yout, indent=1)[:6000]}\n```")

    git = git_short_sha(repo)
    klt = klt_version_of(det_rep)
    allw = all(ndet.values())
    L = [f"# Bitcell Monte Carlo controls record {a.id} ({git})", "",
         "Issue: 2AMLogic/sky130-sram-compiler#19 (follows #14, #7). Append-only: add a new dated record, never edit this one. "
         "`2026-10-18-write-mc-complete.md` and `20261018-040941-91ba071.md` are not edited; this record supplies the controls "
         "their Limits sections say are missing.", "",
         "## Provenance", "",
         f"- klt: {klt}; backend: batch fleet; models staged from the repo-pinned PDK (`options.stage_model_inputs`)",
         f"- determinism control: request `sim/bitcell/requests/mc_write_trip_det.request.json`, testbench `tb/mc_write_trip_det.sp` "
         f"(the baseline ladder with `.param mc_mm_switch=0` after the `_mm` library section), n={DET_N} per point, "
         f"report `{ev.name}/mc_write_trip_det.report.json.gz`",
         f"- write negative control: request `mc_write_trip_neg.request.json`, testbench `tb/mc_write_trip_neg.sp`, n={NEG_N} per point, "
         f"seed {NEG_SEED} (baseline seed 20261018), mismatch sigma x{NEG_SCALE}, report `{ev.name}/mc_write_trip_neg.report.json.gz`",
         f"- read / hold negative control: requests `mc_read_snm_neg` / `mc_hold_snm_neg`, n={NEG_N} per point, seed {NEG_SEED}, "
         f"mismatch sigma x{NEG_SCALE}, same 6 points as the baseline",
         f"- mismatch scaling mechanism: the sky130 `_mm` sections sample `param = nominal + MC_MM_SWITCH * AGAUSS(0,1,1) * "
         f"(<device>__<param>_slope / sqrt(l*w*mult))`; the negative-control testbenches multiply every non-zero slope of "
         f"nfet_01v8 and pfet_01v8 (pinned open_pdks f6eeac7 `*__mismatch.corner.spice`) by `mm_scale = {NEG_SCALE}` with `.param` "
         "lines placed after the klt-injected `.lib`. klt has no first-class knob for this (filed as 2AMLogic/klayout-tools#3942).",
         "- baseline: n=60 per point write-trip MC (seed 20261018) from `corners/20261018-write-mc/` merged with "
         "`corners/20261018-write-mc-complete/` (rule of `make_write_mc_record.py`), and the read/hold MC tables of "
         "`records/20261018-040941-91ba071.md`; neither was re-run.", ""]
    for spec in a.job_log:
        nm, path = spec.split("=", 1)
        ids = sorted(set(re.findall(r"batch job (klt-sim-[0-9a-f]+) submitting", pathlib.Path(path).read_text())))
        L.append(f"- fleet jobs, {nm} ({len(ids)}): " + ", ".join(f"`{i}`" for i in ids))
    L += ["",
          "## Grading bar (by reference, not redesigned)", "",
          "gf180-sram `spec/statistical-treatment-decision.md` (read in a local checkout at `8d5a317`; the pinned commit "
          "`74ba8a621c9e` was not re-read) asks for a determinism control (mismatch off reproduces the deterministic corner), a "
          "negative control (an independently seeded, known-bad variant detected as degraded at every point) and a `klt yield` "
          "report with recorded seed and sample count. No numeric detection threshold is ratified there, so the one below is "
          "this record's own, stated before any control result was read.", "",
          "## Criteria (fixed before looking at results)", "",
          f"- Determinism: at every point all {DET_N} mismatch-off samples have the same highest flipping level k*, equal to k* of the "
          "matching deterministic corner in the 45-corner write table.",
          f"- Negative control: a point is *detected* iff sigma(control) >= {SIGMA_RATIO_MIN:g} x sigma(baseline) AND "
          f"sigmas-to-failure(control) <= {Z_RATIO_MAX:g} x sigmas-to-failure(baseline). Scaling sigma by {NEG_SCALE} predicts a ratio of "
          f"about {NEG_SCALE} on both. Any undetected point is reported as such and the factor is not changed afterwards.", "",
          "## Determinism control (write trip, mismatch off)", "",
          "| process | VDD (V) | T (C) | units | k* of each sample | k* of deterministic corner (45-corner record) | identical and equal |",
          "|---|---:|---:|---:|---|---:|---|"] + drows + ["",
          f"Result: {'all 8 points reproduce the deterministic k*' if dok else 'AT LEAST ONE POINT DOES NOT REPRODUCE the deterministic k* (see NO rows)'}.", "",
          f"## Negative control, write trip (sigma x{NEG_SCALE}, n={NEG_N}, seed {NEG_SEED})", "",
          "Mean / sigma are of the lower-bound trip voltage (V); sigmas-to-failure = mean/sigma against 0 V; no-flip samples enter at 0 V and are counted.", "",
          "| process | VDD (V) | T (C) | units | n valid | no-flip | non-monotone | baseline mean / sigma | control mean / sigma | baseline sigmas | control sigmas | detected |",
          "|---|---:|---:|---:|---:|---:|---:|---|---|---:|---:|---|"] + nrows + ["",
          f"Result: detected at {sum(ndet.values())} of {len(ndet)} points.", ""]
    if snm_blocks:
        L += [f"## Negative control, read / hold SNM (sigma x{NEG_SCALE}, n={NEG_N}, seed {NEG_SEED})", ""] + snm_blocks
        L += [f"Result: detected at {sum(snm_det.values())} of {len(snm_det)} read/hold points.", ""]
    L += ["## klt yield (baseline n=60 write trip)", "", yield_note, ""]
    L += ["## Limits of this record", "",
          f"- n = {NEG_N} per point for the negative controls and {DET_N} for the determinism control (not the baseline's 60); the detection test compares sigma of {NEG_N} against sigma of 60, relative sampling error about 16 % and 9 %.",
          "- The scaled variant changes mismatch sigma only through the pinned model's slope parameters; it does not change the process corner, the nominal parameters or the topology. A single factor was run, so no sensitivity curve is claimed.",
          "- Under the larger sigma the lower-bound mean can rise rather than fall (fs points): no-flip samples enter at 0 V and the lower bound floors there, so a heavy lower tail is invisible to the mean. Detection is therefore by sigma and sigmas-to-failure, as the criterion says, and the no-flip counts are reported beside them.",
          "- The pass/fail thresholds are this record's own (gf180-sram ratifies none); they are not a yield claim about the bitcell.",
          "- Write controls cover the same 8 points as the baseline (fs/sf `_mm` x 1.62/1.98 V x -40/125 C) and the read/hold controls the same 6 points (tt/sf/fs `_mm` x 1.62/1.98 V x 125 C).",
          "- No layout parasitics (no PEX). The fleet image PDK is open_pdks c6d73a3; `options.stage_model_inputs` ships the repo-pinned models.", ""]
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text("\n".join(L) + "\n")
    print("wrote", a.out, "| determinism ok:", dok, "| write detected:", f"{sum(ndet.values())}/{len(ndet)}",
          "| snm detected:", f"{sum(snm_det.values())}/{len(snm_det)}" if snm_det else "-")


if __name__ == "__main__":
    main()
