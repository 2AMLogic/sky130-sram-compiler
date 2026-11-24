# Work Log

Chronological record of merged pull requests and closed issues, newest first.
Maintained by the Loom Guide role; entries are appended automatically.

### 2026-11-24

- **PR #237**: docs(sim): add provenance record for SNM PEX col_*_snm probe column
- **PR #233**: docs(column): disclose word-line wire truncation in PEX record and README
- **Issue #236** (closed): SNM PEX record: cite provenance for the 'Committed col_*_snm probe (pre-layout)' column
- **Issue #232** (closed): Name the word-line wire truncation in the column-slice PEX record's Scope section
- **PR #231**: feat(sim): add extracted-DUT SNM measurement path and provisional PEX comparison record
- **Issue #210** (closed): Measure provisional hold and read SNM on the extracted half-cell fixture
- **Issue #207** (closed): T1 item 7 (post-layout, analog): prove the klt pex route on the bitcell and 256x32 macro, with a provisional one-corner delta on the column benches
- **PR #225**: feat: provisional read/write PEX deltas on an LVS-matched column slice
- **Issue #209** (closed): Measure provisional read and write deltas on an LVS-matched column slice
- **PR #229**: feat: add decoupled half-cell column top for DC SNM fixture
- **Issue #228** (closed): Dedicated half-cell column top for the DC SNM fixture, DRC/LVS clean
- **PR #220**: fix(pex): probe launched klt and surface validator summary
- **Issue #219** (closed): run_pex.sh: TOOL_MISSING pre-flight does not actually check the launched tool, and the validator summary never prints

### 2026-11-23

- **PR #224**: refactor: split gen_layout.build() into per-section helpers
- **Issue #223** (closed): Split gen_layout.build() into per-section helpers and drop three vestigial redundancies
- **PR #216**: feat: add PEX extract-only capacity wrapper, record bitcell and macro results
- **Issue #208** (closed): Measure bitcell and full-macro PEX capacity and body bias
- **PR #214**: test: build column record fixtures from the writer's BENCHES roster
- **Issue #213** (closed): Deduplicate column record test fixtures and verify which request is missing

### 2026-11-20

- **PR #212**: feat: verify the routed sram_ctrl with an SDF-annotated cocotb re-run (T1 item 7 digital)
- **Issue #206** (closed): T1 item 7 (post-layout, digital): SDF-annotated klt functional-verification of the routed sram_ctrl

### 2026-11-18

- **PR #204**: ci: add merge_group trigger to required-check workflows
- **Issue #202** (closed): Merge queue: add the merge_group trigger to the required-check workflow(s)

### 2026-11-17

- **PR #200**: ci: gate the unused-name class with pinned pyflakes in hygiene.yml
- **Issue #197** (closed): Suggestion: gate the unused-name class in CI (pyflakes step in hygiene.yml)
- **PR #196**: fix: remove four unused names pyflakes reports (math, re, sys, tmp) and re-attest item 1
- **Issue #194** (closed): Remove four remaining unused names pyflakes reports: math in sram_compile.py (left over from #82), re, sys, tmp
- **PR #193**: test: run the ERC exit gate in a scratch copy of the tree
- **Issue #189** (closed): test_erc_exit_gate.py mutates the live layout/erc/*.json evidence; test_drc_exit_gate.py's scratch-repo pattern does not
- **PR #192**: fix: pass --untracked-files=normal explicitly in git_short_sha's dirty probe
- **Issue #186** (closed): git_short_sha's untracked-file half of the dirty check can be silenced by a user git config
- **PR #188**: fix: gate layout/erc klt erc exits and validate envelopes before the --write copy
- **Issue #185** (closed): Gate klt erc exit codes in run_erc.sh and validate reports before the --write copy
- **PR #184**: fix: gate verification/drc klt drc exit codes and validate evidence envelopes before copying
- **Issue #183** (closed): verification/drc/run_drc.sh discards every klt drc exit code (|| true x3) and make_record.py clobbers committed evidence before parsing it
- **PR #152**: fix: stamp a dirty working tree <sha>-dirty in record provenance sha
- **Issue #151** (closed): A record can be stamped with a commit that cannot reproduce it: git_short_sha never checks the tree is clean
- **PR #180**: chore(loom): resync installed Loom to v0.19.1306
- **PR #179**: fix: format gate enumerates with git ls-files -z so space-bearing tracked files are validated and named, not fragmented
- **Issue #178** (closed): check_formats.py: git ls-files enumeration has the same whitespace split #159 fixed — a space-bearing tracked .json is silently never validated
- **PR #177**: test: pin the read-1 waveform.raw.json refusal in make_column_record
- **Issue #176** (closed): Add a RefusesBeforeWritingEvidence case for the read-bench waveform.raw.json path in make_column_record
- **PR #175**: fix: read the per-corner waveform artifacts before the column evidence dir is written
- **Issue #174** (closed): make_column_record.py: per-corner waveform.raw.json reads still land after ev.mkdir, and the #172 comment now overstates the guarantee
- **PR #173**: fix: read the repo-tracked record inputs before the evidence dir is written
- **Issue #172** (closed): Record writers still read design/bitcell/sizing.json (and the column request files) after the evidence gzips land
- **PR #171**: fix: read --base-record and --job-log before the controls evidence dir is written
- **Issue #168** (closed): make_controls_record: --base-record and --job-log are still read after the evidence gzips land
- **PR #170**: refactor: write column evidence via record_common.save_gz_json
- **Issue #155** (closed): Use save_gz_json in make_column_record.py instead of an inline gzip writer
- **PR #161**: fix: enumerate committed records/ dirs via NUL-delimited git ls-files
- **Issue #159** (closed): check_reproduce_coverage.py: git ls-files enumeration mangles paths containing whitespace

