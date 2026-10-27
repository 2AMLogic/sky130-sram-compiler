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

## Digital ↔ analog boundary: names and polarity

The control block and the analog macro (`sram_<words>x<bits>_m<mux>`, ports
`A* D* Q* WLEN PCHB SAE WEN`) name the same strobes differently. Polarity below
was read from the gate connections in `design/compiler/macro/sram_256x32_m4.spice`
and the generator `design/compiler/sram_compile.py`, and from `rtl/sram_ctrl.v`;
it is not simulated here (strobe-sequence transients belong to #29).

| Digital (`sram_ctrl`) | Analog macro port | Digital polarity | Analog polarity | Inversion | Evidence |
| --- | --- | --- | --- | --- | --- |
| `pch` | `PCHB` | active-high (precharge on when 1; reset/IDLE = 1) | **active-low** (precharge on when `PCHB`=0) | **yes: `PCHB = ~pch`** | `PCHB` is the gate of PFETs `XMP1/XMP2/XMEQ` in `sram_precharge` (`.spice:81-83`); `pch` reset to 1 (`sram_ctrl.v:44`), 0 on accept (`:59`), back to 1 at the end of EVAL (`:73`) |
| `wl_en` | `WLEN` | active-high | active-high | none (direct) | `WLEN` is a plain input of the group-0 predecode NAND, so a wordline fires only when `WLEN`=1 (`.spice:143-157`, `sram_compile.py:118-125`) |
| `sae` | `SAE` | active-high | active-high | none (direct) | `SAE` gates NFET tail `XMT` (`.spice:99`); the macro derives `SAEB` internally (`sram_compile.py:109`), so no `SAEB` port |
| `wen` | `WEN` | active-high | active-high | none (direct) | `WEN` gates NFETs `XMW2/XMW4` in `sram_wdrv` (`.spice:113,115`) |
| `sa_q[k]` | `Q<k>` | — | — | none | name/width mapping from the port lists; `Q<k>` is the DOUT of column-group `k` (`sram_compile.py:146`) |
| `din_q[k]` | `D<k>` | — | — | none | `D<k>` is the write-driver DIN of column-group `k` (`sram_compile.py:147`) |
| `addr_q[n]` | `A<n>` | — | — | none | name/width mapping from the port lists; `A0` is the address LSB (`sram_compile.py:106-116`; low bits select the column) |

Direction: `pch`, `wl_en`, `sae`, `wen`, `addr_q`, `din_q` are digital outputs
driving macro inputs; `Q<k>` is a macro output feeding the digital input `sa_q`.

**The one required inversion is `PCHB = ~pch`.** It belongs to the **digital**
wrapper/top-level at the macro hookup (a single inverter on `pch`), so the macro
port list and manifest stay unchanged and `sram_ctrl` keeps its active-high
strobes. That inverter is not instantiated yet: no top-level wrapper exists in
this tree, so it is added with the hookup work (#29/#31).

Reset state: `sram_ctrl` resets to `pch`=1, `wl_en`=`sae`=`wen`=0, which maps to
`PCHB`=0 (bitlines precharging/equalised), `WLEN`=`SAE`=`WEN`=0 (all else off).

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
