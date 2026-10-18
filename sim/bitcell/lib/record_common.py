"""Helpers shared by the bitcell margin-record generators (make_record.py, make_write_mc_record.py, make_controls_record.py)."""

import subprocess

LADDER = 33


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