### 2026-11-16

- **PR #169**: chore(loom): resync installed Loom to v0.19.1305
- **PR #167**: fix: load every record input before the evidence directory is written
- **Issue #129** (closed): Record writers interleave scratch-report reads with evidence writes, so a bad report orphans the earlier gzips
- **PR #146**: chore(loom): resync installed Loom to v0.19.1302
- **Issue #145** (closed): verification/hygiene/test_pdk_resolution.py is a fifth PDK-free suite that #88's ACs do not enumerate (and its docstring names the wrong unwired precedent)
- **PR #164**: test: wire the PDK-resolution suite into hygiene CI and re-attest item 10
- **Issue #153** (closed): Dedupe xschem device-stub emitter duplicated in the two gen_schematic.py generators
- **PR #163**: refactor: share xschem device-stub emitter via sky130_pdk.SchematicWriter
- **Issue #122** (closed): No check that every committed records/ directory is covered by the README Reproduce section
- **PR #158**: feat(hygiene): gate Reproduce-table coverage of committed records/ dirs
- **PR #150**: fix: remove dangling worktree:return npm script (target retired upstream)
- **PR #149**: fix(lvs): read make_ref.py inputs via pathlib.read_text, document exit-1 overloading
- **PR #148**: test: probe every guarded member of each --check gate via per-gate globs
- **PR #144**: docs: pin the item-10 regen command to the klt pin hygiene.yml validates with
- **PR #143**: docs: drop stale refactor-attribution clauses from manifests/README.md
- **PR #139**: fix: resolve the deck runners' PDK dir from the variant name, not PDK itself
- **PR #136**: fix: re-attest item 9 to the dac33fa/284d94b member hashes
- **PR #132**: fix: refuse to write the bitcell record on a failed DRC/LVS compare
- **PR #130**: fix(lvs): anchor the bitcell negative control on the literal the netlist carries
- **PR #126**: refactor(records): consolidate the deterministic gzip-JSON write into record_common.save_gz_json()
- **PR #115**: ci: wire ladder-seam, erc-spec and layout suites into hygiene CI; re-attest item 10
- **Issue #142** (closed): Ruleset strict required-checks policy blocks every BEHIND PR from merging
- **Issue #147** (closed): package.json: drop dangling worktree:return script (target retired upstream)
- **Issue #141** (closed): manifests/README.md: name the klt pin that regenerates the item-10 attestation envelope
- **Issue #140** (closed): manifests/README.md L118: item-9 re-attestation attributed to the wrong change (make_column_tb.py refactor)
- **Issue #138** (closed): bitcell LVS: make_ref.py is the only design/ Python using json.load(open(...)); emits ResourceWarnings into the test output
- **Issue #137** (closed): Drift suite probes one artifact per --check gate; gates guarding 9-18 files can stop comparing the rest silently
- **Issue #133** (closed): main is red: signoff item 9 stale_evidence after dac33fa/284d94b — re-attest item 9 and regenerate the record
- **Issue #131** (closed): three_deck_drc.sh: PDK override collides with sim/env.sh's PDK (variant name), breaking the mr deck lookup
- **Issue #104** (closed): Fold the repeated gzip-JSON write and sha256 helpers into record_common
- **Issue #99** (closed): Bitcell LVS negative-control anchor corrupts the control netlist for integer-valued ax.w
- **Issue #95** (closed): make_record.py bakes a failed DRC/LVS compare into an append-only record: check the runners' returncodes
- **Issue #88** (closed): Wire the PDK-free test suites into the hygiene CI inventory (needs an item-10 re-attestation)

