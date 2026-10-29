// sram_ctrl -- digital control for the 1RW synchronous SRAM macro.
//
// Latches the access (ce/we/addr/din) and sequences the analog periphery
// strobes with a 4-phase counter on the single clock edge (no delay cells):
//
//   IDLE  pch=1, ready=1. ce=1 accepts an access and latches we/addr/din.
//   WL    pch=0, wl_en=1 (and wen=1 for a write).
//   EVAL  read only: sae=1 (sense amps fire); sa_q is captured at the end.
//   REST  wl_en/sae/wen=0, pch=1 (bitline restore); then back to IDLE.
//
// An access occupies 4 clock cycles from acceptance to ready. ce is ignored
// unless ready=1. All strobes are registered outputs (glitch-free).
// Port names are the digital side of the analog macro boundary; see
// rtl/README.md. Address width follows WORDS (16..1024), data width BITS.
module sram_ctrl #(
    parameter WORDS = 256,
    parameter BITS  = 32
) (
    input  wire                     clk,
    input  wire                     rst_n,   // async, active low
    input  wire                     ce,
    input  wire                     we,
    input  wire [$clog2(WORDS)-1:0] addr,
    input  wire [BITS-1:0]          din,
    input  wire [BITS-1:0]          sa_q,    // sense-amp outputs (macro)
    output reg                      ready,
    output reg                      pch,     // precharge enable
    output reg                      wl_en,   // wordline enable
    output reg                      sae,     // sense-amp enable
    output reg                      wen,     // write-driver enable
    output reg  [$clog2(WORDS)-1:0] addr_q,  // latched address (to decoder)
    output reg  [BITS-1:0]          din_q,   // latched write data
    output reg  [BITS-1:0]          dout     // captured read data
);
    localparam [1:0] IDLE = 2'd0, WL = 2'd1, EVAL = 2'd2, REST = 2'd3;

    reg [1:0] ph;
    reg       we_q;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            ph    <= IDLE;
            ready <= 1'b1;
            pch   <= 1'b1;
            wl_en <= 1'b0;
            sae   <= 1'b0;
            wen   <= 1'b0;
            we_q  <= 1'b0;
            addr_q <= {$clog2(WORDS){1'b0}};
            din_q  <= {BITS{1'b0}};
            dout   <= {BITS{1'b0}};
        end else begin
            case (ph)
                IDLE: if (ce) begin
                    we_q   <= we;
                    addr_q <= addr;
                    din_q  <= din;
                    ready  <= 1'b0;
                    pch    <= 1'b0;
                    wl_en  <= 1'b1;
                    wen    <= we;
                    ph     <= WL;
                end
                WL: begin
                    sae <= ~we_q;
                    ph  <= EVAL;
                end
                EVAL: begin
                    if (!we_q) dout <= sa_q;
                    wl_en <= 1'b0;
                    sae   <= 1'b0;
                    wen   <= 1'b0;
                    pch   <= 1'b1;
                    ph    <= REST;
                end
                default: begin // REST
                    ready <= 1'b1;
                    ph    <= IDLE;
                end
            endcase
        end
    end
endmodule
