#!/usr/bin/env python3
"""Assemble an append-only column-bench record from collected `klt sim` runs (T1 item 9, analog).

Usage: make_column_record.py --id <record-id> --out <record.md> --evidence <dir> --scratch <dir>
  <scratch> holds <bench>.json (the klt sim report, --format json) and <bench>/ (the `-o` artifact directory)
  for col_read0 col_read1 col_write0 col_write1 col_write0_nowen col_read_snm col_hold_snm
  col_mc_{read,hold}_snm and col_mc_{read,hold}_snm_neg.
Reports are copied gzip-compressed (host paths scrubbed) into <evidence>; the record carries tables only.
Margin extraction reuses sim/bitcell/lib (pinned gf180-sram extractor + inscribed-square eyes()).
"""
import argparse
import gzip
import hashlib
import json
import pathlib
import statistics
import sys

here = pathlib.Path(__file__).resolve().parent
repo = here.parents[2]
sys.path.insert(0, str(repo / "sim/bitcell/lib"))
sys.path.insert(0, str(here))
import make_column_tb as gen  # noqa: E402
import snm_from_artifacts as sa  # noqa: E402
from record_common import git_short_sha, klt_version_of, scrub  # noqa: E402


def dirname(cid):
    return cid.replace("/", "_").replace(".", "p").replace("-", "n")


def load(scratch, bench):
    return json.load(open(scratch / f"{bench}.json"))


def meas(c):
    return {m["name"]: m["value"] for m in c["measurements"]}


def cname(c):
    return f"{c['process']}/{c['supply_v']['vvdd']:.3f}V/{c['temperature_c']}C"


def ladder_min(flags):
    """Index of the first trial from which every later trial passes (None if the last one fails)."""
    for i in range(len(flags)):
        if all(flags[i:]):
            return i
    return None


def crossing(t, y, level, rising, t0, t1):
    for i in range(1, len(t)):
        if t[i] <= t0 or t[i - 1] >= t1:
            continue
        a, b = y[i - 1], y[i]
        if (a < level <= b) if rising else (a > level >= b):
            return t[i - 1] + (level - a) * (t[i] - t[i - 1]) / (b - a)
    return None


def waveform_series(path, names):
    wf = json.load(open(path))
    vn = [v["name"] for v in wf["variables"]]
    idx = {n: vn.index(n) for n in names}
    pts = sorted(wf["points"], key=lambda p: p[vn.index("time")])
    return [p[vn.index("time")] for p in pts], {n: [p[i] for p in pts] for n, i in idx.items()}


def read_rows(scratch, bench):
    want = 1 if bench.endswith("1") else 0
    rep = load(scratch, bench)
    rows = []
    for c in rep["corners"]:
        vdd, m = c["supply_v"]["vvdd"], meas(c)
        n = len(gen.READ_D)
        if any(m.get(f"dout{k:02d}") is None for k in range(n)):
            rows.append((cname(c), None))
            continue
        ok = [(m[f"dout{k:02d}"] > vdd / 2) == bool(want) for k in range(n)]
        st = [(m[f"q{k:02d}"] > vdd / 2) == bool(want) for k in range(n)]
        i = ladder_min(ok)
        tsa = None
        if want == 1 and i is not None:
            wf = scratch / bench / dirname(c["corner_id"]) / "waveform.raw.json"
            if wf.exists():
                t, y = waveform_series(wf, ["time", "v(sae)", "v(dout)"])
                ts = [x * 1e9 for x in t]
                rises = []
                prev = False
                for j, v in enumerate(y["v(sae)"]):
                    hi = v > vdd / 2
                    if hi and not prev:
                        rises.append(ts[j])
                    prev = hi
                if len(rises) == n:
                    td = crossing(ts, y["v(dout)"], vdd / 2, True, rises[i], rises[i] + 0.7)
                    tsa = None if td is None else td - rises[i]
        rows.append((cname(c), dict(dmin=None if i is None else gen.READ_D[i],
                                    low_fail=not ok[0], all_state_ok=all(st),
                                    dv=None if i is None else m[f"dv{i:02d}"],
                                    tsa=tsa, bump=m["bump"], hs=(m["hs1"], m["hs2"]), vdd=vdd)))
    return rep, rows


