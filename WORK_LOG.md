# Work Log

Chronological record of merged pull requests and closed issues, newest first.
Maintained by the Loom Guide role; entries are appended automatically.

### 2026-11-14

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
