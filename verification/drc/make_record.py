#!/usr/bin/env python3
"""Render the T1 item 3 evidence envelopes and an append-only dated record from a run_drc.sh run.

Usage: verification/drc/make_record.py <outdir from run_drc.sh>
Copies the two graded `klt drc` envelopes (unmodified) to design/compiler/evidence/item3.json and
evidence/item3-digital.json, and writes verification/drc/records/<UTC date>-<git sha>.md, never
overwriting one. The manifest cites the evidence files; regenerate the signoff record after
(manifests/README.md). Quoted coverage fields are dumped from the JSON, not retyped.
"""
import datetime
import json
import pathlib
import shutil
import subprocess
import sys

here = pathlib.Path(__file__).resolve().parent
repo = here.parents[1]
out = pathlib.Path(sys.argv[1])
J = lambda p: json.loads((out / p).read_text())
run = lambda *c: subprocess.run(c, capture_output=True, text=True, cwd=repo).stdout.strip()

shutil.copyfile(out / "analog/curated-graded.json", repo / "design/compiler/evidence/item3.json")
shutil.copyfile(out / "digital/curated.json", repo / "evidence/item3-digital.json")

sha = run("git", "rev-parse", "--short", "HEAD")
day = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
rec = here / "records" / f"{day}-{sha}.md"
assert not rec.exists(), rec
times = (out / "times.txt").read_text().strip().splitlines()
summary = (out / "analog/summary.txt").read_text().strip()
seam = J("seam/curated.json")
seam_w = [v["bbox"] for v in seam["violations"] if v["rule"] == "met1.width.1"]

L = [f"# T1 item 3 (DRC clean) record {day} ({sha})", "",
     "Issue: 2AMLogic/sky130-sram-compiler#32. Append-only: add a new dated record, never edit this one.", "",
     f"- klt: {run('klt', '--version')}; command and wall time of each run below (`verification/drc/run_drc.sh`, one run at a time, local)",
     "- streams (guarded by sha256 before the run): `layout/sram_256x32_m4.gds` ca10c045b447a8ce3bdb55f8922e2dfb954826dd8a9583ca0d39629d5b9e555c; "
     "`layout/control/control.gds` 8d22fcb1ffc9da78508311e825761b66c6983e70887dbdcfee651f41636bb6a6",
     "- each partition is graded on its own stream. The P&R control block is **not composed** into the macro GDS on `main`; no composed macro+control DRC exists or is claimed.", "",
     "```", *times, "```", ""]
for name, path, ev in (("Analog: `layout/sram_256x32_m4.gds` (array, pitch-matched periphery, control row; top `sram_256x32_m4`)",
                        "analog/curated-graded.json", "design/compiler/evidence/item3.json"),
                       ("Digital: `layout/control/control.gds` (`klt place-and-route` output, `sram_ctrl`)",
                        "digital/curated.json", "evidence/item3-digital.json")):
    d = J(path)
    p, c, n = d["provenance"], d["coverage"], d["negative_control"]
    L += [f"## {name}", "",
          f"- graded report: `{ev}` (unmodified `klt drc --deck sky130` envelope, schema {d['schema_version']})",
          f"- **status: {d['status']}**, violation_count {d['violation_count']}, rule_counts {d['rule_counts']}",
          f"- deck `{p['deck']['name']}` content hash `{p['deck']['content_hash']}` (released: {p['deck']['released']}); klayout {p['klayout_version']}; input `{p['input']['content_hash']}`",
          f"- in-report negative control `{n['file']}`: {n['status']}, {n['violation_count']} violations, rules {n['rules_found']}", "",
          "Coverage, quoted verbatim from the report (`coverage.*`):", "", "```json",
          json.dumps({k: c[k] for k in ("layers_in_stream_without_rules", "rules_skipped", "deck_scope")}, indent=1), "```", "",
          f"Not covered: layers {c['layers_in_stream_without_rules']} are drawn in the stream and the deck has no rule for them; "
          f"{len(c['rules_skipped'])} deck rules were skipped (list above); only the layer groups in `deck_scope` are in scope. "
          f"`coverage.unchecked_rules` = {c['unchecked_rules']}, `coverage.marker_blind_layers_in_stream` = {c['marker_blind_layers_in_stream']}. "
          "`clean` is the curated deck's verdict on those rules; it is not a claim about rules the deck does not have.", ""]
L += ["## Supporting decks on the analog macro (not the graded report)", "", "```", summary, "```", "",
      "`lydrc` (PDK `sky130A.lydrc`) and `mr` (PDK `sky130A_mr.drc`, `feol=true beol=true thr=1`) are klayout-engine runs: klt labels a zero-finding run "
      "`coverage_unknown`, i.e. **no violation reported, not proven clean**. They are disclosed, not graded; deck-var logic is `design/bitcell/run_drc.sh`. "
      "That these two decks execute is shown by `verification/marker/records/2026-10-17-f22b400.md`, not by this run.", "",
      "## Marker and seam statement (measured)", ""]
m, c_, pc = J("scan-macro.json"), J("scan-control.json"), J("scan-positive-control.json")
L += [f"- `verification/drc/probe.py scan`: macro stream, {m['cells']} cells, shapes on layer 81 = {m['layer_81_shapes'] or 'none'}; **areaid.ce (81/2) shapes = {m['areaid_ce_shapes']}**.",
      f"- control stream, {c_['cells']} cells: layer 81 shapes {c_['layer_81_shapes']}; areaid.ce (81/2) shapes = {c_['areaid_ce_shapes']} (81/4 is the std-cell id marker `areaid.sc`, not the relaxed-rule core marker).",
      f"- scan positive control (one 81/2 box): areaid.ce shapes = {pc['areaid_ce_shapes']}, so a zero above is the scanner seeing none.",
      "- with no 81/2 anywhere, the strict (logic) rule set applies everywhere, including the array/periphery seam; the curated deck is marker-blind and `mr` switches only on 81/2.",
      f"- seam control (`seam/macro_seam_probe.gds` = the macro plus two 0.05 um met1 slivers straddling the array/precharge seam (y 114.1-115.1 um) and the column-mux/array seam (y -0.5-0.9 um)): "
      f"the same curated deck reports status {seam['status']}, rule_counts {seam['rule_counts']}; met1.width.1 at {seam_w} (dbu). A silent zero-rule run at the seam would not have flagged them.", ""]
rec.write_text("\n".join(L))
print(rec)
