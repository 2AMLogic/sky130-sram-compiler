// Smoke bench for sram_ctrl: a behavioural bitcell array stands in for the
// analog macro (written while wl_en&wen, sa_q = addressed word while sae).
// Checks read-after-write, phase order, ce-low behaviour, and back-to-back
// write/read.
`timescale 1ns/1ps
module tb_sram_ctrl;
    parameter WORDS = 256;
    parameter BITS  = 32;
    localparam AW = $clog2(WORDS);
    reg clk = 0, rst_n = 0, ce = 0, we = 0;
    reg [AW-1:0] addr = 0;
    reg [BITS-1:0] din = 0;
    wire ready, pch, wl_en, sae, wen;
    wire [AW-1:0] addr_q;
    wire [BITS-1:0] din_q, dout;
    wire [BITS-1:0] sa_q;
    reg [BITS-1:0] mem [0:WORDS-1];
    integer errors = 0, i;
    reg [BITS-1:0] magic = 32'hdeadbeef;

    sram_ctrl #(.WORDS(WORDS), .BITS(BITS)) dut (.clk(clk), .rst_n(rst_n),
        .ce(ce), .we(we), .addr(addr), .din(din), .sa_q(sa_q), .ready(ready),
        .pch(pch), .wl_en(wl_en), .sae(sae), .wen(wen), .addr_q(addr_q),
        .din_q(din_q), .dout(dout));
    always #5 clk = ~clk;

    always @(posedge clk) if (wl_en && wen) mem[addr_q] <= din_q;
    assign sa_q = sae ? mem[addr_q] : {BITS{1'bx}};

    // strobe protocol monitor, sampled on each posedge
    always @(posedge clk) begin
        #1;
        if (pch && (wl_en || sae || wen)) begin errors = errors + 1; $display("FAIL strobe while precharging"); end
        if (sae && wen) begin errors = errors + 1; $display("FAIL sae with wen"); end
        if ((sae || wen) && !wl_en) begin errors = errors + 1; $display("FAIL sae/wen without wl_en"); end
    end

    task access(input w, input [AW-1:0] a, input [BITS-1:0] d);
        begin
            while (!ready) @(negedge clk);
            @(negedge clk); ce = 1; we = w; addr = a; din = d;
            // accepted at the next posedge: WL -> EVAL -> REST -> IDLE
            @(posedge clk); #1; ce = 0; we = 0;
            if (!(!pch && wl_en && !sae && (wen === w) && !ready)) begin errors = errors + 1; $display("FAIL WL phase"); end
            @(posedge clk); #1;
            if (!(!pch && wl_en && (sae === !w) && (wen === w))) begin errors = errors + 1; $display("FAIL EVAL phase"); end
            @(posedge clk); #1;
            if (!(pch && !wl_en && !sae && !wen)) begin errors = errors + 1; $display("FAIL REST phase"); end
            @(posedge clk); #1;
            if (!ready) begin errors = errors + 1; $display("FAIL not ready after REST"); end
        end
    endtask

    function [BITS-1:0] pat(input integer k);
        pat = (k * 32'h9e3779b1) ^ 32'h5a5a5a5a;
    endfunction

    initial begin
        #12 rst_n = 1;
        if (!(pch && ready && !wl_en && !sae && !wen)) begin errors = errors + 1; $display("FAIL idle state"); end
        for (i = 0; i < 6; i = i + 1) access(1, (i * 2) % WORDS, pat(i));
        access(1, WORDS-1, pat(77));
        for (i = 0; i < 6; i = i + 1) begin
            access(0, (i * 2) % WORDS, 0);
            if (dout !== pat(i)) begin errors = errors + 1; $display("FAIL read %0d: %h vs %h", i, dout, pat(i)); end
        end
        access(0, WORDS-1, 0);
        if (dout !== pat(77)) begin errors = errors + 1; $display("FAIL top address"); end
        // ce low holds all strobes inactive
        repeat (6) begin
            @(negedge clk); ce = 0; we = 1;
            #2; if (!(pch && !wl_en && !sae && !wen && ready)) begin errors = errors + 1; $display("FAIL ce=0 strobes"); end
        end
        // write immediately followed by read (consecutive accesses)
        access(1, 5, magic);
        access(0, 5, 0);
        if (dout !== magic) begin errors = errors + 1; $display("FAIL back-to-back"); end
        // ce asserted while busy is ignored
        @(negedge clk); ce = 1; we = 1; addr = 9; din = 32'h1; // accepted
        @(negedge clk); ce = 1; we = 0; addr = 10;              // busy: ignored
        @(negedge clk); ce = 0;
        repeat (6) @(posedge clk);
        if (addr_q !== 9) begin errors = errors + 1; $display("FAIL busy ce not ignored"); end
        if (errors == 0) $display("TB_PASS sram_ctrl WORDS=%0d BITS=%0d", WORDS, BITS);
        else $display("TB_FAIL sram_ctrl errors=%0d", errors);
        $finish;
    end
    initial begin #200000 $display("TB_FAIL timeout"); $finish; end
endmodule
