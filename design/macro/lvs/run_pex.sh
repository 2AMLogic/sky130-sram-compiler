#!/usr/bin/env bash
# Extract-only PEX capacity probe: can the signoff-pinned klt extract the bare bitcell and
# the 8,192-cell macro, and what body bias does each extraction carry? Supplies the capacity
# and body-bias evidence for #207 (ROADMAP item 7, analog) before the column benches move
# to a pex netlist (#209/#210). No measurement leg, no PDK needed: `--extract-only` is a
# layout-in, netlist+report-out run.
# Usage: design/macro/lvs/run_pex.sh [--report PATH] [--klt CMD] <layout.gds> <top> <outdir>
#   design/macro/lvs/run_pex.sh --self-test <tmpdir>
#     <outdir>: scratch, outside the repo (or under gitignored sim/build/). Each invocation
#     allocates its own unique child <outdir>/<top>.XXXXXX (mktemp -d; nothing is ever
#     removed, so a retry or a concurrent run cannot discard another run's evidence),
#     holding: extracted.spice report.json stdout.json stderr time.v limits.before meta.json
#     Layout, <outdir> and --report paths are resolved relative to the caller's directory.
#     --report PATH also copies a completed run's report.json there (committed evidence);
#     a failed copy fails the wrapper (exit 1).
#     --klt CMD overrides the klt launcher; default `uvx --from klayout-tools==0.9.0 klt`,
#     the signoff.yml pin (host klt is not the pin -- see the dated record for the version
#     actually used; the report's provenance.klt_version is the authority and meta.json
#     records it per run).
# Acceptance (a run is accepted ONLY when every item holds):
#   process exited 4; extracted.spice exists nonempty; report.json parses and has
#   status "not_checked", measurement.mode "extract-only", delta [], a 4-key
#   extraction.model and a body_bias block. An error envelope, a missing netlist, a killed
#   extractor (any exit other than 4, incl. 128+signal) or a malformed report fails the
#   wrapper -- always per run, nothing from an earlier invocation is reused (each run has a
#   fresh scratch and each artifact is re-read). On a failed run the scratch (netlist if
#   written, diagnostics) is preserved for the record: exit 4 also captures the enforced
#   limits (ulimit -v/-m/-d/-s, cgroup memory.max/high) beside host MemTotal/MemAvailable,
#   elapsed time, peak RSS, the last stderr lines, and any terminating signal (reported
#   whatever its cause; RESOURCE_LIMIT is added when a signal or an allocation diagnostic
#   is present).
# Body bias is read from the extraction itself: meta.json carries the report's body_bias
# block verbatim plus the top subckt's pin list, .GLOBAL directives and a histogram of
# device bulk nodes (the bare cell's nfet bulks sit on the deck substrate net `vsubs`,
# exposed as a pin -- the array's drawn taps are what the macro adds). The report's own
# body_bias.status derives from PMOS bulks only (klt 0.9.0 unbiased_pmos_body_nets): it says
# nothing about the NFET bulks on `vsubs`, which a consuming bench must bias itself.
# Exit: 0 accepted extract-only run; 1 TOOL_MISSING/setup; 2 usage; 3 the run completed but
#       its report violates the extract-only contract above; 4 the extractor run itself
#       failed (unexpected exit code, error envelope, killed, no netlist).
# Self-test (--self-test): drives the full run+validate path through a stub klt for the
# failure shapes plus the good shape (its netlist has .GLOBAL before the first .SUBCKT),
# checks a retry into the same <outdir> keeps the first run's evidence, a bad body_bias
# status is rejected, file-level globals are retained, relative paths resolve against the
# caller, a failed --report copy fails, the launcher is probed (--version) before any scratch,
# and the validator summary/diagnostic reaches stdout/stderr. Each self-test allocates its own unique child
# of <tmpdir>. Exits 0 only if every case verdicts as expected.
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
  mkdir -p "$self_test" || { echo "run_pex.sh: cannot create $self_test" >&2; exit 1; }
  T="$(mktemp -d "$(realpath "$self_test")/selftest.XXXXXX")" || { echo "run_pex.sh: mktemp failed" >&2; exit 1; }
  self="$(realpath "${BASH_SOURCE[0]}")"
  stub="$T/stub-klt"; cat > "$stub" <<'STUB'
