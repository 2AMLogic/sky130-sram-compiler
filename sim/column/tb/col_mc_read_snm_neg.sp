* In-situ READ SNM: decoupled half cell(s) (two independently mismatched)
* whose bit line is the real column bl0 of the 64 x 4 bit slice: sram_precharge ON (PCHB = 0) and 63 further
* bitcell_6t on the column (WL = 0, background data stored by .nodeset, Q = 0 = worst-case DC load on BL).
* Half-cell devices read from the macro's bitcell_6t (pu pfet_01v8 0.42/0.15, pd nfet_01v8 0.84/0.15, ax nfet_01v8 0.42/0.15).
* read: WL = VDD; sweep source is normalised and scaled by VDD.
* NEGATIVE CONTROL: every per-instance mismatch sigma x 6 (slope params of the pinned
* open_pdks mismatch.corner files, x mm_scale); nominal parameters and process corner unchanged.
.param mm_scale=6
.param sky130_fd_pr__nfet_01v8__toxe_slope='3.443e-03*mm_scale'
.param sky130_fd_pr__nfet_01v8__voff_slope='0.007*mm_scale'
.param sky130_fd_pr__nfet_01v8__vth0_slope='3.356e-03*mm_scale'
.param sky130_fd_pr__nfet_01v8__vth0_slope1='7.356e-03*mm_scale'
.param sky130_fd_pr__pfet_01v8__toxe_slope='4.443e-03*mm_scale'
.param sky130_fd_pr__pfet_01v8__toxe_slope1='6.443e-03*mm_scale'
.param sky130_fd_pr__pfet_01v8__toxe_slope2='3.443e-03*mm_scale'
.param sky130_fd_pr__pfet_01v8__nfactor_slope='0.1*mm_scale'
.param sky130_fd_pr__pfet_01v8__nfactor_slope1='0.1*mm_scale'
.param sky130_fd_pr__pfet_01v8__voff_slope2='0.007*mm_scale'
.param sky130_fd_pr__pfet_01v8__vth0_slope='5.856e-03*mm_scale'
.param sky130_fd_pr__pfet_01v8__vth0_slope1='7.356e-03*mm_scale'
.param sky130_fd_pr__pfet_01v8__vth0_slope2='4.356e-03*mm_scale'
.include '../../../design/compiler/macro/sram_256x32_m4.spice'
VVDD vdd 0 dc 1.8
VNRM nrm 0 dc 0
BIN in 0 V='v(nrm)*v(vdd)'
VPCHB pchb 0 dc 0
XC1_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc1_0.q)=0 v(xc1_0.qb)=1.8
XC2_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc2_0.q)=0 v(xc2_0.qb)=1.8
XC3_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc3_0.q)=0 v(xc3_0.qb)=1.8
XC4_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc4_0.q)=0 v(xc4_0.qb)=1.8
XC5_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc5_0.q)=0 v(xc5_0.qb)=1.8
XC6_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc6_0.q)=0 v(xc6_0.qb)=1.8
XC7_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc7_0.q)=0 v(xc7_0.qb)=1.8
XC8_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc8_0.q)=0 v(xc8_0.qb)=1.8
XC9_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc9_0.q)=0 v(xc9_0.qb)=1.8
XC10_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc10_0.q)=0 v(xc10_0.qb)=1.8
XC11_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc11_0.q)=0 v(xc11_0.qb)=1.8
XC12_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc12_0.q)=0 v(xc12_0.qb)=1.8
XC13_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc13_0.q)=0 v(xc13_0.qb)=1.8
XC14_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc14_0.q)=0 v(xc14_0.qb)=1.8
XC15_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc15_0.q)=0 v(xc15_0.qb)=1.8
XC16_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc16_0.q)=0 v(xc16_0.qb)=1.8
XC17_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc17_0.q)=0 v(xc17_0.qb)=1.8
XC18_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc18_0.q)=0 v(xc18_0.qb)=1.8
XC19_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc19_0.q)=0 v(xc19_0.qb)=1.8
XC20_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc20_0.q)=0 v(xc20_0.qb)=1.8
XC21_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc21_0.q)=0 v(xc21_0.qb)=1.8
XC22_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc22_0.q)=0 v(xc22_0.qb)=1.8
XC23_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc23_0.q)=0 v(xc23_0.qb)=1.8
XC24_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc24_0.q)=0 v(xc24_0.qb)=1.8
XC25_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc25_0.q)=0 v(xc25_0.qb)=1.8
XC26_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc26_0.q)=0 v(xc26_0.qb)=1.8
XC27_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc27_0.q)=0 v(xc27_0.qb)=1.8
XC28_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc28_0.q)=0 v(xc28_0.qb)=1.8
XC29_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc29_0.q)=0 v(xc29_0.qb)=1.8
XC30_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc30_0.q)=0 v(xc30_0.qb)=1.8
XC31_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc31_0.q)=0 v(xc31_0.qb)=1.8
XC32_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc32_0.q)=0 v(xc32_0.qb)=1.8
XC33_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc33_0.q)=0 v(xc33_0.qb)=1.8
XC34_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc34_0.q)=0 v(xc34_0.qb)=1.8
XC35_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc35_0.q)=0 v(xc35_0.qb)=1.8
XC36_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc36_0.q)=0 v(xc36_0.qb)=1.8
XC37_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc37_0.q)=0 v(xc37_0.qb)=1.8
XC38_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc38_0.q)=0 v(xc38_0.qb)=1.8
XC39_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc39_0.q)=0 v(xc39_0.qb)=1.8
XC40_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc40_0.q)=0 v(xc40_0.qb)=1.8
XC41_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc41_0.q)=0 v(xc41_0.qb)=1.8
XC42_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc42_0.q)=0 v(xc42_0.qb)=1.8
XC43_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc43_0.q)=0 v(xc43_0.qb)=1.8
XC44_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc44_0.q)=0 v(xc44_0.qb)=1.8
XC45_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc45_0.q)=0 v(xc45_0.qb)=1.8
XC46_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc46_0.q)=0 v(xc46_0.qb)=1.8
XC47_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc47_0.q)=0 v(xc47_0.qb)=1.8
XC48_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc48_0.q)=0 v(xc48_0.qb)=1.8
XC49_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc49_0.q)=0 v(xc49_0.qb)=1.8
XC50_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc50_0.q)=0 v(xc50_0.qb)=1.8
XC51_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc51_0.q)=0 v(xc51_0.qb)=1.8
XC52_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc52_0.q)=0 v(xc52_0.qb)=1.8
XC53_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc53_0.q)=0 v(xc53_0.qb)=1.8
XC54_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc54_0.q)=0 v(xc54_0.qb)=1.8
XC55_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc55_0.q)=0 v(xc55_0.qb)=1.8
XC56_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc56_0.q)=0 v(xc56_0.qb)=1.8
XC57_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc57_0.q)=0 v(xc57_0.qb)=1.8
XC58_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc58_0.q)=0 v(xc58_0.qb)=1.8
XC59_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc59_0.q)=0 v(xc59_0.qb)=1.8
XC60_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc60_0.q)=0 v(xc60_0.qb)=1.8
XC61_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc61_0.q)=0 v(xc61_0.qb)=1.8
XC62_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc62_0.q)=0 v(xc62_0.qb)=1.8
XC63_0 bl0 blb0 0 vdd 0 bitcell_6t
.nodeset v(xc63_0.q)=0 v(xc63_0.qb)=1.8
XPCH0 bl0 blb0 pchb vdd sram_precharge
XMPa outa in vdd vdd sky130_fd_pr__pfet_01v8 w=0.42 l=0.15
XMNa outa in 0 0 sky130_fd_pr__nfet_01v8 w=0.84 l=0.15
XMAa bl0 vdd outa 0 sky130_fd_pr__nfet_01v8 w=0.42 l=0.15
XMPb outb in vdd vdd sky130_fd_pr__pfet_01v8 w=0.42 l=0.15
XMNb outb in 0 0 sky130_fd_pr__nfet_01v8 w=0.84 l=0.15
XMAb bl0 vdd outb 0 sky130_fd_pr__nfet_01v8 w=0.42 l=0.15
