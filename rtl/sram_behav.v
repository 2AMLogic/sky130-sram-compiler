// sram_behav -- behavioural (functional) model of the 1RW synchronous SRAM
// macro, the model behind the Liberty/views row. Not synthesizable memory.
// Single-cycle functional view: on posedge clk with ce=1, we=1 writes din;
// we=0 registers the addressed word on dout (read-before-write order is not
// modelled; a write leaves dout unchanged). It does not model the
// 4-phase internal sequence of sram_ctrl (see rtl/README.md).
module sram_behav #(
    parameter WORDS = 256,
    parameter BITS  = 32
) (
    input  wire                     clk,
    input  wire                     ce,
    input  wire                     we,
    input  wire [$clog2(WORDS)-1:0] addr,
    input  wire [BITS-1:0]          din,
    output reg  [BITS-1:0]          dout
);
    reg [BITS-1:0] mem [0:WORDS-1];

    always @(posedge clk) begin
        if (ce) begin
            if (we) mem[addr] <= din;
            else    dout      <= mem[addr];
        end
    end
endmodule
