#!/usr/bin/env bash
# Extract-only PEX capacity probe: can the signoff-pinned klt extract the bare bitcell and
# the 8,192-cell macro, and what body bias does each extraction carry? Supplies the capacity
# and body-bias evidence for #207 (ROADMAP item 7, analog) before the column benches move
# to a pex netlist (#209/#210). No measurement leg, no PDK needed: `--extract-only` is a
# layout-in, netlist+report-out run.
# Usage: design/macro/lvs/run_pex.sh [--report PATH] [--klt CMD] <layout.gds> <top> <outdir>
#   design/macro/lvs/run_pex.sh --self-test <tmpdir>
#     <outdir>: scratch, outside the repo (or under gitignored sim/build/). One fresh
#     <outdir>/<top>/ per invocation (wiped first), holding:
#       extracted.spice  report.json  stdout.json  stderr  time.v  meta.json
#     --report PATH also copies a completed run's report.json there (committed evidence).
#     --klt CMD overrides the klt launcher; default `uvx --from klayout-tools==0.9.0 klt`,
#     the signoff.yml pin (host klt is not the pin -- see the dated record for the version
#     actually used; the report's provenance.klt_version is the authority and meta.json
#     records it per run).
# Acceptance (a run is accepted ONLY when every item holds):
#   process exited 4; extracted.spice exists nonempty; report.json parses and has
#   status "not_checked", measurement.mode "extract-only", delta [], a 4-key
#   extraction.model and a body_bias block. An error envelope, a missing netlist, a killed
#   extractor (any exit other than 4, incl. 128+signal) or a malformed report fails the
#   wrapper -- always per run, nothing from an earlier invocation is reused (the scratch is
#   wiped and each artifact is re-read). On a failed run the scratch (layout copy reference,
#   netlist if written, diagnostics) is preserved for the record: exit 4 also captures the
#   resource limit (host MemTotal/MemAvailable), elapsed time, peak RSS and the last
#   stderr lines as a RESOURCE_LIMIT line when the process died to a signal.
# Body bias is read from the extraction itself: meta.json carries the report's body_bias
# block verbatim plus the top subckt's pin list, .GLOBAL directives and a histogram of
# device bulk nodes (the bare cell's nfet bulks sit on the deck substrate net `vsubs`,
# exposed as a pin -- the array's drawn taps are what the macro adds).
# Exit: 0 accepted extract-only run; 1 TOOL_MISSING/setup; 2 usage; 3 the run completed but
#       its report violates the extract-only contract above; 4 the extractor run itself
#       failed (unexpected exit code, error envelope, killed, no netlist).
# Self-test (--self-test): drives the full run+validate path through a stub klt for the
# five failure shapes plus the good shape, reusing one scratch for a success followed by a
# malformed report (validation must fail on the second run all the same). Exits 0 only if
# every case verdicts as expected.
set -uo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
KLT="uvx --from klayout-tools==0.9.0 klt"
report=""
self_test=""

usage() { sed -n '2,30p' "${BASH_SOURCE[0]}"; exit 2; }
while [ $# -gt 0 ]; do
  case "$1" in
    --report) [ $# -ge 2 ] || usage; report=$2; shift 2 ;;
    --klt) [ $# -ge 2 ] || usage; KLT=$2; shift 2 ;;
    --self-test) [ $# -ge 2 ] || usage; self_test=$2; shift 2 ;;
    -h|--help) usage ;;
    --*) echo "run_pex.sh: usage: unknown option $1" >&2; exit 2 ;;
    *) break ;;
  esac
done

if [ -n "$self_test" ]; then
  # ---- self-test: stub klt per scenario, full wrapper path, expected verdicts -------------
  T="$(realpath -m "$self_test")"; rm -rf "$T"; mkdir -p "$T"
  stub="$T/stub-klt"; cat > "$stub" <<'STUB'
#!/usr/bin/env bash
# Stub klt for run_pex.sh --self-test. Behaviour keyed by $STUB_MODE.
scratch="" ; prev=""
for a in "$@"; do
  [ "$prev" = "-o" ] && scratch="$a"
  [ "$prev" = "--envelope-out" ] && envelope="$a"
  prev="$a"
done
good_report() {
  cat > "$envelope" <<'JSON'
{"schema_version": 2, "status": "not_checked",
 "measurement": {"mode": "extract-only", "command": null, "timeout_s": null, "sides": null},
 "delta": [], "testbenches": [],
 "extraction": {"deck": "sky130", "device_count": 6, "net_count": 8, "netlist_sha256": "x",
   "model": {"capacitance": "c", "coupling": "k", "resistance": "r", "frequency": "f"}},
 "body_bias": {"status": "biased", "unbiased_device_count": 0, "unbiased_nets": [],
   "unbiased_pmos_body_nets": []},
 "provenance": {"klt_version": "0.test", "deck": {"name": "sky130"}}}
JSON
  printf '.SUBCKT t a b vsubs\nM$1 a b vsubs vsubs nfet\n.ENDS\n' > "$scratch"
}
case "${STUB_MODE:?}" in
  good)          good_report; echo '{}'; exit 4 ;;
  malformed)     printf '{"status": "not_checked", oops' > "$envelope"; exit 4 ;;
  error-envelope) printf '{"error": {"code": "extraction_failed", "message": "boom"}}' > "$envelope"
                 echo '{"error": {"code": "extraction_failed"}}'; echo "klt: boom" >&2; exit 1 ;;
  no-netlist)    good_report; rm -f "$scratch"; exit 4 ;;
  killed)        echo "klt(1) killed by OOM killer" >&2; exit 137 ;;
