module sram_ctrl (ce,
    clk,
    pch,
    ready,
    rst_n,
    sae,
    we,
    wen,
    wl_en,
    addr,
    addr_q,
    din,
    din_q,
    dout,
    sa_q);
 input ce;
 input clk;
 output pch;
 output ready;
 input rst_n;
 output sae;
 input we;
 output wen;
 output wl_en;
 input [7:0] addr;
 output [7:0] addr_q;
 input [31:0] din;
 output [31:0] din_q;
 output [31:0] dout;
 input [31:0] sa_q;

 wire clknet_3_6__leaf_clk;
 wire _001_;
 wire _002_;
 wire _003_;
 wire _004_;
 wire _005_;
 wire _006_;
 wire _007_;
 wire _008_;
 wire _009_;
 wire _010_;
 wire _011_;
 wire _012_;
 wire _013_;
 wire _014_;
 wire _015_;
 wire _016_;
 wire _017_;
 wire _018_;
 wire _019_;
 wire _020_;
 wire _021_;
 wire _022_;
 wire _023_;
 wire _024_;
 wire _025_;
 wire _026_;
 wire _027_;
 wire _028_;
 wire _029_;
 wire _030_;
 wire _031_;
 wire _032_;
 wire _033_;
 wire _034_;
 wire _035_;
 wire _036_;
 wire _037_;
 wire _038_;
 wire _039_;
 wire _040_;
 wire _041_;
 wire _042_;
 wire _043_;
 wire _044_;
 wire _045_;
 wire _046_;
 wire _047_;
 wire _048_;
 wire _049_;
 wire _050_;
 wire _051_;
 wire _052_;
 wire _053_;
 wire _054_;
 wire _055_;
 wire _056_;
 wire _057_;
 wire _058_;
 wire _059_;
 wire _060_;
 wire _061_;
 wire _062_;
 wire _063_;
 wire _064_;
 wire _065_;
 wire _066_;
 wire _067_;
 wire _068_;
 wire _069_;
 wire _070_;
 wire _071_;
 wire _072_;
 wire _073_;
 wire _074_;
 wire _075_;
 wire _076_;
 wire _077_;
 wire _078_;
 wire _079_;
 wire _080_;
 wire _081_;
 wire _082_;
 wire _083_;
 wire clknet_3_2__leaf_clk;
 wire clknet_3_1__leaf_clk;
 wire clknet_3_0__leaf_clk;
 wire clknet_3_5__leaf_clk;
 wire clknet_3_4__leaf_clk;
 wire clknet_3_3__leaf_clk;
 wire _090_;
 wire _091_;
 wire _092_;
 wire clknet_0_clk;
 wire _094_;
 wire _095_;
 wire _096_;
 wire _097_;
 wire _098_;
 wire we_q;
 wire clknet_3_7__leaf_clk;
 wire [3:0] ph;

 sky130_fd_sc_hd__nand2_1 _099_ (.A(ph[0]),
    .B(ce),
    .Y(_080_));
 sky130_fd_sc_hd__inv_2 _100_ (.A(_080_),
    .Y(_081_));
 sky130_fd_sc_hd__inv_1 _102_ (.A(ce),
    .Y(_082_));
 sky130_fd_sc_hd__a21o_1 _103_ (.A1(ph[0]),
    .A2(_082_),
    .B1(ph[3]),
    .X(_001_));
 sky130_fd_sc_hd__nor2b_4 _104_ (.A(we_q),
    .B_N(ph[1]),
    .Y(_083_));
 sky130_fd_sc_hd__mux2_4 _107_ (.A0(dout[15]),
    .A1(sa_q[15]),
    .S(_083_),
    .X(_002_));
 sky130_fd_sc_hd__mux2_4 _108_ (.A0(dout[14]),
    .A1(sa_q[14]),
    .S(_083_),
    .X(_003_));
 sky130_fd_sc_hd__mux2_4 _109_ (.A0(dout[13]),
    .A1(sa_q[13]),
    .S(_083_),
    .X(_004_));
 sky130_fd_sc_hd__mux2_4 _110_ (.A0(dout[12]),
    .A1(sa_q[12]),
    .S(_083_),
    .X(_005_));
 sky130_fd_sc_hd__mux2_4 _111_ (.A0(dout[11]),
    .A1(sa_q[11]),
    .S(_083_),
    .X(_006_));
 sky130_fd_sc_hd__mux2_4 _112_ (.A0(dout[10]),
    .A1(sa_q[10]),
    .S(_083_),
    .X(_007_));
 sky130_fd_sc_hd__mux2_4 _113_ (.A0(dout[9]),
    .A1(sa_q[9]),
    .S(_083_),
    .X(_008_));
 sky130_fd_sc_hd__mux2_4 _114_ (.A0(dout[8]),
    .A1(sa_q[8]),
    .S(_083_),
    .X(_009_));
 sky130_fd_sc_hd__mux2_4 _115_ (.A0(dout[7]),
    .A1(sa_q[7]),
    .S(_083_),
    .X(_010_));
 sky130_fd_sc_hd__mux2_4 _116_ (.A0(dout[6]),
    .A1(sa_q[6]),
    .S(_083_),
    .X(_011_));
 sky130_fd_sc_hd__mux2_4 _118_ (.A0(dout[5]),
    .A1(sa_q[5]),
    .S(_083_),
    .X(_012_));
 sky130_fd_sc_hd__mux2_4 _119_ (.A0(dout[4]),
    .A1(sa_q[4]),
    .S(_083_),
    .X(_013_));
 sky130_fd_sc_hd__mux2_4 _120_ (.A0(dout[3]),
    .A1(sa_q[3]),
    .S(_083_),
    .X(_014_));
 sky130_fd_sc_hd__mux2_4 _121_ (.A0(dout[2]),
    .A1(sa_q[2]),
    .S(_083_),
    .X(_015_));
 sky130_fd_sc_hd__mux2_4 _122_ (.A0(dout[1]),
    .A1(sa_q[1]),
    .S(_083_),
    .X(_016_));
 sky130_fd_sc_hd__mux2_4 _123_ (.A0(dout[0]),
    .A1(sa_q[0]),
    .S(_083_),
    .X(_017_));
 sky130_fd_sc_hd__mux2_2 _124_ (.A0(din_q[30]),
    .A1(din[30]),
    .S(_081_),
    .X(_018_));
 sky130_fd_sc_hd__mux2_2 _125_ (.A0(din_q[29]),
    .A1(din[29]),
    .S(_081_),
    .X(_019_));
 sky130_fd_sc_hd__mux2_2 _126_ (.A0(din_q[28]),
    .A1(din[28]),
    .S(_081_),
    .X(_020_));
 sky130_fd_sc_hd__mux2_2 _127_ (.A0(din_q[27]),
    .A1(din[27]),
    .S(_081_),
    .X(_021_));
 sky130_fd_sc_hd__mux2_2 _128_ (.A0(din_q[26]),
    .A1(din[26]),
    .S(_081_),
    .X(_022_));
 sky130_fd_sc_hd__mux2_2 _129_ (.A0(din_q[25]),
    .A1(din[25]),
    .S(_081_),
    .X(_023_));
 sky130_fd_sc_hd__mux2_2 _130_ (.A0(din_q[24]),
    .A1(din[24]),
    .S(_081_),
    .X(_024_));
 sky130_fd_sc_hd__mux2_2 _132_ (.A0(din_q[23]),
    .A1(din[23]),
    .S(_081_),
    .X(_025_));
 sky130_fd_sc_hd__mux2_2 _133_ (.A0(din_q[22]),
    .A1(din[22]),
    .S(_081_),
    .X(_026_));
 sky130_fd_sc_hd__mux2_2 _134_ (.A0(din_q[21]),
    .A1(din[21]),
    .S(_081_),
    .X(_027_));
 sky130_fd_sc_hd__mux2_2 _135_ (.A0(din_q[20]),
    .A1(din[20]),
    .S(_081_),
    .X(_028_));
 sky130_fd_sc_hd__mux2_2 _136_ (.A0(din_q[19]),
    .A1(din[19]),
    .S(_081_),
    .X(_029_));
 sky130_fd_sc_hd__mux2_2 _137_ (.A0(din_q[18]),
    .A1(din[18]),
    .S(_081_),
    .X(_030_));
 sky130_fd_sc_hd__mux2_2 _138_ (.A0(din_q[17]),
    .A1(din[17]),
    .S(_081_),
    .X(_031_));
 sky130_fd_sc_hd__mux2_2 _139_ (.A0(din_q[16]),
    .A1(din[16]),
    .S(_081_),
    .X(_032_));
 sky130_fd_sc_hd__mux2_2 _140_ (.A0(din_q[15]),
    .A1(din[15]),
    .S(_081_),
    .X(_033_));
 sky130_fd_sc_hd__mux2_2 _141_ (.A0(din_q[14]),
    .A1(din[14]),
    .S(_081_),
    .X(_034_));
 sky130_fd_sc_hd__mux2_2 _143_ (.A0(din_q[13]),
    .A1(din[13]),
    .S(_081_),
    .X(_035_));
 sky130_fd_sc_hd__mux2_2 _144_ (.A0(din_q[12]),
    .A1(din[12]),
    .S(_081_),
    .X(_036_));
 sky130_fd_sc_hd__mux2_2 _145_ (.A0(din_q[11]),
    .A1(din[11]),
    .S(_081_),
    .X(_037_));
 sky130_fd_sc_hd__mux2_2 _146_ (.A0(din_q[10]),
    .A1(din[10]),
    .S(_081_),
    .X(_038_));
 sky130_fd_sc_hd__mux2_2 _147_ (.A0(din_q[9]),
    .A1(din[9]),
    .S(_081_),
    .X(_039_));
 sky130_fd_sc_hd__mux2_2 _148_ (.A0(din_q[8]),
    .A1(din[8]),
    .S(_081_),
    .X(_040_));
 sky130_fd_sc_hd__mux2_2 _149_ (.A0(din_q[7]),
    .A1(din[7]),
    .S(_081_),
    .X(_041_));
 sky130_fd_sc_hd__mux2_2 _150_ (.A0(din_q[6]),
    .A1(din[6]),
    .S(_081_),
    .X(_042_));
 sky130_fd_sc_hd__mux2_2 _151_ (.A0(din_q[5]),
    .A1(din[5]),
    .S(_081_),
    .X(_043_));
 sky130_fd_sc_hd__mux2_2 _152_ (.A0(din_q[4]),
    .A1(din[4]),
    .S(_081_),
    .X(_044_));
 sky130_fd_sc_hd__mux2_2 _154_ (.A0(din_q[3]),
    .A1(din[3]),
    .S(_081_),
    .X(_045_));
 sky130_fd_sc_hd__mux2_2 _155_ (.A0(din_q[2]),
    .A1(din[2]),
    .S(_081_),
    .X(_046_));
 sky130_fd_sc_hd__mux2_2 _156_ (.A0(din_q[1]),
    .A1(din[1]),
    .S(_081_),
    .X(_047_));
 sky130_fd_sc_hd__mux2_1 _157_ (.A0(din_q[0]),
    .A1(din[0]),
    .S(_081_),
    .X(_048_));
 sky130_fd_sc_hd__mux2_1 _158_ (.A0(addr_q[6]),
    .A1(addr[6]),
    .S(_081_),
    .X(_049_));
 sky130_fd_sc_hd__mux2_1 _159_ (.A0(addr_q[5]),
    .A1(addr[5]),
    .S(_081_),
    .X(_050_));
 sky130_fd_sc_hd__mux2_2 _160_ (.A0(addr_q[4]),
    .A1(addr[4]),
    .S(_081_),
    .X(_051_));
 sky130_fd_sc_hd__mux2_2 _161_ (.A0(addr_q[3]),
    .A1(addr[3]),
    .S(_081_),
    .X(_052_));
 sky130_fd_sc_hd__mux2_2 _162_ (.A0(addr_q[2]),
    .A1(addr[2]),
    .S(_081_),
    .X(_053_));
 sky130_fd_sc_hd__mux2_2 _163_ (.A0(addr_q[1]),
    .A1(addr[1]),
    .S(_081_),
    .X(_054_));
 sky130_fd_sc_hd__mux2_2 _164_ (.A0(addr_q[0]),
    .A1(addr[0]),
    .S(_081_),
    .X(_055_));
 sky130_fd_sc_hd__mux2_2 _165_ (.A0(addr_q[7]),
    .A1(addr[7]),
    .S(_081_),
    .X(_056_));
 sky130_fd_sc_hd__nor2_1 _166_ (.A(ph[1]),
    .B(ph[2]),
    .Y(_090_));
 sky130_fd_sc_hd__nor2_1 _167_ (.A(ph[1]),
    .B(we_q),
    .Y(_091_));
 sky130_fd_sc_hd__a22o_1 _168_ (.A1(sae),
    .A2(_090_),
    .B1(_091_),
    .B2(ph[2]),
    .X(_057_));
 sky130_fd_sc_hd__mux2_4 _169_ (.A0(dout[30]),
    .A1(sa_q[30]),
    .S(_083_),
    .X(_058_));
 sky130_fd_sc_hd__nor3_1 _170_ (.A(ph[0]),
    .B(ph[1]),
    .C(ph[2]),
    .Y(_092_));
 sky130_fd_sc_hd__a2bb2oi_1 _171_ (.A1_N(ready),
    .A2_N(_092_),
    .B1(_090_),
    .B2(_081_),
    .Y(_059_));
 sky130_fd_sc_hd__mux2_2 _172_ (.A0(din_q[31]),
    .A1(din[31]),
    .S(_081_),
    .X(_060_));
 sky130_fd_sc_hd__mux2_4 _173_ (.A0(dout[29]),
    .A1(sa_q[29]),
    .S(_083_),
    .X(_061_));
 sky130_fd_sc_hd__mux2_4 _174_ (.A0(dout[28]),
    .A1(sa_q[28]),
    .S(_083_),
    .X(_062_));
 sky130_fd_sc_hd__mux2_4 _175_ (.A0(dout[31]),
    .A1(sa_q[31]),
    .S(_083_),
    .X(_063_));
 sky130_fd_sc_hd__mux2_4 _177_ (.A0(dout[27]),
    .A1(sa_q[27]),
    .S(_083_),
    .X(_064_));
 sky130_fd_sc_hd__mux2_2 _178_ (.A0(ph[1]),
    .A1(ce),
    .S(ph[0]),
    .X(_094_));
 sky130_fd_sc_hd__o22a_1 _179_ (.A1(ph[1]),
    .A2(_080_),
    .B1(_094_),
    .B2(pch),
    .X(_065_));
 sky130_fd_sc_hd__mux2_4 _180_ (.A0(dout[26]),
    .A1(sa_q[26]),
    .S(_083_),
    .X(_066_));
 sky130_fd_sc_hd__mux2_4 _181_ (.A0(dout[25]),
    .A1(sa_q[25]),
    .S(_083_),
    .X(_067_));
 sky130_fd_sc_hd__mux2_4 _182_ (.A0(dout[24]),
    .A1(sa_q[24]),
    .S(_083_),
    .X(_068_));
 sky130_fd_sc_hd__mux2_4 _183_ (.A0(dout[23]),
    .A1(sa_q[23]),
    .S(_083_),
    .X(_069_));
 sky130_fd_sc_hd__inv_1 _184_ (.A(wen),
    .Y(_095_));
 sky130_fd_sc_hd__nand3_1 _185_ (.A(ph[0]),
    .B(we),
    .C(ce),
    .Y(_096_));
 sky130_fd_sc_hd__o22ai_1 _186_ (.A1(_095_),
    .A2(_094_),
    .B1(_096_),
    .B2(ph[1]),
    .Y(_070_));
 sky130_fd_sc_hd__mux2_4 _187_ (.A0(dout[22]),
    .A1(sa_q[22]),
    .S(_083_),
    .X(_071_));
 sky130_fd_sc_hd__mux2_4 _188_ (.A0(dout[21]),
    .A1(sa_q[21]),
    .S(_083_),
    .X(_072_));
 sky130_fd_sc_hd__mux2_4 _189_ (.A0(dout[20]),
    .A1(sa_q[20]),
    .S(_083_),
    .X(_073_));
 sky130_fd_sc_hd__mux2_4 _190_ (.A0(dout[19]),
    .A1(sa_q[19]),
    .S(_083_),
    .X(_074_));
 sky130_fd_sc_hd__mux2_4 _191_ (.A0(dout[18]),
    .A1(sa_q[18]),
    .S(_083_),
    .X(_075_));
 sky130_fd_sc_hd__mux2_2 _192_ (.A0(dout[17]),
    .A1(sa_q[17]),
    .S(_083_),
    .X(_076_));
 sky130_fd_sc_hd__inv_1 _193_ (.A(we_q),
    .Y(_097_));
 sky130_fd_sc_hd__o21ai_0 _194_ (.A1(_097_),
    .A2(_081_),
    .B1(_096_),
    .Y(_077_));
 sky130_fd_sc_hd__mux2_2 _195_ (.A0(dout[16]),
    .A1(sa_q[16]),
    .S(_083_),
    .X(_078_));
 sky130_fd_sc_hd__inv_1 _196_ (.A(wl_en),
    .Y(_098_));
 sky130_fd_sc_hd__o22ai_1 _197_ (.A1(ph[1]),
    .A2(_080_),
    .B1(_094_),
    .B2(_098_),
    .Y(_079_));
 sky130_fd_sc_hd__dfrtp_1 _198_ (.CLK(clknet_3_0__leaf_clk),
    .D(_055_),
    .RESET_B(rst_n),
    .Q(addr_q[0]));
 sky130_fd_sc_hd__dfrtp_1 _199_ (.CLK(clknet_3_1__leaf_clk),
    .D(_054_),
    .RESET_B(rst_n),
    .Q(addr_q[1]));
 sky130_fd_sc_hd__dfrtp_1 _200_ (.CLK(clknet_3_0__leaf_clk),
    .D(_053_),
    .RESET_B(rst_n),
    .Q(addr_q[2]));
 sky130_fd_sc_hd__dfrtp_1 _201_ (.CLK(clknet_3_0__leaf_clk),
    .D(_052_),
    .RESET_B(rst_n),
    .Q(addr_q[3]));
 sky130_fd_sc_hd__dfrtp_1 _202_ (.CLK(clknet_3_1__leaf_clk),
    .D(_051_),
    .RESET_B(rst_n),
    .Q(addr_q[4]));
 sky130_fd_sc_hd__dfrtp_1 _203_ (.CLK(clknet_3_0__leaf_clk),
    .D(_050_),
    .RESET_B(rst_n),
    .Q(addr_q[5]));
 sky130_fd_sc_hd__dfrtp_1 _204_ (.CLK(clknet_3_0__leaf_clk),
    .D(_049_),
    .RESET_B(rst_n),
    .Q(addr_q[6]));
 sky130_fd_sc_hd__dfrtp_1 _205_ (.CLK(clknet_3_1__leaf_clk),
    .D(_056_),
    .RESET_B(rst_n),
    .Q(addr_q[7]));
 sky130_fd_sc_hd__dfrtp_1 _206_ (.CLK(clknet_3_4__leaf_clk),
    .D(_057_),
    .RESET_B(rst_n),
    .Q(sae));
 sky130_fd_sc_hd__dfstp_2 _207_ (.CLK(clknet_3_4__leaf_clk),
    .D(_059_),
    .SET_B(rst_n),
    .Q(ready));
 sky130_fd_sc_hd__dfrtp_1 _208_ (.CLK(clknet_3_0__leaf_clk),
    .D(_048_),
    .RESET_B(rst_n),
    .Q(din_q[0]));
 sky130_fd_sc_hd__dfrtp_1 _209_ (.CLK(clknet_3_0__leaf_clk),
    .D(_047_),
    .RESET_B(rst_n),
    .Q(din_q[1]));
 sky130_fd_sc_hd__dfrtp_1 _210_ (.CLK(clknet_3_2__leaf_clk),
    .D(_046_),
    .RESET_B(rst_n),
    .Q(din_q[2]));
 sky130_fd_sc_hd__dfrtp_1 _211_ (.CLK(clknet_3_3__leaf_clk),
    .D(_045_),
    .RESET_B(rst_n),
    .Q(din_q[3]));
 sky130_fd_sc_hd__dfrtp_1 _212_ (.CLK(clknet_3_2__leaf_clk),
    .D(_044_),
    .RESET_B(rst_n),
    .Q(din_q[4]));
 sky130_fd_sc_hd__dfrtp_1 _213_ (.CLK(clknet_3_2__leaf_clk),
    .D(_043_),
    .RESET_B(rst_n),
    .Q(din_q[5]));
 sky130_fd_sc_hd__dfrtp_1 _214_ (.CLK(clknet_3_3__leaf_clk),
    .D(_042_),
    .RESET_B(rst_n),
    .Q(din_q[6]));
 sky130_fd_sc_hd__dfrtp_1 _215_ (.CLK(clknet_3_2__leaf_clk),
    .D(_041_),
    .RESET_B(rst_n),
    .Q(din_q[7]));
 sky130_fd_sc_hd__dfrtp_1 _216_ (.CLK(clknet_3_3__leaf_clk),
    .D(_040_),
    .RESET_B(rst_n),
    .Q(din_q[8]));
 sky130_fd_sc_hd__dfrtp_1 _217_ (.CLK(clknet_3_2__leaf_clk),
    .D(_039_),
    .RESET_B(rst_n),
    .Q(din_q[9]));
 sky130_fd_sc_hd__dfrtp_1 _218_ (.CLK(clknet_3_0__leaf_clk),
    .D(_038_),
    .RESET_B(rst_n),
    .Q(din_q[10]));
 sky130_fd_sc_hd__dfrtp_1 _219_ (.CLK(clknet_3_0__leaf_clk),
    .D(_037_),
    .RESET_B(rst_n),
    .Q(din_q[11]));
 sky130_fd_sc_hd__dfrtp_1 _220_ (.CLK(clknet_3_0__leaf_clk),
    .D(_036_),
    .RESET_B(rst_n),
    .Q(din_q[12]));
 sky130_fd_sc_hd__dfrtp_1 _221_ (.CLK(clknet_3_0__leaf_clk),
    .D(_035_),
    .RESET_B(rst_n),
    .Q(din_q[13]));
 sky130_fd_sc_hd__dfrtp_1 _222_ (.CLK(clknet_3_1__leaf_clk),
    .D(_034_),
    .RESET_B(rst_n),
    .Q(din_q[14]));
 sky130_fd_sc_hd__dfrtp_1 _223_ (.CLK(clknet_3_1__leaf_clk),
    .D(_033_),
    .RESET_B(rst_n),
    .Q(din_q[15]));
 sky130_fd_sc_hd__dfrtp_1 _224_ (.CLK(clknet_3_1__leaf_clk),
    .D(_032_),
    .RESET_B(rst_n),
    .Q(din_q[16]));
 sky130_fd_sc_hd__dfrtp_1 _225_ (.CLK(clknet_3_1__leaf_clk),
    .D(_031_),
    .RESET_B(rst_n),
    .Q(din_q[17]));
 sky130_fd_sc_hd__dfrtp_1 _226_ (.CLK(clknet_3_0__leaf_clk),
    .D(_030_),
    .RESET_B(rst_n),
    .Q(din_q[18]));
 sky130_fd_sc_hd__dfrtp_1 _227_ (.CLK(clknet_3_2__leaf_clk),
    .D(_029_),
    .RESET_B(rst_n),
    .Q(din_q[19]));
 sky130_fd_sc_hd__dfrtp_1 _228_ (.CLK(clknet_3_0__leaf_clk),
    .D(_028_),
    .RESET_B(rst_n),
    .Q(din_q[20]));
 sky130_fd_sc_hd__dfrtp_1 _229_ (.CLK(clknet_3_2__leaf_clk),
    .D(_027_),
    .RESET_B(rst_n),
    .Q(din_q[21]));
 sky130_fd_sc_hd__dfrtp_1 _230_ (.CLK(clknet_3_2__leaf_clk),
    .D(_026_),
    .RESET_B(rst_n),
    .Q(din_q[22]));
 sky130_fd_sc_hd__dfrtp_1 _231_ (.CLK(clknet_3_2__leaf_clk),
    .D(_025_),
    .RESET_B(rst_n),
    .Q(din_q[23]));
 sky130_fd_sc_hd__dfrtp_1 _232_ (.CLK(clknet_3_2__leaf_clk),
    .D(_024_),
    .RESET_B(rst_n),
    .Q(din_q[24]));
 sky130_fd_sc_hd__dfrtp_1 _233_ (.CLK(clknet_3_2__leaf_clk),
    .D(_023_),
    .RESET_B(rst_n),
    .Q(din_q[25]));
 sky130_fd_sc_hd__dfrtp_1 _234_ (.CLK(clknet_3_3__leaf_clk),
    .D(_022_),
    .RESET_B(rst_n),
    .Q(din_q[26]));
 sky130_fd_sc_hd__dfrtp_1 _235_ (.CLK(clknet_3_2__leaf_clk),
    .D(_021_),
    .RESET_B(rst_n),
    .Q(din_q[27]));
 sky130_fd_sc_hd__dfrtp_1 _236_ (.CLK(clknet_3_3__leaf_clk),
    .D(_020_),
    .RESET_B(rst_n),
    .Q(din_q[28]));
 sky130_fd_sc_hd__dfrtp_1 _237_ (.CLK(clknet_3_3__leaf_clk),
    .D(_019_),
    .RESET_B(rst_n),
    .Q(din_q[29]));
 sky130_fd_sc_hd__dfrtp_1 _238_ (.CLK(clknet_3_2__leaf_clk),
    .D(_018_),
    .RESET_B(rst_n),
    .Q(din_q[30]));
 sky130_fd_sc_hd__dfrtp_1 _239_ (.CLK(clknet_3_2__leaf_clk),
    .D(_060_),
    .RESET_B(rst_n),
    .Q(din_q[31]));
 sky130_fd_sc_hd__dfrtp_1 _240_ (.CLK(clknet_3_6__leaf_clk),
    .D(_017_),
    .RESET_B(rst_n),
    .Q(dout[0]));
 sky130_fd_sc_hd__dfrtp_1 _241_ (.CLK(clknet_3_6__leaf_clk),
    .D(_016_),
    .RESET_B(rst_n),
    .Q(dout[1]));
 sky130_fd_sc_hd__dfrtp_1 _242_ (.CLK(clknet_3_5__leaf_clk),
    .D(_015_),
    .RESET_B(rst_n),
    .Q(dout[2]));
 sky130_fd_sc_hd__dfrtp_1 _243_ (.CLK(clknet_3_7__leaf_clk),
    .D(_014_),
    .RESET_B(rst_n),
    .Q(dout[3]));
 sky130_fd_sc_hd__dfrtp_1 _244_ (.CLK(clknet_3_6__leaf_clk),
    .D(_013_),
    .RESET_B(rst_n),
    .Q(dout[4]));
 sky130_fd_sc_hd__dfrtp_1 _245_ (.CLK(clknet_3_7__leaf_clk),
    .D(_012_),
    .RESET_B(rst_n),
    .Q(dout[5]));
 sky130_fd_sc_hd__dfrtp_1 _246_ (.CLK(clknet_3_5__leaf_clk),
    .D(_011_),
    .RESET_B(rst_n),
    .Q(dout[6]));
 sky130_fd_sc_hd__dfrtp_1 _247_ (.CLK(clknet_3_5__leaf_clk),
    .D(_010_),
    .RESET_B(rst_n),
    .Q(dout[7]));
 sky130_fd_sc_hd__dfrtp_1 _248_ (.CLK(clknet_3_5__leaf_clk),
    .D(_009_),
    .RESET_B(rst_n),
    .Q(dout[8]));
 sky130_fd_sc_hd__dfrtp_1 _249_ (.CLK(clknet_3_5__leaf_clk),
    .D(_008_),
    .RESET_B(rst_n),
    .Q(dout[9]));
 sky130_fd_sc_hd__dfrtp_1 _250_ (.CLK(clknet_3_6__leaf_clk),
    .D(_007_),
    .RESET_B(rst_n),
    .Q(dout[10]));
 sky130_fd_sc_hd__dfrtp_1 _251_ (.CLK(clknet_3_7__leaf_clk),
    .D(_006_),
    .RESET_B(rst_n),
    .Q(dout[11]));
 sky130_fd_sc_hd__dfrtp_1 _252_ (.CLK(clknet_3_6__leaf_clk),
    .D(_005_),
    .RESET_B(rst_n),
    .Q(dout[12]));
 sky130_fd_sc_hd__dfrtp_1 _253_ (.CLK(clknet_3_5__leaf_clk),
    .D(_004_),
    .RESET_B(rst_n),
    .Q(dout[13]));
 sky130_fd_sc_hd__dfrtp_1 _254_ (.CLK(clknet_3_5__leaf_clk),
    .D(_003_),
    .RESET_B(rst_n),
    .Q(dout[14]));
 sky130_fd_sc_hd__dfrtp_1 _255_ (.CLK(clknet_3_5__leaf_clk),
    .D(_002_),
    .RESET_B(rst_n),
    .Q(dout[15]));
 sky130_fd_sc_hd__dfrtp_1 _256_ (.CLK(clknet_3_4__leaf_clk),
    .D(_078_),
    .RESET_B(rst_n),
    .Q(dout[16]));
 sky130_fd_sc_hd__dfrtp_1 _257_ (.CLK(clknet_3_5__leaf_clk),
    .D(_076_),
    .RESET_B(rst_n),
    .Q(dout[17]));
 sky130_fd_sc_hd__dfrtp_1 _258_ (.CLK(clknet_3_7__leaf_clk),
    .D(_075_),
    .RESET_B(rst_n),
    .Q(dout[18]));
 sky130_fd_sc_hd__dfrtp_1 _259_ (.CLK(clknet_3_4__leaf_clk),
    .D(_074_),
    .RESET_B(rst_n),
    .Q(dout[19]));
 sky130_fd_sc_hd__dfrtp_1 _260_ (.CLK(clknet_3_6__leaf_clk),
    .D(_073_),
    .RESET_B(rst_n),
    .Q(dout[20]));
 sky130_fd_sc_hd__dfrtp_1 _261_ (.CLK(clknet_3_6__leaf_clk),
    .D(_072_),
    .RESET_B(rst_n),
    .Q(dout[21]));
 sky130_fd_sc_hd__dfrtp_1 _262_ (.CLK(clknet_3_6__leaf_clk),
    .D(_071_),
    .RESET_B(rst_n),
    .Q(dout[22]));
 sky130_fd_sc_hd__dfrtp_1 _263_ (.CLK(clknet_3_4__leaf_clk),
    .D(_069_),
    .RESET_B(rst_n),
    .Q(dout[23]));
 sky130_fd_sc_hd__dfrtp_1 _264_ (.CLK(clknet_3_6__leaf_clk),
    .D(_068_),
    .RESET_B(rst_n),
    .Q(dout[24]));
 sky130_fd_sc_hd__dfrtp_1 _265_ (.CLK(clknet_3_4__leaf_clk),
    .D(_067_),
    .RESET_B(rst_n),
    .Q(dout[25]));
 sky130_fd_sc_hd__dfrtp_1 _266_ (.CLK(clknet_3_7__leaf_clk),
    .D(_066_),
    .RESET_B(rst_n),
    .Q(dout[26]));
 sky130_fd_sc_hd__dfrtp_1 _267_ (.CLK(clknet_3_7__leaf_clk),
    .D(_064_),
    .RESET_B(rst_n),
    .Q(dout[27]));
 sky130_fd_sc_hd__dfrtp_1 _268_ (.CLK(clknet_3_7__leaf_clk),
    .D(_062_),
    .RESET_B(rst_n),
    .Q(dout[28]));
 sky130_fd_sc_hd__dfrtp_1 _269_ (.CLK(clknet_3_7__leaf_clk),
    .D(_061_),
    .RESET_B(rst_n),
    .Q(dout[29]));
 sky130_fd_sc_hd__dfrtp_1 _270_ (.CLK(clknet_3_7__leaf_clk),
    .D(_058_),
    .RESET_B(rst_n),
    .Q(dout[30]));
 sky130_fd_sc_hd__dfrtp_1 _271_ (.CLK(clknet_3_7__leaf_clk),
    .D(_063_),
    .RESET_B(rst_n),
    .Q(dout[31]));
 sky130_fd_sc_hd__dfstp_2 _272_ (.CLK(clknet_3_3__leaf_clk),
    .D(_065_),
    .SET_B(rst_n),
    .Q(pch));
 sky130_fd_sc_hd__dfrtp_1 _273_ (.CLK(clknet_3_3__leaf_clk),
    .D(_070_),
    .RESET_B(rst_n),
    .Q(wen));
 sky130_fd_sc_hd__dfrtp_1 _274_ (.CLK(clknet_3_1__leaf_clk),
    .D(_077_),
    .RESET_B(rst_n),
    .Q(we_q));
 sky130_fd_sc_hd__dfrtp_1 _275_ (.CLK(clknet_3_3__leaf_clk),
    .D(_079_),
    .RESET_B(rst_n),
    .Q(wl_en));
 sky130_fd_sc_hd__dfstp_2 _276_ (.CLK(clknet_3_3__leaf_clk),
    .D(_001_),
    .SET_B(rst_n),
    .Q(ph[0]));
 sky130_fd_sc_hd__dfrtp_1 _277_ (.CLK(clknet_3_1__leaf_clk),
    .D(ph[2]),
    .RESET_B(rst_n),
    .Q(ph[1]));
 sky130_fd_sc_hd__dfrtp_1 _278_ (.CLK(clknet_3_1__leaf_clk),
    .D(_081_),
    .RESET_B(rst_n),
    .Q(ph[2]));
 sky130_fd_sc_hd__dfrtp_1 _279_ (.CLK(clknet_3_3__leaf_clk),
    .D(ph[1]),
    .RESET_B(rst_n),
    .Q(ph[3]));
 sky130_fd_sc_hd__buf_4 clkbuf_0_clk (.A(clk),
    .X(clknet_0_clk));
 sky130_fd_sc_hd__buf_4 clkbuf_3_0__f_clk (.A(clknet_0_clk),
    .X(clknet_3_0__leaf_clk));
 sky130_fd_sc_hd__buf_4 clkbuf_3_1__f_clk (.A(clknet_0_clk),
    .X(clknet_3_1__leaf_clk));
 sky130_fd_sc_hd__buf_4 clkbuf_3_2__f_clk (.A(clknet_0_clk),
    .X(clknet_3_2__leaf_clk));
 sky130_fd_sc_hd__buf_4 clkbuf_3_3__f_clk (.A(clknet_0_clk),
    .X(clknet_3_3__leaf_clk));
 sky130_fd_sc_hd__buf_4 clkbuf_3_4__f_clk (.A(clknet_0_clk),
    .X(clknet_3_4__leaf_clk));
 sky130_fd_sc_hd__buf_4 clkbuf_3_5__f_clk (.A(clknet_0_clk),
    .X(clknet_3_5__leaf_clk));
 sky130_fd_sc_hd__buf_4 clkbuf_3_6__f_clk (.A(clknet_0_clk),
    .X(clknet_3_6__leaf_clk));
 sky130_fd_sc_hd__buf_4 clkbuf_3_7__f_clk (.A(clknet_0_clk),
    .X(clknet_3_7__leaf_clk));
 sky130_fd_sc_hd__inv_1 clkload0 (.A(clknet_3_0__leaf_clk));
 sky130_fd_sc_hd__bufinv_16 clkload1 (.A(clknet_3_1__leaf_clk));
 sky130_fd_sc_hd__clkinv_2 clkload2 (.A(clknet_3_3__leaf_clk));
 sky130_fd_sc_hd__inv_6 clkload3 (.A(clknet_3_4__leaf_clk));
 sky130_fd_sc_hd__clkinvlp_4 clkload4 (.A(clknet_3_5__leaf_clk));
 sky130_fd_sc_hd__clkinvlp_4 clkload5 (.A(clknet_3_6__leaf_clk));
 sky130_fd_sc_hd__bufinv_16 clkload6 (.A(clknet_3_7__leaf_clk));
endmodule
