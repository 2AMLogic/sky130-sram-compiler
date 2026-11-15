"""Print per-case rule counts for the three runs (curated, lydrc, maximal-rules deck-file)."""
import collections, glob, json, os, sys

out = sys.argv[1]
names = sorted({os.path.basename(p)[:-4] for p in glob.glob(f"{out}/*.gds")})
for n in names:
    row = {}
    for eng in ("curated", "lydrc", "mr"):
        d = json.load(open(f"{out}/{n}.{eng}.json"))
        c = collections.Counter(v["rule"] for v in d["violations"])
        row[eng] = (d["status"], dict(sorted(c.items())))
    print(n)
    for k, (st, c) in row.items():
        print(f"  {k:8s} {st:17s} total={sum(c.values()):3d} {c}")

# The stripped-marker foundry case is the control that proves the mr deck really
# executed its rules (records/2026-10-17-f22b400.md, 47 at that klt/PDK pin).
# Losing the mr --deck-var trio yields coverage_unknown and 0 violations for
# every case; that must not pass as a green summary, so assert count > 0.
CONTROL = "foundry_marker_stripped"
try:
    d = json.load(open(f"{out}/{CONTROL}.mr.json"))
    total = sum(collections.Counter(v["rule"] for v in d["violations"]).values())
except (OSError, json.JSONDecodeError, KeyError) as e:
    print(f"CONTROL FAILED: cannot read {CONTROL} mr result ({e})")
    sys.exit(1)
if total <= 0:
    print(f"CONTROL FAILED: {CONTROL} mr deck reported 0 violations (status={d.get('status')}) -- the mr deck did not execute")
    sys.exit(1)
print(f"CONTROL ok: {CONTROL} mr deck fired {total} violations")