### 2026-11-15

- **PR #123**: docs(marker): add 2026-11-15 re-run record with per-deck drift attribution
- **PR #118**: test: assert hygiene --check gates exit non-zero on drift
- **Issue #108** (closed): Marker study: counts have drifted from the 2026-10-17 record on the current klt pin — new dated record needed
- **Issue #105** (closed): No test asserts any generator's --check actually exits non-zero on drift
- **PR #127**: fix(evidence): resolve git provenance before any evidence write in make_column_record.py
- **PR #125**: chore(evidence): back-fill the bitcell harness into the item-9 inventory
- **PR #121**: refactor: consolidate record provenance lookups onto record_common
- **PR #110**: fix: derive the write-trip ladder prose in the record generators from tb_common.LADDER
- **PR #106**: fix: make the bitcell GDS writer deterministic and gate it with --check
- **Issue #134** (closed): main: klt signoff red since #110 — re-attest item 9 (sim/bitcell record generators changed under a stale envelope)
- **Issue #128** (closed): The bitcell record_common test file is never run by CI (25 tests, including the new gzip byte-reproducibility gate)
- **Issue #119** (closed): T1 item 9 grades analog 'met' while sim/testbench-inventory.json omits every bitcell testbench but one
- **Issue #116** (closed): Consolidate the duplicated provenance guard in verification/drc and guard design/bitcell make_record
- **Issue #114** (closed): make_column_record.py writes evidence before resolving the sha, so a provenance failure leaves orphaned gzips (needs item-9 re-attestation)
- **Issue #103** (closed): Guard the remaining discarded-return-code provenance lookups in record writers (sha, klt version)
- **Issue #94** (closed): Marker run_checks.sh: three-deck loop duplicates run_drc.sh, klt stderr discarded, and the README's control is never asserted
- **Issue #91** (closed): Write-MC record prose hardcodes the ladder step (/32) while the data now derives from tb_common.LADDER
- **Issue #67** (closed): bitcell GDS is not byte-reproducible: gen_bitcell.py writes klayout timestamps into the GDS header
- **PR #120**: docs: name layout/records/ as a historical dev-checks record in the Reproduce preamble
- **PR #117**: refactor(sim): remove dead corner-grid imports and unused column-TB symbols
- **PR #113**: fix: refuse record writes on a failed provenance lookup (git sha, klt version)
- **PR #112**: ci(hygiene): run the column drift gate and sweep check_formats coverage to the tracked tree
- **PR #111**: fix: remove five unused names the pyflakes pass finds (POLY_DIFF, NW_P, dead gl import, allw, empty f-string)
- **PR #102**: feat(hygiene): gate the bitcell schematic on its generator with a --check mode
- **PR #101**: refactor(verification): one shared three-deck klt drc helper, assert the stripped-marker control
- **PR #90**: chore: drop unused point_key import from make_controls_record.py
- **Issue #93** (closed): Remove five more unused names the pyflakes pass finds: POLY_DIFF, NW_P, gen_erc_spec's gl, allw, an empty f-string
- **Issue #89** (closed): Remove the unused PROCESS/TEMPS/VDDS imports in both testbench generators, and the stale noqa: F401 hiding them
- **Issue #84** (closed): README Reproduce table: layout/records/ has no reproduce row
- **Issue #82** (closed): Remove two unused imports: point_key in make_controls_record.py (free) and math in sram_compiler.py (needs an item 1+2 re-attestation)
- **Issue #80** (closed): make_column_tb.py --check is not run by CI, so column bench/request drift is unguarded
- **Issue #75** (closed): design/bitcell/gen_schematic.py has no --check mode, so the generated bitcell_6t.sch has no regeneration gate
- **PR #96**: fix(lvs): gate bitcell LVS on its expected-status table, derive the control width from sizing.json
- **PR #92**: refactor(compiler): name build()'s geometry return instead of locals()
- **Issue #107** (closed): CI never runs sim/bitcell/lib/test_record_common.py: add it to hygiene.yml and the item-10 inventory
- **Issue #78** (closed): design/bitcell/lvs/run_lvs.sh computes an expected-status table it never checks: a desynced negative control reports match and exits 0
- **Issue #74** (closed): Narrow gen_layout.build()'s locals() return to the two fields callers actually use

