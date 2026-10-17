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
