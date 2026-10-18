#!/usr/bin/env python3
"""Assemble an append-only bitcell margin record from collected `klt sim` runs.

Usage: make_record.py --id <record-id> --out <record.md> --evidence <dir>
         --read <reportA.json> <artifacts-dir> --hold <reportB.json> <artifacts-dir>
         --write <reportC.json>
         [--mc-read <artifacts-dir> ...] [--mc-hold <artifacts-dir> ...]
         [--mc-report-read <report.json> ...] [--mc-report-hold <report.json> ...]

Reports are copied gzip-compressed into <evidence>; the record carries tables only. Read/hold
margins are `eye_snm` (largest inscribed square); `pinned_snm` is the gf180-sram extractor's
number, shown beside it. Write margin is the write trip voltage from the 33-level ladder.
"""
import argparse
import gzip
import hashlib
import json
import math
import pathlib
import statistics
import subprocess
import sys

here = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(here))
import snm_from_artifacts as sa  # noqa: E402

repo = here.parents[2]


def dirname(corner_id):
    p = corner_id.replace("/", "_").replace(".", "p").replace("-", "n")
    return p


def snm_table(report, art):
    rep = json.load(open(report))
    rows = {}
    for c in rep["corners"]:
        d = pathlib.Path(art) / dirname(c["corner_id"])
        (plo, phi), (elo, ehi) = sa.snm_for(d / "waveform.raw.json", False)
        rows[c["corner_id"]] = (min(elo, ehi), min(plo, phi))
    return rep, rows


def write_table(report):
    rep = json.load(open(report))
    rows = {}
    for c in rep["corners"]:
        vdd = c["supply_v"]["vvdd"]
        q = [m["value"] for m in sorted(c["measurements"], key=lambda m: m["name"])]
        flipped = [v is not None and v < vdd / 2 for v in q]
        k = -1
        for i, f in enumerate(flipped):
            if not f:
                break
            k = i
        mono = not any(flipped[k + 1:])
        rows[c["corner_id"]] = (k, vdd * k / (len(q) - 1) if k >= 0 else None, mono, len(q))
    return rep, rows


def mc_stats(art_dirs, pair=True):
    pts = {}
    for a in art_dirs:
        for d in sorted(pathlib.Path(a).glob("*/waveform.raw.json")):
            name = d.parent.name
            key = name.rsplit("_mc", 1)[0]
            try:
                (plo, phi), (elo, ehi) = sa.snm_for(d, pair)
                pts.setdefault(key, []).append((min(elo, ehi), min(plo, phi)))
            except Exception as e:  # kept visible as an extraction failure
                pts.setdefault(key, []).append((None, str(e)))
    return pts