esac
echo "stub: no such STUB_MODE" >&2; exit 99
STUB
  chmod +x "$stub"
  G="$repo/design/bitcell/bitcell_6t.gds"
  run() { "$0" --klt "$stub" "$G" t "$T/$1"; }
  declare -A want=([good]=0 [error-envelope]=4 [no-netlist]=4 [killed]=4 [malformed]=3)
  fail=0
  for mode in good error-envelope no-netlist killed malformed; do
    STUB_MODE="$mode" run "case-$mode" >"$T/case-$mode.log" 2>&1
    got=$?
    [ "$got" -eq "${want[$mode]}" ] && verdict=ok || { verdict=BAD; fail=1; }
    echo "self-test $mode: exit $got (want ${want[$mode]}) $verdict"
  done
  # success then malformed report in the SAME scratch: the second run must still fail
  STUB_MODE=good run shared >"$T/shared-1.log" 2>&1; s1=$?
  STUB_MODE=malformed run shared >"$T/shared-2.log" 2>&1; s2=$?
  { [ "$s1" -eq 0 ] && [ "$s2" -eq 3 ]; } && verdict=ok || { verdict=BAD; fail=1; }
  echo "self-test good-then-malformed (same scratch): exits $s1,$s2 (want 0,3) $verdict"
  [ "$fail" -eq 0 ] && echo "run_pex.sh self-test: PASS" || echo "run_pex.sh self-test: FAIL" >&2
  exit "$fail"
fi