### 2026-11-14

- **PR #100**: fix: guard the append-only DRC record before copying evidence over committed files
- **PR #87**: refactor(sim): declare the write-trip ladder length once and reject a wrong-length ladder loudly
- **PR #77**: docs: add the nine missing Reproduce rows and resync the status line and repo layout
- **Issue #98** (closed): verification/drc/make_record.py overwrites the committed item-3 evidence before its append-only guard
- **Issue #76** (closed): Declare the write-trip LADDER length once: make_tb.py and record_common.py each define LADDER = 33
- **Issue #73** (closed): README: bring the status line, Reproduce table and repo layout up to the tree
- **PR #86**: feat(evidence): attest both T1 item 2 envelopes with klt signoff --attest 2
- **PR #81**: fix: derive sim/column batch unit caps from timeout_s and bound shard concurrency
- **Issue #85** (closed): check_formats.py's JSON globs miss the item-2 inventories and evidence/item2-digital.json
- **Issue #79** (closed): check_formats.py PY_GLOBS is still a hand-maintained list: 7 tracked project .py files are not syntax-checked
- **Issue #72** (closed): Produce the T1 item 2 analog envelope with `klt signoff --attest 2` and retire attest_layout.py
- **Issue #71** (closed): Regenerate the six over-limit sim/column batch requests and correct the stale fleet note
- **Issue #69** (closed): Remove the dead init_drivers() helper and the ignored cells_hs parameter from the column testbench generator
- **PR #66**: refactor(design): take the sky130 layer table and PDK drawing rules from one module
- **PR #70**: docs: roadmap as of 2026-11-13
- **Issue #65** (closed): Deduplicate the sky130 layer table and PDK drawing constants shared by the bitcell and compiler generators
- **Issue #68** (closed): check_formats.py PY_GLOBS misses design/*.py, and fixing it requires regenerating the item-10 attestation

### 2026-11-12

- **PR #61**: Bump Repo Skills 0.25.10 -> 0.26.1

### 2026-11-07

- **PR #60**: Bump Repo Skills 0.25.1 -> 0.25.10

### 2026-11-06

- **PR #59**: docs(manifests): rewrite evidence-map bullet to match the 13 cited keys
- **PR #55**: refactor: fold duplicated record-generator helpers into record_common
- **Issue #58** (closed): manifests/README.md: rewrite the stale evidence-map paragraph to match the block manifest
- **Issue #54** (closed): Consolidate leftover record-generator duplicates into record_common (klt_version, dirname, mc_stats/fmt_mc)

### 2026-11-05

- **PR #52**: feat(lvs): control block LVS match with power_connectivity match under klt 0.9.0
- **PR #53**: chore(evidence): re-attest T1 item 9 under klt 0.9.0
- **PR #56**: feat(sim): klt yield report for the n=60 write-trip baseline
- **PR #57**: feat(erc): supply ERC specs, severed-rail controls and item 11 evidence
- **Issue #33** (closed): T1 item 4 (LVS clean): klt lvs of the full macro and the control block
- **Issue #51** (closed): Re-attest T1 item 9 (stale make_column_tb.py hash under klt 0.9.0)
- **Issue #19** (closed): Write-trip MC: determinism control, negative control and klt yield report
- **Issue #34** (closed): T1 item 11 (power delivery): klt erc supply spec with array tap ties

### 2026-11-01

