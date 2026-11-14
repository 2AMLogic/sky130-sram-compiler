"""Helpers shared by the bitcell margin-record generators (make_record.py, make_write_mc_record.py, make_controls_record.py)."""

import gzip
import json
import pathlib
import statistics
import subprocess

LADDER = 33


def dirname(corner_id):
    """Artifact directory name `klt sim` gives a corner_id."""
    return corner_id.replace("/", "_").replace(".", "p").replace("-", "n")


def load(p):
    """JSON report, plain or gzip-compressed (.gz)."""
    p = pathlib.Path(p)
    return json.load(gzip.open(p) if p.suffix == ".gz" else open(p))


def scrub(o):
    """Host-absolute artifact paths (scratch dirs, home) are replaced by their last two components."""
    if isinstance(o, dict):
        return {k: scrub(v) for k, v in o.items()}
    if isinstance(o, list):
        return [scrub(v) for v in o]
    if isinstance(o, str) and o.startswith("/") and ("/home/" in o or "/tmp/" in o):
        return "<artifact>/" + "/".join(o.rstrip("/").split("/")[-2:])
    return o


def git_short_sha(repo):
    """Short SHA of HEAD in `repo`, as stamped into a record's title."""
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()


def klt_version_of(report):
    """klt build that produced `report`, from environment.client_klt_version or environment.remote.client_klt_version.

    Never invents a version: a report that carries neither field yields an explicit marker, so a record cannot
    name a klt build that did not produce it.
    """
    env = report["environment"]
    return env.get("client_klt_version") or env.get("remote", {}).get("client_klt_version") or "unknown (not in report)"


def runner_version_of(report):
    """Fleet runner klt build that ran `report`, from environment.remote.runner_klt_version.

    The runner is the klt on the fleet image, not the client that submitted: `klt sim` compares the
    two before any S3 write and refuses a mismatch with `batch_runner_version_mismatch` under the
    default `batch.runner_version_check: "enforce"`. Never invents a version (a local run carries no
    `remote` block at all), so a record cannot name a fleet runner that did not produce it.
    """
    return report["environment"].get("remote", {}).get("runner_klt_version") or "unknown (not in report)"


def write_ladder(c):
    """Write-trip ladder of one report corner/unit -> (kstar, monotone, n_levels), or None.

    kstar is the highest BL level index in the leading run of levels that flipped the cell
    (value < VDD/2), -1 if even level 0 did not flip. None means the unit did not produce a
    complete ladder (a missing measurement or fewer/more than LADDER levels); callers count
    that as a failure rather than a lower trip.
    """
    vdd = c["supply_v"]["vvdd"]
    q = [m["value"] for m in sorted(c["measurements"], key=lambda m: m["name"])]
    if len(q) != LADDER or any(v is None for v in q):
        return None
    flipped = [v < vdd / 2 for v in q]
    k = -1
    for i, f in enumerate(flipped):
        if not f:
            break
        k = i
    return k, not any(flipped[k + 1:]), len(q)


def mc_stats(art_dirs, pair=True):
    """Per-point (eye SNM, pinned SNM) samples from Monte Carlo artifact dirs, keyed by point name.

    An extraction failure is kept visible as (None, message), never dropped.
    """
    import snm_from_artifacts as sa  # sibling module; the caller has sim/bitcell/lib on sys.path

    pts = {}
    for a in art_dirs:
        for d in sorted(pathlib.Path(a).glob("*/waveform.raw.json")):
            key = d.parent.name.rsplit("_mc", 1)[0]
            try:
                (plo, phi), (elo, ehi) = sa.snm_for(d, pair)
                pts.setdefault(key, []).append((min(elo, ehi), min(plo, phi)))
            except Exception as e:
                pts.setdefault(key, []).append((None, str(e)))
    return pts


def fmt_mc(pts, det=None):
    """Markdown Monte Carlo SNM table. With `det` (point -> deterministic-corner eye SNM) it also has the
    mean-pinned and deterministic columns; without, only the eye-SNM columns."""
    cols = ["point", "n", "extract fail", "mean eye SNM (V)", "sigma (V)", "min (V)", "n <= 0", "sigmas to 0 (mean/sigma)"]
    if det is not None:
        cols += ["mean pinned (V)", "deterministic corner eye SNM (V)"]
    out = ["| " + " | ".join(cols) + " |", "|---|" + "---:|" * (len(cols) - 1)]
    for k, v in sorted(pts.items()):
        ok = [x[0] for x in v if x[0] is not None]
        bad = len(v) - len(ok)
        if len(ok) < 2:
            out.append(f"| {k} | {len(v)} | {bad} |" + " - |" * (len(cols) - 3))
            continue
        m, s = statistics.mean(ok), statistics.stdev(ok)
        row = (f"| {k} | {len(v)} | {bad} | {m:.4f} | {s:.4f} | {min(ok):.4f} | "
               f"{sum(1 for x in ok if x <= 0)} | {m / s:.1f}")
        if det is not None:
            pin = [x[1] for x in v if x[0] is not None]
            row += f" | {statistics.mean(pin):.4f} | {det.get(k, float('nan')):.4f}"
        out.append(row + " |")
    return out
