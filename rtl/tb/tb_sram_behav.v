// Smoke bench for sram_behav: write then read back, several addresses.
`timescale 1ns/1ps
module tb_sram_behav;
    parameter WORDS = 256;
    parameter BITS  = 32;
    localparam AW = $clog2(WORDS);
    reg clk = 0, ce = 0, we = 0;
    reg [AW-1:0] addr = 0;
    reg [BITS-1:0] din = 0;
    wire [BITS-1:0] dout;
    integer errors = 0, i;
    sram_behav #(.WORDS(WORDS), .BITS(BITS)) dut (.clk(clk), .ce(ce), .we(we),
        .addr(addr), .din(din), .dout(dout));
    always #5 clk = ~clk;

    task access(input w, input [AW-1:0] a, input [BITS-1:0] d);
        begin
            @(negedge clk); ce = 1; we = w; addr = a; din = d;
            @(negedge clk); ce = 0;
        end
    endtask

    function [BITS-1:0] pat(input integer k);
        pat = (k * 32'h9e3779b1) ^ 32'h5a5a5a5a;
    endfunction

    initial begin
        for (i = 0; i < 8; i = i + 1) access(1, (i * 2) % WORDS, pat(i));
        access(1, WORDS-1, pat(99));
        for (i = 0; i < 8; i = i + 1) begin
            access(0, (i * 2) % WORDS, 0);
            #1; if (dout !== pat(i)) begin errors = errors + 1;
                $display("FAIL addr %0d: got %h want %h", (i*37)%WORDS, dout, pat(i)); end
        end
        access(0, WORDS-1, 0); #1;
        if (dout !== pat(99)) begin errors = errors + 1; $display("FAIL top address"); end
        // ce low: a write must not land (address 0 holds pat(0))
        @(negedge clk); ce = 0; we = 1; addr = 0; din = ~pat(0);
        @(negedge clk);
        access(0, 0, 0); #1;
        if (dout !== pat(0)) begin errors = errors + 1; $display("FAIL ce-low write landed"); end
        if (errors == 0) $display("TB_PASS sram_behav WORDS=%0d BITS=%0d", WORDS, BITS);
        else $display("TB_FAIL sram_behav errors=%0d", errors);
        $finish;
    end
endmodule
