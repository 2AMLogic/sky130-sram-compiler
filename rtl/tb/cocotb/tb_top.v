// tb_top -- cocotb harness top for the control block (T1 item 9, digital).
//
// `sram_ctrl` is either rtl/sram_ctrl.v or the synthesized netlist
// rtl/synth/sram_ctrl_256x32_synth.v (same port list, selected by the
// runner). A behavioural bitcell array stands in for the analog macro: it is
// written while wl_en & wen and drives sa_q while sae. `sram_behav` is the
// reference model: it sees the same user-level access, one cycle, and the
// controller's captured `dout` must equal its `dout` once the access is done.
`timescale 1ns/1ps
module tb_top #(
    parameter WORDS = 256,
    parameter BITS  = 32
) (
    input  wire                     clk,
    input  wire                     rst_n,
    input  wire                     ce,
    input  wire                     we,
    input  wire [$clog2(WORDS)-1:0] addr,
    input  wire [BITS-1:0]          din,
    output wire                     ready,
    output wire                     pch,
    output wire                     wl_en,
    output wire                     sae,
    output wire                     wen,
    output wire [$clog2(WORDS)-1:0] addr_q,
    output wire [BITS-1:0]          din_q,
    output wire [BITS-1:0]          dout,
    output wire [BITS-1:0]          ref_dout
);
    wire [BITS-1:0] sa_q;
    reg  [BITS-1:0] array [0:WORDS-1];

`ifdef SYNTH_NETLIST
    sram_ctrl dut (   // the netlist is the fixed 256 x 32 instance (no parameters)
`else
    sram_ctrl #(.WORDS(WORDS), .BITS(BITS)) dut (
`endif
        .clk(clk), .rst_n(rst_n), .ce(ce), .we(we), .addr(addr), .din(din),
        .sa_q(sa_q), .ready(ready), .pch(pch), .wl_en(wl_en), .sae(sae),
        .wen(wen), .addr_q(addr_q), .din_q(din_q), .dout(dout));

    always @(posedge clk) if (wl_en && wen) array[addr_q] <= din_q;
    assign sa_q = sae ? array[addr_q] : {BITS{1'bx}};

    // The reference only sees an access the controller accepts (ce while ready).
    sram_behav #(.WORDS(WORDS), .BITS(BITS)) ref_model (
        .clk(clk), .ce(ce & ready), .we(we), .addr(addr), .din(din), .dout(ref_dout));
endmodule
