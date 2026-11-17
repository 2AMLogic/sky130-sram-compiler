"""Helpers shared by the bitcell margin-record generators (make_record.py, make_write_mc_record.py, make_controls_record.py): the read half (load, scrub) and the write half (save_gz_json, the deterministic gzip-JSON form every committed record artifact is stored in)."""

import gzip
import json
import pathlib
import statistics
import subprocess

# The ladder length is declared once, by the generator side that emits the ladder; this module validates
# against that same object, so a bench and a record can never be built from two different lengths.
# Re-exported because make_write_mc_record.py and make_controls_record.py import LADDER from here.
# tb_common is a sibling module: every caller already puts sim/bitcell/lib on sys.path before importing
# this one, so no path plumbing is added here (same convention as the snm_from_artifacts import below).
from tb_common import LADDER  # noqa: E402


class LadderLengthError(ValueError):
    """A report corner/unit carries a number of write-trip measurements that is not LADDER.

    That is a tooling error -- the bench that produced the report and this helper were built from
    different ladder lengths -- and never a margin result, so it is raised rather than folded into
    the `None` that means "this unit failed". Reporting it as a unit failure would publish a record
    asserting the cell never flips.
    """


class ProvenanceError(RuntimeError):
    """A provenance lookup (git sha, local klt version) failed, so the record cannot name what produced it.

    Raised rather than degraded to an empty string or a marker: unlike klt_version_of()'s
    "unknown (not in report)" -- a legitimate, documented absence in a local run's report -- a failed
    lookup means the value exists and we could not read it, and an append-only record published with a
    blank sha or version cannot be corrected in place. Fix the host fault and re-run.
    """


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


def save_gz_json(path, obj):
    """Scrubbed `obj` as deterministic gzip-JSON: the byte-reproducible form every committed record
    artifact is stored in. `mtime=0` plus sort_keys/indent is what makes a stored report reproducible
    from its input; it is spelled out here once so a change to the format cannot land in some
    generators and not others. GzipFile's default compression level is part of the format -- the
    committed artifacts replay byte-identically only under it -- so no compresslevel argument exists.
    """
    data = json.dumps(scrub(obj), indent=1, sort_keys=True).encode()
    with gzip.GzipFile(path, "wb", mtime=0) as g:
        g.write(data)


def _checked_output(argv):
    """stdout of `argv`, stripped, for the provenance lookups stamped into an append-only record.

    Refuses rather than degrades: a non-zero return code, an empty stdout, or a binary missing from
    PATH raises ProvenanceError carrying the command and the stderr tail, so no record is written
    naming a sha or version the lookup did not actually produce (an empty `git` sha used to land in
    record titles; a `klt` diagnostic used to be recorded as a "version").
    """
    try:
        r = subprocess.run(argv, capture_output=True, text=True)
    except FileNotFoundError as e:
        raise ProvenanceError(f"`{argv[0]}` not found on PATH: provenance lookup `{' '.join(argv)}` cannot run ({e})") from e
    out = r.stdout.strip()
    if r.returncode != 0 or not out:
        tail = (r.stderr or "").strip().splitlines()
        raise ProvenanceError(f"`{' '.join(argv)}` failed (rc {r.returncode}): {tail[-1] if tail else 'no stderr, empty stdout'}")
    return out


def git_short_sha(repo):
    """Short SHA of HEAD in `repo`, as stamped into a record's title and filename; a dirty working tree stamps `<sha>-dirty`.

    A record generated from uncommitted code names a commit that cannot reproduce it, and records
    are append-only, so the stamp must say so rather than silently mis-attribute (decision 0002;
    PR #139's `88af0fd` record is the concrete instance). Dirty means `git status --porcelain` is
    non-empty: tracked modifications and untracked non-ignored files count (a new source file is
    a real reproducibility gap), gitignored scratch output stays out, and every `records/`
    directory is excluded by pathspec so an earlier uncommitted record in the same PR does not
    mark the next one dirty, and it passes --untracked-files=normal explicitly so an ambient
    status.showUntrackedFiles=no (user or system config) cannot silence the untracked half
    (issue #186). The status probe cannot go through _checked_output -- empty stdout
    IS the clean case -- so it carries its own rc check: a failing `git status` raises
    ProvenanceError, it is never read as "clean" (the same refusal class as #103).
    Raises ProvenanceError on a failed lookup.
    """
    sha = _checked_output(["git", "-C", str(repo), "rev-parse", "--short", "HEAD"])
    r = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=normal",
         "--", ":(exclude,glob)**/records/**"],
        capture_output=True, text=True)
    if r.returncode != 0:
        tail = (r.stderr or "").strip().splitlines()
        raise ProvenanceError(
            f"`git -C {repo} status --porcelain` failed (rc {r.returncode}): "
            f"{tail[-1] if tail else 'no stderr, empty stdout'} -- cannot decide dirty vs clean "
            "for the record stamp")
    return sha if not r.stdout.strip() else f"{sha}-dirty"


def klt_version_local():
    """Version of the klt on THIS host (`klt --version`), for the steps that run locally rather than on the
    batch fleet (e.g. the `klt yield` step of the controls record); everything run remotely keeps using
    klt_version_of, the build recorded in the sim report. Raises ProvenanceError on a failed lookup, so a
    stderr diagnostic is never recorded as a version.
    """
    return _checked_output(["klt", "--version"])


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
    (value < VDD/2), -1 if even level 0 did not flip. None means the unit has a missing
    measurement; callers count that as a failure rather than a lower trip.

    A ladder whose length is not LADDER is a different thing entirely -- the report was produced
    by a bench built from another ladder length -- and raises LadderLengthError, because counting
    it as a unit failure would record a tooling mismatch as physics.
    """
    vdd = c["supply_v"]["vvdd"]
    q = [m["value"] for m in sorted(c["measurements"], key=lambda m: m["name"])]
    if len(q) != LADDER:
        raise LadderLengthError(
            f"corner {c.get('corner_id', '<unnamed>')} has {len(q)} write-trip measurements, expected "
            f"LADDER={LADDER}: this report was produced by a bench with a different ladder length. "
            "Regenerate the benches and requests (python3 -I sim/bitcell/lib/make_tb.py) and re-run the "
            "sim; this is not a write-margin failure.")
    if any(v is None for v in q):
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