#!/usr/bin/env bash
# Stub klt for run_pex.sh --self-test. Behaviour keyed by $STUB_MODE.
[ "${1:-}" = "--version" ] && { echo "klt 0.test"; exit 0; }
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
  if [ "${STUB_MODE:-}" = badbias ]; then
    sed -i 's/"status": "biased"/"status": ""/' "$envelope"
  fi
  # file-level .GLOBAL before the first .SUBCKT, as the real deck emits it
  printf '.GLOBAL vsubs\n.SUBCKT t a b vsubs\nM$1 a b vsubs vsubs nfet\n.ENDS\n' > "$scratch"
}
case "${STUB_MODE:?}" in
  good|badbias)  good_report; echo '{}'; exit 4 ;;
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
  run() { "$self" --klt "$stub" "$G" t "$T/$1"; }
  declare -A want=([good]=0 [error-envelope]=4 [no-netlist]=4 [killed]=4 [malformed]=3 [badbias]=3)
  fail=0
  for mode in good error-envelope no-netlist killed malformed badbias; do
    STUB_MODE="$mode" run "case-$mode" >"$T/case-$mode.out" 2>"$T/case-$mode.err"
    got=$?
    [ "$got" -eq "${want[$mode]}" ] && verdict=ok || { verdict=BAD; fail=1; }
    echo "self-test $mode: exit $got (want ${want[$mode]}) $verdict"
  done
  # stdout/stderr content: accepted summary on stdout; specific diagnostics on stderr
  { grep -q 'top=t exit=4 .*devices=6 nets=8 body_bias.status=biased' "$T/case-good.out" \
    && grep -q 'scratch ' "$T/case-good.out" && [ ! -s "$T/case-good.err" ]; } \
    && verdict=ok || { verdict=BAD; fail=1; }
  echo "self-test good-summary-on-stdout: $verdict"
  { grep -q 'report.json unreadable' "$T/case-malformed.err" && grep -q 'scratch preserved at' "$T/case-malformed.err" \
    && grep -q 'unexpected exit 137' "$T/case-killed.err" && grep -q 'killed by OOM' "$T/case-killed.err" \
    && grep -q 'klt: boom' "$T/case-error-envelope.err" && grep -q "body_bias.status=''" "$T/case-badbias.err"; } \
    && verdict=ok || { verdict=BAD; fail=1; }
  echo "self-test rejection-diagnostics-on-stderr: $verdict"
  # launcher pre-flight: missing executable and a multiword launcher whose child is missing
  for L in "$T/no-such-klt" "env no-such-tool-xyz"; do
    STUB_MODE=good "$self" --klt "$L" "$G" t "$T/pre" >"$T/pre.out" 2>"$T/pre.err"; r=$?
    { [ "$r" -eq 1 ] && grep -q TOOL_MISSING "$T/pre.err" && grep -q -- "${L##*/}" "$T/pre.err" && [ ! -e "$T/pre" ]; } \
      && verdict=ok || { verdict=BAD; fail=1; }
    echo "self-test tool-missing '${L##*/}': exit $r (want 1), no scratch $verdict"
  done
  # retry into the SAME outdir: the first run's evidence must survive the second run
  STUB_MODE=good run shared >"$T/shared-1.log" 2>&1; s1=$?
  STUB_MODE=malformed run shared >"$T/shared-2.log" 2>&1; s2=$?
  first=$(sed -n 's/.*scratch \(.*\)$/\1/p' "$T/shared-1.log" | tail -n1)
  second=$(sed -n 's/.*scratch preserved at \(.*\)$/\1/p' "$T/shared-2.log" | tail -n1)
  { [ "$s1" -eq 0 ] && [ "$s2" -eq 3 ] && [ -n "$first" ] && [ -n "$second" ] && [ "$first" != "$second" ] \
    && [ -s "$first/meta.json" ] && [ -s "$first/extracted.spice" ] && [ -s "$second/report.json" ]; } \
    && verdict=ok || { verdict=BAD; fail=1; }
  echo "self-test retry-keeps-first-run: exits $s1,$s2 (want 0,3), distinct scratches $verdict"
  # file-level .GLOBAL retained in meta.json
  g=$(python3 -I -c 'import json,sys; print(" ".join(json.load(open(sys.argv[1]))["netlist"]["globals"]))' "$first/meta.json" 2>/dev/null)
  [ "$g" = "vsubs" ] && verdict=ok || { verdict=BAD; fail=1; }
  echo "self-test file-level-globals: got '$g' (want vsubs) $verdict"
  # relative layout/outdir/report paths resolve against the caller, not the repo root
  mkdir -p "$T/rel"
  ( cd "$(dirname "$G")" && STUB_MODE=good "$self" --klt "$stub" --report "$T/rel/ok.json" "$(basename "$G")" t "$T/rel/out" ) >"$T/rel.log" 2>&1; r=$?
  { [ "$r" -eq 0 ] && [ -s "$T/rel/ok.json" ]; } && verdict=ok || { verdict=BAD; fail=1; }
  echo "self-test caller-relative-paths: exit $r (want 0) $verdict"
  # a --report whose parent is missing must fail, not silently succeed
  STUB_MODE=good "$self" --klt "$stub" --report "$T/no/such/dir/r.json" "$G" t "$T/rep" >"$T/rep.log" 2>&1; r=$?
  { [ "$r" -ne 0 ] && [ ! -e "$T/no/such/dir/r.json" ]; } && verdict=ok || { verdict=BAD; fail=1; }
  echo "self-test report-copy-failure: exit $r (want nonzero) $verdict"
  [ "$fail" -eq 0 ] && echo "run_pex.sh self-test: PASS" || echo "run_pex.sh self-test: FAIL" >&2
  exit "$fail"