def write_rows(scratch, bench, want):
    rep = load(scratch, bench)
    rows = []
    for c in rep["corners"]:
        vdd, m = c["supply_v"]["vvdd"], meas(c)
        n = len(gen.WRITE_W)
        if any(m.get(f"q{k:02d}") is None for k in range(n)):
            rows.append((cname(c), None))
            continue
        ok = [(m[f"q{k:02d}"] > vdd / 2) == bool(want) for k in range(n)]
        i = ladder_min(ok)
        rows.append((cname(c), dict(wmin=None if i is None else gen.WRITE_W[i], first_ok=ok[0],
                                    nflip=sum(ok), hs=(m["hs1"], m["hs2"]), vdd=vdd)))
    return rep, rows


def snm_rows(scratch, bench):
    rep = load(scratch, bench)
    rows = {}
    for c in rep["corners"]:
        d = scratch / bench / dirname(c["corner_id"])
        (plo, phi), (elo, ehi) = sa.snm_for(d / "waveform.raw.json", False)
        rows[cname(c)] = (min(elo, ehi), min(plo, phi))
    return rep, rows


def mc_stats(scratch, bench):
    pts = {}
    for d in sorted((scratch / bench).glob("*/waveform.raw.json")):
        key = d.parent.name.rsplit("_mc", 1)[0]
        try:
            (plo, phi), (elo, ehi) = sa.snm_for(d, True)
            pts.setdefault(key, []).append(min(elo, ehi))
        except Exception:
            pts.setdefault(key, []).append(None)
    return pts


