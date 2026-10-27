# rtl

Digital half of the SRAM compiler: control RTL, behavioural model and the
synthesized gate-level control netlist. Reference instance: 256 x 32
(8 address bits); the RTL is parameterised on `WORDS` (16..1024) and `BITS`
(8..64) with address width `$clog2(WORDS)`.

| File | Role |
| --- | --- |
| `sram_ctrl.v` | Control RTL (synthesized): latches the access, sequences the periphery strobes. |
| `sram_behav.v` | Behavioural model of the 1RW macro (Liberty/views model; not synthesized). |
| `synth/request.json` | `klt synthesize` request (256 x 32, `sky130_fd_sc_hd` tt_025C_1v80). |
| `synth/sram_ctrl_256x32_synth.v` | Committed gate-level netlist (derived). |
| `synth/regen.sh` | Regenerates / checks the netlist. |
| `inventory.json` | T1 item 1 (digital) attestation inventory. |
| `tb/` | PDK-free Icarus smoke benches (`tb/run.sh`). |

## Control interface (names #26/#29/#30/#31 inherit; keep stable)

Inputs: `clk`, `rst_n` (async, active low), `ce`, `we`, `addr[AW-1:0]`,
`din[BITS-1:0]`, `sa_q[BITS-1:0]` (sense-amp outputs from the macro).
Outputs: `ready`, `pch` (precharge enable), `wl_en` (wordline enable),
`sae` (sense-amp enable), `wen` (write-driver enable), `addr_q` (latched
address to the decoder), `din_q` (latched write data), `dout` (captured read
data).

Sequencing is a 4-phase counter on `clk` (no delay cells), all strobes
registered: IDLE (`pch`=1, `ready`=1) -> accept on `ce` -> WL (`pch`=0,
`wl_en`=1, `wen`=`we`) -> EVAL (read: `sae`=1; `sa_q` captured into `dout` at
its end) -> REST (all strobes off, `pch`=1) -> IDLE. An access takes 4 cycles;
`ce` is ignored while `ready`=0. `sram_behav` is the single-cycle functional
view and does not model this latency; reconciling the externally visible
latency belongs to the spec (#2 / #8).

## Regenerate / check

```console
rtl/synth/regen.sh            # rewrite the committed netlist
rtl/synth/regen.sh --check    # synthesize twice, require byte-identical == committed
rtl/tb/run.sh                 # Icarus smoke benches (16x8, 256x32, 1024x64)
klt signoff --attest 1 --inventory rtl/inventory.json -o evidence/item1-digital.json
```

`regen.sh` needs `klt` (>= 0.8.0 for `--attest`), `yosys`, and the PDK pinned
by `sim/env.sh`. The netlist header carries the Yosys version, so a Yosys
upgrade makes `--check` report drift until the netlist is regenerated.
`klt synthesize --verify-equivalence` covers combinational designs only and
cannot gate this sequential block; functional evidence for the netlist is the
cocotb bench (#29).