[ $# -eq 3 ] || { echo "run_pex.sh: usage: run_pex.sh [--report PATH] [--klt CMD] <layout.gds> <top> <outdir>" >&2; exit 2; }
G=$1; TOP=$2; O=$3
for t in "$KLT" python3 /usr/bin/time; do
  # shellcheck disable=SC2086
  command -v $t >/dev/null || { echo "run_pex.sh: TOOL_MISSING: $t not on PATH" >&2; exit 1; }
done
[ -f "$G" ] || { echo "run_pex.sh: NO_INPUT: $G is not a file" >&2; exit 1; }
cd "$repo"
G=$(realpath "$G"); GSRC=$G
mkdir -p "$O"; O=$(realpath "$O")
scratch="$O/$TOP"; rm -rf "$scratch"; mkdir -p "$scratch"   # fresh per invocation

# Resource-limit context, recorded before the run (the limit a killed run hit).
grep -E '^(MemTotal|MemAvailable):' /proc/meminfo > "$scratch/meminfo.before" 2>/dev/null || true

# The capacity probe itself. --outdir keeps klt's own .klt/pex/ artifacts in the scratch,
# out of the repo tree next to the layout. Everything else is the issue-#208 contract verb.
# shellcheck disable=SC2086
/usr/bin/time -v -o "$scratch/time.v" -- $KLT pex "$GSRC" --top "$TOP" --deck sky130 \
  --extract-only --outdir "$scratch/klt-outdir" \
  -o "$scratch/extracted.spice" --envelope-out "$scratch/report.json" \
  --format json > "$scratch/stdout.json" 2> "$scratch/stderr"
rc=$?

# shellcheck disable=SC2086
verdict=$(python3 -I - "$scratch" "$G" "$TOP" "$rc" "$KLT" <<'PY'
import json, re, sys

scratch, layout, top, rc, klt_cmd = sys.argv[1:6]
rc = int(rc)
out = {"klt_command": klt_cmd, "layout": layout, "top": top, "exit_code": rc}

# --- GNU time -v: wall time, peak RSS, terminating signal ---
elapsed_s = peak_rss_kb = signal = None
tv = open(f"{scratch}/time.v").read().splitlines()
for ln in tv:
    if "Elapsed (wall clock) time" in ln:
        t = ln.split("):")[-1].strip().split(":")   # after "(h:mm:ss or m:ss):"
        elapsed_s = round(sum(float(x) * 60 ** i for i, x in enumerate(reversed(t))), 2)
    elif "Maximum resident set size" in ln:
        peak_rss_kb = int(ln.rsplit(":", 1)[1])
    elif "terminated with signal" in ln or "died with non-zero signal" in ln:
        m = re.search(r"signal (\d+)", ln)
        signal = int(m.group(1)) if m else -1
out.update(elapsed_s=elapsed_s, peak_rss_kb=peak_rss_kb, exit_signal=signal)
mem = {}
for ln in open(f"{scratch}/meminfo.before"):
    k, v = ln.split(":", 1)
    mem[k] = int(v.strip().split()[0])  # kB
out["host_memory_kb_at_start"] = mem

def finish(code, reason, summary):
    out["verdict"], out["reason"] = ("accepted", None) if code == 0 else ("rejected", reason)
    json.dump(out, open(f"{scratch}/meta.json", "w"), indent=1, sort_keys=True)
    print(summary)
    print(f"verdict={'accepted' if code == 0 else 'rejected:' + str(reason)}")
    sys.exit(code)

if rc != 4:
    tail = open(f"{scratch}/stderr").read().splitlines()[-5:]
    out["last_diagnostic"] = tail
    kind = f"RESOURCE_LIMIT (signal {signal})" if signal is not None else f"unexpected exit {rc}"
    finish(4, kind, f"{kind}; stderr tail: {tail}")

# --- the report: malformed / error envelope / contract ---
try:
    d = json.load(open(f"{scratch}/report.json"))
except Exception as e:
    finish(3, f"report.json unreadable ({e})", f"report.json unreadable ({e})")
if not isinstance(d, dict) or "error" in d or d.get("status") == "error":
    err = d.get("error") if isinstance(d, dict) else None
    finish(4, f"error envelope {err}", f"error envelope: {err}")
why = []
if d.get("status") != "not_checked": why.append(f"status={d.get('status')!r}")
m = d.get("measurement") or {}
if m.get("mode") != "extract-only": why.append(f"measurement.mode={m.get('mode')!r}")
if d.get("delta") != []: why.append(f"delta={d.get('delta')!r}")
model = (d.get("extraction") or {}).get("model") or {}
for k in ("capacitance", "coupling", "resistance", "frequency"):
    if not isinstance(model.get(k), str) or not model[k]: why.append(f"model.{k} missing")
bb = d.get("body_bias")
if not isinstance(bb, dict) or not isinstance(bb.get("status"), str) \
        or not isinstance(bb.get("unbiased_nets"), list):
    why.append("body_bias block missing or malformed")
if why:
    finish(3, "; ".join(why), f"report violates extract-only contract: {'; '.join(why)}")

# --- the netlist: present, nonempty, and its own body-bias facts ---
try:
    nl = open(f"{scratch}/extracted.spice").read()
except FileNotFoundError:
    finish(4, "extracted.spice missing", "extracted.spice missing")
if not nl.strip():
    finish(4, "extracted.spice empty", "extracted.spice empty")
pins, globs, bulk = [], [], {}
in_top = False
for ln in nl.splitlines():
    s = ln.strip()
    if s.upper().startswith(".SUBCKT"):
        in_top = s.split()[1] == top
        if in_top:
            pins = s.split()[2:]
    elif in_top and s.upper().startswith(".GLOBAL"):
        globs = s.split()[1:]
    elif in_top and re.match(r"^M\S+", s):
        b = s.split()[4]                      # M d g s b model
        base = re.sub(r"__t\d+$", "", b)      # star-network terminal nodes -> net
        bulk[base] = bulk.get(base, 0) + 1
ex = d["extraction"]
out["report"] = {"status": d["status"], "measurement_mode": m["mode"], "delta_rows": len(d["delta"]),
                 "klt_version": (d.get("provenance") or {}).get("klt_version"),
                 "deck": ex.get("deck"), "device_count": ex.get("device_count"),
                 "net_count": ex.get("net_count"), "netlist_sha256": ex.get("netlist_sha256")}
out["body_bias"] = bb
out["netlist"] = {"pins": pins, "globals": globs, "device_bulk_nets": dict(sorted(bulk.items(), key=lambda kv: -kv[1]))}
finish(0, None,
       f"top={top} exit=4 elapsed={elapsed_s}s peak_rss={peak_rss_kb}kB "
       f"devices={ex.get('device_count')} nets={ex.get('net_count')} "
       f"body_bias.status={bb['status']} unbiased_nets={bb['unbiased_nets']} "
       f"bulk_nets={list(out['netlist']['device_bulk_nets'])[:6]}")
PY
) || verdict="rc=$?"
verdict="$(printf '%s\n' "$verdict" | tail -n1)"   # the validator's verdict= line (summary precedes it)
verdict="${verdict#verdict=}"

case "$verdict" in
  accepted)
    [ -z "$report" ] || cp "$scratch/report.json" "$report"
    echo "run_pex.sh: $TOP extract-only accepted; scratch $scratch"
    exit 0 ;;
  *)
    echo "run_pex.sh: $TOP extract-only FAILED ($verdict); scratch preserved at $scratch" >&2
    exit "${verdict#rc=}" ;;
esac
