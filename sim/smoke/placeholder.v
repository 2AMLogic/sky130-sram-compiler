// Trivial placeholder module for the Yosys half of the toolchain smoke.
// Not part of the design.
module smoke_top (
    input  wire clk,
    input  wire a,
    input  wire b,
    output reg  y
);
  always @(posedge clk) y <= a & b;
endmodule