def fmt_mc(pts, det):
    out = ["| point | n | extract fail | mean eye SNM (V) | sigma (V) | min (V) | n <= 0 | sigmas to 0 (mean/sigma) | mean pinned (V) | deterministic corner eye SNM (V) |",
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for k, v in sorted(pts.items()):
        ok = [x[0] for x in v if x[0] is not None]
        pin = [x[1] for x in v if x[0] is not None]
        bad = len(v) - len(ok)
        if len(ok) < 2:
            out.append(f"| {k} | {len(v)} | {bad} | - | - | - | - | - | - | - |")
            continue
        m, s = statistics.mean(ok), statistics.stdev(ok)
        out.append(f"| {k} | {len(v)} | {bad} | {m:.4f} | {s:.4f} | {min(ok):.4f} | "
                   f"{sum(1 for x in ok if x <= 0)} | {m / s:.1f} | {statistics.mean(pin):.4f} | {det.get(k, float('nan')):.4f} |")
    return out


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--read", nargs=2, required=True)
    ap.add_argument("--hold", nargs=2, required=True)
    ap.add_argument("--write", required=True)
    ap.add_argument("--mc-read", nargs="*", default=[])
    ap.add_argument("--mc-hold", nargs="*", default=[])
    ap.add_argument("--mc-report-read", nargs="*", default=[])
    ap.add_argument("--mc-report-hold", nargs="*", default=[])
    a = ap.parse_args()

    ev = pathlib.Path(a.evidence)
    ev.mkdir(parents=True, exist_ok=True)

    def scrub(o):
        """Host-absolute artifact paths (scratch dirs, home) are replaced by their last two components."""
        if isinstance(o, dict):
            return {k: scrub(v) for k, v in o.items()}
        if isinstance(o, list):
            return [scrub(v) for v in o]
        if isinstance(o, str) and o.startswith("/") and ("/home/" in o or "/tmp/" in o):
            return "<artifact>/" + "/".join(o.rstrip("/").split("/")[-2:])
        return o

    def keep(src, name):
        data = json.dumps(scrub(json.load(open(src))), indent=1, sort_keys=True).encode()
        with gzip.GzipFile(ev / f"{name}.json.gz", "wb", mtime=0) as g:
            g.write(data)

    rrep, rread = snm_table(*a.read)
    hrep, rhold = snm_table(*a.hold)
    wrep, rwrite = write_table(a.write)
    keep(a.read[0], "read_snm_corners.report")
    keep(a.hold[0], "hold_snm_corners.report")
    keep(a.write, "write_trip_corners.report")
    mcr = [(p, f"mc_read_snm.report{i}") for i, p in enumerate(a.mc_report_read)]
    mch = [(p, f"mc_hold_snm.report{i}") for i, p in enumerate(a.mc_report_hold)]
    for p, n in mcr + mch:
        keep(p, n)

    def remote(rep):
        r = rep["environment"].get("remote", {})
        w = r.get("worker_environment", {})
        return r.get("job_id"), r.get("instance_type"), w.get("pdk", {}).get("stamp_text"), \
            (w.get("simulator", {}).get("version_banner", "").split("\n")[1:2] or [""])[0].strip("* ")

    sizing = json.load(open(repo / "design/bitcell/sizing.json"))
    git = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    L = [f"# Bitcell margin record {a.id} ({git})", "",
         "Issue: 2AMLogic/sky130-sram-compiler#7 (part of #2). Append-only: add a new dated record, never edit this one.", "",
         "## Provenance", "",
         f"- sizing (drawn W/L, um): PD {sizing['pd']['w']}/{sizing['pd']['l']} {sizing['pd']['model']}, "
         f"AX {sizing['ax']['w']}/{sizing['ax']['l']} {sizing['ax']['model']}, "
         f"PU {sizing['pu']['w']}/{sizing['pu']['l']} {sizing['pu']['model']} (design/bitcell/sizing.json)",
         f"- klt: {rrep['environment'].get('client_klt_version') or rrep['environment'].get('remote', {}).get('client_klt_version')}",
         "- backend: batch fleet (`KLT_SIM_BACKEND=batch`); models staged from the repo-pinned PDK (`options.stage_model_inputs`)",
         "- margin extractor: gf180-sram `sim/lib/snm_extract.py` @ `74ba8a621c9e` (sha256 checked by `fetch_pinned.sh`) plus the inscribed-square `eyes()` in `sim/bitcell/lib/snm_from_artifacts.py`", ""]
    for nm, rep, req in (("read SNM", rrep, "read_snm_corners"), ("hold SNM", hrep, "hold_snm_corners"),
                         ("write trip", wrep, "write_trip_corners")):
        job, inst, pdk, eng = remote(rep)
        L.append(f"- {nm}: job `{job}`, {inst}, worker `{eng}`, worker image PDK `{pdk}`; "
                 f"request `sim/bitcell/requests/{req}.request.json` sha256 `{sha(repo / f'sim/bitcell/requests/{req}.request.json')[:16]}`; "
                 f"report `{ev.name}/{req}.report.json.gz` (host paths scrubbed)")
    L += ["", "## Deterministic corners (45)", "",
          "`eye_snm` = largest inscribed square (graded). `pinned` = gf180-sram extractor output (vertical gap), shown for comparison. "
          "Write trip = highest BL level (V) that still flipped the cell within the 2 ns pulse (ladder step VDD/32, so the true trip lies in the next 56 mV-class step above); "
          "`k` is the ladder index of that level.", "",
          "| corner | read eye SNM | read pinned | hold eye SNM | hold pinned | write trip V (k) |", "|---|---:|---:|---:|---:|---:|"]
    order = list(rread)
    for cid in order:
        r, h = rread[cid], rhold[cid]
        w = rwrite.get(cid)
        wtxt = f"{w[1]:.3f} ({w[0]})" if w and w[1] is not None else "NONE"
        L.append(f"| {cid} | {r[0]:.4f} | {r[1]:.4f} | {h[0]:.4f} | {h[1]:.4f} | {wtxt} |")
    rmin = min(rread.items(), key=lambda kv: kv[1][0])
    hmin = min(rhold.items(), key=lambda kv: kv[1][0])
    wmin = min((kv for kv in rwrite.items() if kv[1][1] is not None), key=lambda kv: kv[1][1])
    bad_w = [c for c, v in rwrite.items() if v[1] is None or not v[2]]
    L += ["", "## Summary", "",
          f"- corners with a row in each table: read {len(rread)}, hold {len(rhold)}, write {len(rwrite)} (expected 45)",
          f"- read SNM minimum {rmin[1][0]:.4f} V at {rmin[0]}; all > 0: {all(v[0] > 0 for v in rread.values())}",
          f"- hold SNM minimum {hmin[1][0]:.4f} V at {hmin[0]}; all > 0: {all(v[0] > 0 for v in rhold.values())}",
          f"- write trip minimum {wmin[1][1]:.3f} V at {wmin[0]}; corners with no flip or a non-monotone ladder: {bad_w or 'none'}", ""]
    if a.mc_read or a.mc_hold:
        L += ["## Monte Carlo (per-instance mismatch, `_mm` sections, two independent half cells, pair extraction)", ""]
        for nm, dirs, reps in (("read SNM", a.mc_read, a.mc_report_read), ("hold SNM", a.mc_hold, a.mc_report_hold)):
            if dirs:
                det = rread if nm.startswith("read") else rhold
                detk = {}
                for cid, v in det.items():
                    proc, vdd, temp = cid.split("/")
                    detk[f"{proc}_mm_{vdd.replace('.', 'p').replace('V', 'V')}_{temp}"] = v[0]
                L += [f"### {nm}", ""] + fmt_mc(mc_stats(dirs), detk) + [""]
                L.append("jobs: " + ", ".join(sorted({pathlib.Path(d).name for d in dirs})))
                L.append("")
            for p in reps:
                rep = json.load(open(p))
                mc = rep["environment"].get("monte_carlo", {})
                L.append(f"- n={mc.get('n')} samples per point, seed={mc.get('seed')}, vary={mc.get('vary')}, "
                         f"k_sigma={mc.get('k_sigma')}; merged report `{ev.name}/` (gz)")
            L.append("")
    L += ["## Limits of this record", "",
          "- Graded margin is `eye_snm`. The pinned extractor over-reads (filed as 2AMLogic/gf180-sram#213); at tt / 1.98 V / 25 C read, "
          "`eye_snm` 0.4419 V matches an independent series-noise-source SPICE probe (0.4410 V, single local ngspice run) while the pinned script says 0.572 V.",
          "- Write margin is the 2 ns write-trip ladder (resolution VDD/32), not gf180-sram's bisection (`klt sim` owns the `.control` block). "
          "The worst corner is the thinnest margin in the set; **no Monte Carlo was run on write margin**, so a mismatch-driven write failure is not excluded.",
          "- Monte Carlo covers read and hold SNM only: 60 samples at 6 points (tt, sf, fs `_mm` sections x 1.62 / 1.98 V x 125 C, the hot corner where both margins are lowest in the deterministic table), "
          "not the full 45. The \"deterministic corner\" column is the matching non-mismatch corner, a consistency check, not gf180-sram's exact mismatch-off rerun. "
          "No negative control and no `klt yield` report were produced, so the gf180-sram statistical-evidence recipe is not fully met; sigma is estimated from 60 draws.",
          "- Read/hold use decoupled half-cell fixtures whose sizes come from the same `sizing.json` as the schematic and layout; they model no layout parasitics (no PEX).",
          "- The fleet image PDK is open_pdks c6d73a3; requests set `options.stage_model_inputs` so the models are shipped from the repo-pinned f6eeac7 install (worker `pdk.models_staged` is reported in the gz reports).",
          ""]
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text("\n".join(L) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