- **PR #50**: Bump Repo Skills 0.24.7 -> 0.25.1

### 2026-10-31

- **PR #49**: refactor(sim): share Monte Carlo testbench helpers between generators
- **PR #37**: feat: add README Reproduce section, PDK-free hygiene CI and item 10 attestation
- **Issue #48** (closed): Consolidate duplicated Monte Carlo testbench helpers in bitcell and column generators
- **Issue #28** (closed): T1 item 10 (repo hygiene): README reproduction for every record, PDK-free CI, --attest 10

### 2026-10-27

- **PR #35**: feat: add SRAM periphery generator and compiled 256x32 macro netlist
- **PR #36**: feat(rtl): add sram_ctrl control RTL, behavioural model and synthesized netlist
- **PR #39**: feat(layout): add reproducible P&R flow and routed GDS for sram_ctrl control block
- **PR #41**: docs(rtl): document strobe names and polarity at the digital/analog boundary
- **PR #42**: feat(layout): SRAM macro layout generator and the 256x32 mux-4 GDS, LEF and item 2 evidence
- **PR #44**: feat(verification): klt drc item 3 evidence for the 256x32 macro and control stream
- **PR #45**: ci(signoff): fail when README verdict count disagrees with the signoff record
- **PR #46**: feat(sim): ship column and cocotb benches, inventory and item 9 attestation
- **PR #47**: feat(lvs): macro and control LVS scripts, negative controls, T1 item 4 evidence
- **Issue #26** (closed): T1 item 1 (design sources, analog): periphery generator and compiled 256x32 macro netlist
- **Issue #27** (closed): T1 item 1 (design sources, digital): control RTL, behavioural model and synthesized netlist
- **Issue #31** (closed): T1 item 2 (layout, digital): klt place-and-route of the control block
- **Issue #38** (closed): Document digital sram_ctrl to analog macro control-signal name/polarity mapping
- **Issue #30** (closed): T1 item 2 (layout, analog): tiled 256x32 array and pitch-matched periphery GDS + LEF from the compiler
- **Issue #32** (closed): T1 item 3 (DRC clean): klt drc on the full 256x32 macro, including the array/periphery seam
- **Issue #43** (closed): manifests/README.md verdict count is stale (says 3 of 22; signoff record says 4)

### 2026-10-25

- **Issue #24** (closed): Install the EE-key and market-key ratification reviewer trees (2am#5346 stage 2)

### 2026-10-24

- **PR #25**: ratification: install ee-key and market-key reviewer trees

### 2026-10-21

- **PR #23**: Bump Repo Skills 0.24.3 -> 0.24.7

### 2026-10-20

- **PR #10**: ci: add klt signoff manifest, vendored checklist and verdict check
- **Issue #3** (closed): Add the T1 signoff scaffolding: block manifest, vendored checklist and CI (item 10)

### 2026-10-18

- **PR #13**: feat: add logic-rule 6T bitcell with DRC/LVS-clean layout and PVT margin evidence
- **PR #15**: feat: add write-trip Monte Carlo fixture and partial mismatch record
- **PR #17**: refactor: share write-ladder and scrub helpers between record generators
- **PR #18**: feat: complete write-trip Monte Carlo to n=60 per point
- **PR #20**: feat: add determinism and negative controls for the bitcell Monte Carlo
- **PR #22**: refactor: share git SHA and klt-version helpers across record generators
- **Issue #7** (closed): Size and measure the logic-rule 6T bitcell against the foundry cell
- **Issue #16** (closed): Consolidate duplicated write-ladder and scrub logic in record generators
- **Issue #14** (closed): Bitcell: Monte Carlo on write margin (worst corner 0.203 V, no mismatch evidence)
- **Issue #21** (closed): Consolidate record provenance helpers; drop hardcoded klt version fallback

### 2026-10-17

- **PR #1**: chore(loom): Install Loom 0.19.1181
- **PR #9**: feat: pin sky130 PDK, add env resolver and toolchain smoke bench
- **PR #11**: docs: record sky130 deck treatment of the SRAM core-area marker
- **Issue #4** (closed): Pin the PDK and commit a smoke simulation for both toolchain halves (T1 item 9 bring-up)
- **Issue #6** (closed): Record how klt's sky130 deck treats the SRAM core-area marker