fi

[ $# -eq 3 ] || { echo "run_pex.sh: usage: run_pex.sh [--report PATH] [--klt CMD] <layout.gds> <top> <outdir>" >&2; exit 2; }
G=$1; TOP=$2; O=$3
# Parse the launcher into arguments ONCE; the probe and the extraction use the same array.
read -r -a KLT_ARR <<< "$KLT"
[ "${#KLT_ARR[@]}" -gt 0 ] || { echo "run_pex.sh: TOOL_MISSING: empty klt command" >&2; exit 1; }
for t in python3 /usr/bin/time "${KLT_ARR[0]}"; do
  command -v "$t" >/dev/null || { echo "run_pex.sh: TOOL_MISSING: $t not on PATH" >&2; exit 1; }
done
# Probe the full launcher (not just its first word): a launcher such as `uvx ... klt` must
# actually be able to run the requested tool. Done before any scratch is allocated.
timeout 300 "${KLT_ARR[@]}" --version >/dev/null 2>&1 \
  || { echo "run_pex.sh: TOOL_MISSING: '$KLT --version' failed (launcher or tool unavailable)" >&2; exit 1; }
[ -f "$G" ] || { echo "run_pex.sh: NO_INPUT: $G is not a file" >&2; exit 1; }
# Resolve every caller-supplied path against the caller's directory BEFORE changing directory.
G=$(realpath "$G"); GSRC=$G
[ -z "$report" ] || report=$(realpath -m "$report")
mkdir -p "$O" || { echo "run_pex.sh: cannot create outdir $O" >&2; exit 1; }
O=$(realpath "$O")
cd "$repo"
scratch=$(mktemp -d "$O/$TOP.XXXXXX") && [ -d "$scratch" ] \
  || { echo "run_pex.sh: cannot allocate a scratch directory under $O" >&2; exit 1; }

# Resource-limit context, recorded before the run (the limits a killed run hit): host memory
# plus the limits actually enforced on this process (ulimit, cgroup v2/v1) where available.
{
  grep -E '^(MemTotal|MemAvailable):' /proc/meminfo 2>/dev/null | tr -d ' ' | sed 's/kB$//; s/:/_kb=/; s/^/host_/'
  echo "ulimit_v_kb=$(ulimit -v)"; echo "ulimit_m_kb=$(ulimit -m)"
  echo "ulimit_d_kb=$(ulimit -d)"; echo "ulimit_s_kb=$(ulimit -s)"
  cgp=$(sed -n 's/^0:://p' /proc/self/cgroup 2>/dev/null)
  for f in "/sys/fs/cgroup$cgp/memory.max" "/sys/fs/cgroup$cgp/memory.high" /sys/fs/cgroup/memory.max \
           /sys/fs/cgroup/memory/memory.limit_in_bytes; do
    [ -r "$f" ] && echo "cgroup_$(basename "$f")=$(cat "$f" 2>/dev/null) # $f"
  done
} > "$scratch/limits.before"

# The capacity probe itself. --outdir keeps klt's own .klt/pex/ artifacts in the scratch,
# out of the repo tree next to the layout. Everything else is the issue-#208 contract verb.
/usr/bin/time -v -o "$scratch/time.v" -- "${KLT_ARR[@]}" pex "$GSRC" --top "$TOP" --deck sky130 \
  --extract-only --outdir "$scratch/klt-outdir" \
  -o "$scratch/extracted.spice" --envelope-out "$scratch/report.json" \
  --format json > "$scratch/stdout.json" 2> "$scratch/stderr"
rc=$?

vout=$(python3 -I - "$scratch" "$G" "$TOP" "$rc" "$KLT" <<'PY'
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
    elif re.search(r"terminated (by|with) signal|died with non-zero signal", ln):
        m = re.search(r"signal (\d+)", ln)
        signal = int(m.group(1)) if m else -1
if signal is None and rc > 128:
    signal = rc - 128                           # shell-style 128+N from the child's status
out.update(elapsed_s=elapsed_s, peak_rss_kb=peak_rss_kb, exit_signal=signal)
limits = {}
for ln in open(f"{scratch}/limits.before"):
    k, _, v = ln.rstrip("\n").partition("=")
    v = v.split(" # ")[0].strip()
    limits[k] = int(v) if v.isdigit() else v
out["limits_at_start"] = limits                 # host_MemTotal/MemAvailable in kB, ulimits, cgroup

def finish(code, reason, summary):
    out["verdict"], out["reason"] = ("accepted", None) if code == 0 else ("rejected", reason)
    json.dump(out, open(f"{scratch}/meta.json", "w"), indent=1, sort_keys=True)
    print(summary)
    print(f"verdict={'accepted' if code == 0 else 'rejected:' + str(reason)}")
    sys.exit(code)

if rc != 4:
    tail = open(f"{scratch}/stderr").read().splitlines()[-5:]
    out["last_diagnostic"] = tail
    sig = f"; terminated by signal {signal}" if signal is not None else ""
    alloc = re.search(r"alloc|out of memory|cannot allocate|bad_alloc|memoryerror", " ".join(tail), re.I)
    kind = f"unexpected exit {rc}{sig}"
    if signal is not None or alloc:
        kind = f"RESOURCE_LIMIT ({kind}; enforced limits: {limits})"
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
if not isinstance(bb, dict):
    why.append("body_bias block missing")
else:
    if bb.get("status") not in ("biased", "unbiased"):
        why.append(f"body_bias.status={bb.get('status')!r} not biased/unbiased")
    if not isinstance(bb.get("unbiased_nets"), list) or not all(isinstance(n, str) for n in bb["unbiased_nets"]):
        why.append("body_bias.unbiased_nets missing or not a list of strings")
    c = bb.get("unbiased_device_count")
    if not isinstance(c, int) or isinstance(c, bool):
        why.append("body_bias.unbiased_device_count missing or not an int")
    if not isinstance(bb.get("unbiased_pmos_body_nets"), list):
        why.append("body_bias.unbiased_pmos_body_nets missing or not a list")
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
in_top = in_sub = False
for ln in nl.splitlines():
    s = ln.strip()
    if s.upper().startswith(".GLOBAL"):         # file-level (outside any .SUBCKT) or in the top
        if not in_sub or in_top:
            globs += [g for g in s.split()[1:] if g not in globs]
    elif s.upper().startswith(".SUBCKT"):
        in_sub = True
        in_top = s.split()[1] == top
        if in_top:
            pins = s.split()[2:]
    elif s.upper().startswith(".ENDS"):
        in_sub = in_top = False
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
)
vrc=$?
# The validator prints its summary/diagnostic lines, then a final verdict= line; its exit
# status (0 accepted, 3 contract violation, 4 extractor failure) is kept separately.
verdict=$(printf '%s\n' "$vout" | tail -n1)
summary=$(printf '%s\n' "$vout" | sed '$d')
verdict="${verdict#verdict=}"

case "$verdict" in
  accepted)
    if [ "$vrc" -ne 0 ]; then
      echo "run_pex.sh: $TOP validator reported accepted but exited $vrc; scratch $scratch" >&2
      exit 1
    fi
    echo "run_pex.sh: $summary"
    if [ -n "$report" ] && ! cp "$scratch/report.json" "$report"; then
      echo "run_pex.sh: $TOP accepted but publishing the report to $report FAILED; scratch $scratch" >&2
      exit 1
    fi
    echo "run_pex.sh: $TOP extract-only accepted; scratch $scratch"
    exit 0 ;;
  *)
    [ "$vrc" -ne 0 ] || vrc=1
    [ -z "$summary" ] || echo "run_pex.sh: $summary" >&2
    echo "run_pex.sh: $TOP extract-only FAILED (${verdict:-validator produced no verdict; exit $vrc}); scratch preserved at $scratch" >&2
    exit "$vrc" ;;
esac