def fmt_mc(pts):
    out = ["| point | n | extract fail | mean eye SNM (V) | sigma (V) | min (V) | n <= 0 | sigmas to 0 (mean/sigma) |",
           "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for k, v in sorted(pts.items()):
        ok = [x for x in v if x is not None]
        if len(ok) < 2:
            out.append(f"| {k} | {len(v)} | {len(v) - len(ok)} | - | - | - | - | - |")
            continue
        m, s = statistics.mean(ok), statistics.stdev(ok)
        out.append(f"| {k} | {len(v)} | {len(v) - len(ok)} | {m:.4f} | {s:.4f} | {min(ok):.4f} | "
                   f"{sum(x <= 0 for x in ok)} | {m / s:.1f} |")
    return out


def f(x, nd=3):
    return "-" if x is None else f"{x:.{nd}f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--scratch", required=True)
    a = ap.parse_args()
    scratch, ev = pathlib.Path(a.scratch), pathlib.Path(a.evidence)
    ev.mkdir(parents=True, exist_ok=True)
    benches = ["col_read0", "col_read1", "col_write0", "col_write1", "col_write0_nowen", "col_read_snm",
               "col_hold_snm", "col_mc_read_snm", "col_mc_hold_snm", "col_mc_read_snm_neg", "col_mc_hold_snm_neg"]
    reps = {}
    for b in benches:
        reps[b] = load(scratch, b)
        data = json.dumps(scrub(reps[b]), indent=1, sort_keys=True).encode()
        with gzip.GzipFile(ev / f"{b}.report.json.gz", "wb", mtime=0) as g:
            g.write(data)

    def sha(p):
        return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16]

    L = [f"# Column bench record {a.id} ({git_short_sha(repo)})", "",
         "Issue: 2AMLogic/sky130-sram-compiler#29 (T1 item 9, analog partition). Append-only: add a new dated record, never edit this one.", "",
         "## Provenance", "",
         "- design under test: bit slice (64 rows x 4 columns) of `design/compiler/macro/sram_256x32_m4.spice` (mux 4: 64-cell bit lines), "
         "sizing unchanged from `design/compiler/sizing.json` / `design/bitcell/sizing.json`",
         "- benches generated by `sim/column/lib/make_column_tb.py` (drift gate: `--check`)",
         f"- klt: {klt_version_of(reps['col_read0'])} (fleet runner 0.7.0; a 0.8.x client is refused by the fleet's version check, see Limits)",
         "- backend: batch fleet; models staged from the repo-pinned PDK (`options.stage_model_inputs`)",
         "- margin extractor for the SNM benches: gf180-sram `snm_extract.py` @ `74ba8a621c9e` plus the inscribed-square `eyes()` of `sim/bitcell/lib/snm_from_artifacts.py`"]
    for b in benches:
        r = reps[b]["environment"].get("remote", {})
        L.append(f"- {b}: job `{r.get('job_id')}`, {r.get('instance_type')}, request sha256 `{sha(repo / f'sim/column/requests/{b}.request.json')}`; report `{ev.name}/{b}.report.json.gz`")
    L.append("")

    # ---- read access
    L += ["## Read access (SAE-delay ladder, 45 corners)", "",
          "`d_min` = smallest SAE delay after WL (ns) from which every longer-delay trial reads the stored value (ladder step 0.05 ns up to 1.0 ns, "
          "then 1.2 .. 2.4). `t_sa` = SAE rising 50 % to DOUT 50 % at the `d_min` trial (read 1 only; a read 0 leaves DOUT low). "
          "`t_access` = d_min + t_sa for read 1 (WL 50 % to DOUT 50 %, decoder excluded). `dv` = SBL - SBLB at SAE (V). "
          "`bump` = max voltage of the node that is 0 (Q for read 0, QB for read 1) over the run; half-select columns: hs1/hs2 are the min/max of the "
          "row-0 cells of columns 1 and 2 over the run (a left rail is a retained cell). `fail@0` = the d = 0 trial read wrongly "
          "(read 1: the ladder has a failing end).", ""]
    r0rep, r0 = read_rows(scratch, "col_read0")
    r1rep, r1 = read_rows(scratch, "col_read1")
    L += ["| corner | read0 d_min | read0 dv | read0 bump | read1 d_min | read1 t_sa | read1 t_access | read1 dv | read1 bump | read1 fail@0 | state kept | hs1/hs2 (read1) |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|"]
    worst = (None, -1.0)
    ncorner_bad = []
    for (cid, x0), (_, x1) in zip(r0, r1):
        if x0 is None or x1 is None or x0["dmin"] is None or x1["dmin"] is None:
            ncorner_bad.append(cid)
            L.append(f"| {cid} | " + ("NO VALUE / NEVER CORRECT" if x0 is None or x0["dmin"] is None else f(x0['dmin'], 2)) + " | | | "
                     + ("NO VALUE / NEVER CORRECT" if x1 is None or x1["dmin"] is None else f(x1['dmin'], 2)) + " | | | | | | | |")
            continue
        ta = None if x1["tsa"] is None else x1["dmin"] + x1["tsa"]
        if ta is not None and ta > worst[1]:
            worst = (cid, ta)
        L.append(f"| {cid} | {f(x0['dmin'], 2)} | {f(x0['dv'])} | {f(x0['bump'])} | {f(x1['dmin'], 2)} | {f(x1['tsa'])} | {f(ta)} | "
                 f"{f(x1['dv'])} | {f(x1['bump'])} | {x1['low_fail']} | {x0['all_state_ok'] and x1['all_state_ok']} | "
                 f"{x1['hs'][0]:.2f}/{x1['hs'][1]:.2f} |")
    L += [""]

    # ---- write completion
    w0rep, w0 = write_rows(scratch, "col_write0", 0)
    w1rep, w1 = write_rows(scratch, "col_write1", 1)
    nrep, nw = write_rows(scratch, "col_write0_nowen", 0)
    L += ["## Write completion (write-pulse-width ladder, 45 corners)", "",
          "`w_min` = smallest WL + WEN pulse width (ns) from which every longer pulse writes the cell; ladder 0.05 .. 0.80 step 0.05, then 1.0, 1.25, 1.5, 2.0. "
          "`NONE` = the cell is not written even by the 2.0 ns pulse. `flips` = trials (of 20) that wrote the cell.", "",
          "| corner | write0 w_min | write0 flips | write1 w_min | write1 flips |", "|---|---:|---:|---:|---:|"]
    nonew = []
    for (cid, x0), (_, x1) in zip(w0, w1):
        def cell(x, tag):
            if x is None:
                nonew.append((cid, tag, "no value"))
                return "NO VALUE", "-"
            if x["wmin"] is None:
                nonew.append((cid, tag, x["nflip"]))
                return "NONE", str(x["nflip"])
            return f(x["wmin"], 2), str(x["nflip"])
        a0, a1 = cell(x0, "write0"), cell(x1, "write1")
        L.append(f"| {cid} | {a0[0]} | {a0[1]} | {a1[0]} | {a1[1]} |")
    L += ["", f"Corners where a write is never completed within 2.0 ns: {nonew or 'none'}.", "",
          "### Negative control (WEN never asserted)", "",
          f"Same ladder, {len(nw)} corners, DIN = 0 but WEN held low: trials that wrote the cell (must be 0 everywhere): "
          f"{sum(x['nflip'] for _, x in nw if x)} of {sum(len(gen.WRITE_W) for _, x in nw if x)}; "
          f"corners with no value: {[c for c, x in nw if x is None] or 'none'}.", ""]

    # ---- SNM
    rrep, rs = snm_rows(scratch, "col_read_snm")
    hrep, hs = snm_rows(scratch, "col_hold_snm")
    L += ["## In-situ SNM, deterministic corners (bit line = real column: precharge on, 63 further cells)", "",
          "| corner | read eye SNM | read pinned | hold eye SNM | hold pinned |", "|---|---:|---:|---:|---:|"]
    for cid in rs:
        L.append(f"| {cid} | {rs[cid][0]:.4f} | {rs[cid][1]:.4f} | {hs[cid][0]:.4f} | {hs[cid][1]:.4f} |")
    L += ["", "## In-situ SNM, Monte Carlo (two independently mismatched half cells, pair extraction)", ""]
    for b, t in (("col_mc_read_snm", "read SNM, n = 60 per point"), ("col_mc_hold_snm", "hold SNM, n = 60 per point"),
                 ("col_mc_read_snm_neg", "read SNM NEGATIVE CONTROL (mismatch sigma x6, n = 20)"),
                 ("col_mc_hold_snm_neg", "hold SNM NEGATIVE CONTROL (mismatch sigma x6, n = 20)")):
        L += [f"### {t}", ""] + fmt_mc(mc_stats(scratch, b)) + [""]

    # ---- summary
    rmin = min(rs.items(), key=lambda kv: kv[1][0])
    hmin = min(hs.items(), key=lambda kv: kv[1][0])
    L += ["## Summary", "",
          f"- slowest read access (read 1, WL to DOUT): {f(worst[1], 2)} ns at {worst[0]}; corners without a clean read ladder: {ncorner_bad or 'none'}",
          f"- write completion not reached within 2.0 ns: {nonew or 'none'}",
          f"- in-situ read SNM minimum {rmin[1][0]:.4f} V at {rmin[0]}; hold {hmin[1][0]:.4f} V at {hmin[0]}", ""]
    L += ["## Limits of this record", "",
          "- Pre-layout: no bit-line or word-line wire parasitics; the other 124 columns load the word line only through the gate area of 248 access-device-sized NMOS; "
          "strobe edges are ideal 50 ps ramps with no driver fan-out; the row decoder is excluded (WL is driven through the real `sram_wldrv`).",
          "- One bit slice of one row group (64 rows, mux 4), not the full array; no power-grid droop, no neighbour-bit coupling, no sense-amp offset beyond the process corners.",
          "- Read access is SAE-delay limited by construction: the controller's real SAE timing (one clock period after WL) belongs to the spec (#2 / #8).",
          "- Write ladder resolution is 0.05 ns up to 0.8 ns; read-SAE resolution 0.05 ns up to 1.0 ns. Write margin has no Monte Carlo here (stability margins only), so a mismatch-driven write failure is not excluded.",
          "- In-situ DC SNM differs from the isolated-cell SNM only through the precharge device's on-resistance and the 63-cell leakage on the bit line; compare `sim/bitcell/records/`.",
          "- The fleet runner is klt 0.7.0 and refuses a 0.8.x client (`batch_runner_version_mismatch`), so every fleet run here used a 0.7.0 client via `uvx --from klayout-tools==0.7.0`; the `--report-out` flag is also absent in 0.7.0, so reports are the stdout JSON.",
          ""]
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text("\n".join(L) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
