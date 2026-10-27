* READ0 access bench: SAE-delay ladder on a 64-row x 4-column bit slice of design/compiler/macro/sram_256x32_m4.spice.
* Cell (0,0) stores 0, every other cell of the column/slice stores 1 (worst-case leakage);
* half-selected row-0 cells of columns 1..3 store 1-d, d, 1-d. Phase 1 (0.1..1.2 ns): all word lines
* high, bit lines forced to the background value; phase 2 (1.3..2.3 ns): row 0 only, forced to the row-0 data.
* Trial k (variable period): precharge 1.5 ns, WL0+CS0 high, SAE rises d_k after WL (d_k from READ_D),
* WL and SAE fall 0.8 ns after SAE rose. Measured: DOUT and the sense-bit-line differential at SAE,
* cell state after the trial; max Q/QB bump and min half-select node over the run.
.include '../../../design/compiler/macro/sram_256x32_m4.spice'
VVDD vdd 0 dc 1.8
XC0_0 bl0 blb0 wl0 vdd 0 bitcell_6t
XC0_1 bl1 blb1 wl0 vdd 0 bitcell_6t
XC0_2 bl2 blb2 wl0 vdd 0 bitcell_6t
XC0_3 bl3 blb3 wl0 vdd 0 bitcell_6t
XC1_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC1_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC1_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC1_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC2_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC2_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC2_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC2_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC3_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC3_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC3_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC3_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC4_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC4_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC4_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC4_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC5_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC5_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC5_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC5_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC6_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC6_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC6_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC6_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC7_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC7_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC7_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC7_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC8_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC8_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC8_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC8_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC9_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC9_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC9_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC9_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC10_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC10_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC10_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC10_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC11_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC11_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC11_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC11_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC12_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC12_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC12_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC12_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC13_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC13_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC13_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC13_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC14_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC14_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC14_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC14_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC15_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC15_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC15_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC15_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC16_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC16_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC16_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC16_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC17_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC17_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC17_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC17_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC18_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC18_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC18_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC18_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC19_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC19_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC19_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC19_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC20_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC20_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC20_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC20_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC21_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC21_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC21_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC21_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC22_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC22_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC22_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC22_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC23_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC23_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC23_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC23_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC24_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC24_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC24_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC24_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC25_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC25_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC25_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC25_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC26_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC26_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC26_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC26_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC27_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC27_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC27_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC27_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC28_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC28_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC28_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC28_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC29_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC29_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC29_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC29_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC30_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC30_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC30_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC30_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC31_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC31_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC31_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC31_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC32_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC32_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC32_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC32_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC33_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC33_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC33_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC33_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC34_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC34_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC34_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC34_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC35_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC35_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC35_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC35_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC36_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC36_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC36_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC36_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC37_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC37_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC37_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC37_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC38_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC38_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC38_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC38_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC39_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC39_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC39_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC39_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC40_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC40_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC40_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC40_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC41_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC41_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC41_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC41_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC42_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC42_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC42_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC42_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC43_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC43_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC43_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC43_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC44_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC44_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC44_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC44_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC45_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC45_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC45_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC45_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC46_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC46_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC46_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC46_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC47_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC47_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC47_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC47_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC48_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC48_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC48_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC48_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC49_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC49_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC49_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC49_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC50_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC50_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC50_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC50_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC51_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC51_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC51_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC51_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC52_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC52_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC52_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC52_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC53_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC53_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC53_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC53_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC54_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC54_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC54_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC54_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC55_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC55_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC55_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC55_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC56_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC56_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC56_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC56_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC57_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC57_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC57_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC57_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC58_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC58_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC58_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC58_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC59_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC59_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC59_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC59_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC60_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC60_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC60_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC60_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC61_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC61_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC61_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC61_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC62_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC62_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC62_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC62_3 bl3 blb3 wlo vdd 0 bitcell_6t
XC63_0 bl0 blb0 wlo vdd 0 bitcell_6t
XC63_1 bl1 blb1 wlo vdd 0 bitcell_6t
XC63_2 bl2 blb2 wlo vdd 0 bitcell_6t
XC63_3 bl3 blb3 wlo vdd 0 bitcell_6t
XWLDRV wlin0 wl0 vdd 0 sram_wldrv
XWLLOAD 0 wl0 0 0 sky130_fd_pr__nfet_01v8 L=0.15 W=0.42 m=248
* rows 1..63 share an ideal word line (never asserted after initialisation)
XPCH0 bl0 blb0 pchb vdd sram_precharge
XCM0 bl0 blb0 sbl sblb cs0 0 sram_colmux
XPCH1 bl1 blb1 pchb vdd sram_precharge
XCM1 bl1 blb1 sbl sblb cs1 0 sram_colmux
XPCH2 bl2 blb2 pchb vdd sram_precharge
XCM2 bl2 blb2 sbl sblb cs2 0 sram_colmux
XPCH3 bl3 blb3 pchb vdd sram_precharge
XCM3 bl3 blb3 sbl sblb cs3 0 sram_colmux
XSAINV sae saeb vdd 0 sram_inv
XSA sbl sblb sae saeb dout vdd 0 sram_senseamp
XWD sbl sblb din wen vdd 0 sram_wdrv
.model swinit sw(vt=0.5 vh=0.05 ron=20 roff=1e12)
BDB0 drvb0 0 V='(v(ph2)*0+(1-v(ph2))*1)*v(vdd)'
BDN0 drvn0 0 V='(1-(v(ph2)*0+(1-v(ph2))*1))*v(vdd)'
SB0 bl0 drvb0 ctl0 0 swinit
SN0 blb0 drvn0 ctl0 0 swinit
VCTL0 ctl0 0 PWL(0n 0 0.1n 0 0.15n 1 2.3n 1 2.35n 0)
BDB1 drvb1 0 V='(v(ph2)*1+(1-v(ph2))*1)*v(vdd)'
BDN1 drvn1 0 V='(1-(v(ph2)*1+(1-v(ph2))*1))*v(vdd)'
SB1 bl1 drvb1 ctl1 0 swinit
SN1 blb1 drvn1 ctl1 0 swinit
VCTL1 ctl1 0 PWL(0n 0 0.1n 0 0.15n 1 2.3n 1 2.35n 0)
BDB2 drvb2 0 V='(v(ph2)*0+(1-v(ph2))*1)*v(vdd)'
BDN2 drvn2 0 V='(1-(v(ph2)*0+(1-v(ph2))*1))*v(vdd)'
SB2 bl2 drvb2 ctl2 0 swinit
SN2 blb2 drvn2 ctl2 0 swinit
VCTL2 ctl2 0 PWL(0n 0 0.1n 0 0.15n 1 2.3n 1 2.35n 0)
BDB3 drvb3 0 V='(v(ph2)*1+(1-v(ph2))*1)*v(vdd)'
BDN3 drvn3 0 V='(1-(v(ph2)*1+(1-v(ph2))*1))*v(vdd)'
SB3 bl3 drvb3 ctl3 0 swinit
SN3 blb3 drvn3 ctl3 0 swinit
VCTL3 ctl3 0 PWL(0n 0 0.1n 0 0.15n 1 2.3n 1 2.35n 0)
VPH2 ph2 0 PWL(0n 0 1.25n 0 1.3n 1 2.4n 1 2.45n 0)
BDVSA dvsa 0 V='v(sbl)-v(sblb)'
VWL0F wl0f 0 PWL(0n 0 0.1n 0 0.15n 1 1.2n 1 1.25n 0 1.3n 0 1.35n 1 2.3n 1 2.35n 0 4.6n 0 4.65n 1 5.4n 1 5.45n 0 8.3n 0 8.35n 1 9.15n 1 9.2n 0 12.05n 0 12.1n 1 12.95n 1 13n 0 15.85n 0 15.9n 1 16.8n 1 16.85n 0 19.7n 0 19.75n 1 20.7n 1 20.75n 0 23.6n 0 23.65n 1 24.65n 1 24.7n 0 27.55n 0 27.6n 1 28.65n 1 28.7n 0 31.55n 0 31.6n 1 32.7n 1 32.75n 0 35.6n 0 35.65n 1 36.8n 1 36.85n 0 39.7n 0 39.75n 1 40.95n 1 41n 0 43.85n 0 43.9n 1 45.15n 1 45.2n 0 48.05n 0 48.1n 1 49.4n 1 49.45n 0 52.3n 0 52.35n 1 53.7n 1 53.75n 0 56.6n 0 56.65n 1 58.05n 1 58.1n 0 60.95n 0 61n 1 62.45n 1 62.5n 0 65.35n 0 65.4n 1 66.9n 1 66.95n 0 69.8n 0 69.85n 1 71.4n 1 71.45n 0 74.3n 0 74.35n 1 75.95n 1 76n 0 78.85n 0 78.9n 1 80.55n 1 80.6n 0 83.45n 0 83.5n 1 85.2n 1 85.25n 0 88.1n 0 88.15n 1 89.9n 1 89.95n 0 92.8n 0 92.85n 1 94.8n 1 94.85n 0 97.7n 0 97.75n 1 99.9n 1 99.95n 0 102.8n 0 102.85n 1 105.2n 1 105.25n 0 108.1n 0 108.15n 1 110.7n 1 110.75n 0 113.6n 0 113.65n 1 116.4n 1 116.45n 0 119.3n 0 119.35n 1 122.5n 1 122.55n 0)
BWLIN0 wlin0 0 V='(1-v(wl0f))*v(vdd)'
VWLOF wlof 0 PWL(0n 0 0.1n 0 0.15n 1 1.2n 1 1.25n 0)
BWLO wlo 0 V='v(wlof)*v(vdd)'
VPCHBF pchbf 0 PWL(0n 1 2.4n 1 2.45n 0 2.9n 0 2.95n 1 3n 1 3.05n 0 4.5n 0 4.55n 1 6.7n 1 6.75n 0 8.2n 0 8.25n 1 10.45n 1 10.5n 0 11.95n 0 12n 1 14.25n 1 14.3n 0 15.75n 0 15.8n 1 18.1n 1 18.15n 0 19.6n 0 19.65n 1 22n 1 22.05n 0 23.5n 0 23.55n 1 25.95n 1 26n 0 27.45n 0 27.5n 1 29.95n 1 30n 0 31.45n 0 31.5n 1 34n 1 34.05n 0 35.5n 0 35.55n 1 38.1n 1 38.15n 0 39.6n 0 39.65n 1 42.25n 1 42.3n 0 43.75n 0 43.8n 1 46.45n 1 46.5n 0 47.95n 0 48n 1 50.7n 1 50.75n 0 52.2n 0 52.25n 1 55n 1 55.05n 0 56.5n 0 56.55n 1 59.35n 1 59.4n 0 60.85n 0 60.9n 1 63.75n 1 63.8n 0 65.25n 0 65.3n 1 68.2n 1 68.25n 0 69.7n 0 69.75n 1 72.7n 1 72.75n 0 74.2n 0 74.25n 1 77.25n 1 77.3n 0 78.75n 0 78.8n 1 81.85n 1 81.9n 0 83.35n 0 83.4n 1 86.5n 1 86.55n 0 88n 0 88.05n 1 91.2n 1 91.25n 0 92.7n 0 92.75n 1 96.1n 1 96.15n 0 97.6n 0 97.65n 1 101.2n 1 101.25n 0 102.7n 0 102.75n 1 106.5n 1 106.55n 0 108n 0 108.05n 1 112n 1 112.05n 0 113.5n 0 113.55n 1 117.7n 1 117.75n 0 119.2n 0 119.25n 1)
BPCHB pchb 0 V='v(pchbf)*v(vdd)'
VSAEF saef 0 PWL(0n 0 4.6n 0 4.65n 1 5.4n 1 5.45n 0 8.35n 0 8.4n 1 9.15n 1 9.2n 0 12.15n 0 12.2n 1 12.95n 1 13n 0 16n 0 16.05n 1 16.8n 1 16.85n 0 19.9n 0 19.95n 1 20.7n 1 20.75n 0 23.85n 0 23.9n 1 24.65n 1 24.7n 0 27.85n 0 27.9n 1 28.65n 1 28.7n 0 31.9n 0 31.95n 1 32.7n 1 32.75n 0 36n 0 36.05n 1 36.8n 1 36.85n 0 40.15n 0 40.2n 1 40.95n 1 41n 0 44.35n 0 44.4n 1 45.15n 1 45.2n 0 48.6n 0 48.65n 1 49.4n 1 49.45n 0 52.9n 0 52.95n 1 53.7n 1 53.75n 0 57.25n 0 57.3n 1 58.05n 1 58.1n 0 61.65n 0 61.7n 1 62.45n 1 62.5n 0 66.1n 0 66.15n 1 66.9n 1 66.95n 0 70.6n 0 70.65n 1 71.4n 1 71.45n 0 75.15n 0 75.2n 1 75.95n 1 76n 0 79.75n 0 79.8n 1 80.55n 1 80.6n 0 84.4n 0 84.45n 1 85.2n 1 85.25n 0 89.1n 0 89.15n 1 89.9n 1 89.95n 0 94n 0 94.05n 1 94.8n 1 94.85n 0 99.1n 0 99.15n 1 99.9n 1 99.95n 0 104.4n 0 104.45n 1 105.2n 1 105.25n 0 109.9n 0 109.95n 1 110.7n 1 110.75n 0 115.6n 0 115.65n 1 116.4n 1 116.45n 0 121.7n 0 121.75n 1 122.5n 1 122.55n 0)
BSAE sae 0 V='v(saef)*v(vdd)'
VWENF wenf 0 PWL(0n 0)
BWEN wen 0 V='v(wenf)*v(vdd)'
BDIN din 0 V='0*v(vdd)'
VCSF0 csf0 0 PWL(0n 0 3n 0 3.05n 1 6n 1 6.05n 0 6.7n 0 6.75n 1 9.75n 1 9.8n 0 10.45n 0 10.5n 1 13.55n 1 13.6n 0 14.25n 0 14.3n 1 17.4n 1 17.45n 0 18.1n 0 18.15n 1 21.3n 1 21.35n 0 22n 0 22.05n 1 25.25n 1 25.3n 0 25.95n 0 26n 1 29.25n 1 29.3n 0 29.95n 0 30n 1 33.3n 1 33.35n 0 34n 0 34.05n 1 37.4n 1 37.45n 0 38.1n 0 38.15n 1 41.55n 1 41.6n 0 42.25n 0 42.3n 1 45.75n 1 45.8n 0 46.45n 0 46.5n 1 50n 1 50.05n 0 50.7n 0 50.75n 1 54.3n 1 54.35n 0 55n 0 55.05n 1 58.65n 1 58.7n 0 59.35n 0 59.4n 1 63.05n 1 63.1n 0 63.75n 0 63.8n 1 67.5n 1 67.55n 0 68.2n 0 68.25n 1 72n 1 72.05n 0 72.7n 0 72.75n 1 76.55n 1 76.6n 0 77.25n 0 77.3n 1 81.15n 1 81.2n 0 81.85n 0 81.9n 1 85.8n 1 85.85n 0 86.5n 0 86.55n 1 90.5n 1 90.55n 0 91.2n 0 91.25n 1 95.4n 1 95.45n 0 96.1n 0 96.15n 1 100.5n 1 100.55n 0 101.2n 0 101.25n 1 105.8n 1 105.85n 0 106.5n 0 106.55n 1 111.3n 1 111.35n 0 112n 0 112.05n 1 117n 1 117.05n 0 117.7n 0 117.75n 1 123.1n 1 123.15n 0)
BCS0 cs0 0 V='v(csf0)*v(vdd)'
VCSF1 csf1 0 PWL(0n 0)
BCS1 cs1 0 V='v(csf1)*v(vdd)'
VCSF2 csf2 0 PWL(0n 0)
BCS2 cs2 0 V='v(csf2)*v(vdd)'
VCSF3 csf3 0 PWL(0n 0)
BCS3 cs3 0 V='v(csf3)*v(vdd)'
