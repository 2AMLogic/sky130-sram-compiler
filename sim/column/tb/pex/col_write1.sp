* WRITE1 completion bench: write-pulse-width ladder on a
* 64-row x 4-column bit slice of design/compiler/macro/sram_256x32_m4.spice. Initialisation as the read benches (all other cells store 0);
* trial k (variable period): restore cell (0,0) to its old value with forced bit lines, precharge 1.0 ns, then WL0 and
* WEN high together for w_k (WRITE_W) ns with DIN=1 through wdrv -> colmux (CS0); cell state sampled
* 0.5 ns after the pulse. Half-select retention (min/max of the row-0 cells of columns 1..3) over the run.
* PEX bench: the matched DUT sits behind the single .include line klt pex swaps
* for the extracted netlist (sram_col_slice.spice here, the layout extraction there).
.include 'sram_col_slice.spice'
VVDD vdd 0 dc 1.8
XSLICE bl0 bl1 bl2 bl3 blb0 blb1 blb2 blb3 cs0 cs1 cs2 cs3 din dout pchb q00 q01 q02 qb00 sae sbl sblb vdd 0 wen wl0 wlo wlin0 sram_col_slice
* the 124 omitted columns' word-line gate load, outside the extracted top
XWLLOAD 0 wl0 0 0 sky130_fd_pr__nfet_01v8 L=0.15 W=0.42 m=248
.model swinit sw(vt=0.5 vh=0.05 ron=20 roff=1e12)
BDB0 drvb0 0 V='(v(rst)*0+(1-v(rst))*(v(ph2)*0+(1-v(ph2))*0))*v(vdd)'
BDN0 drvn0 0 V='(1-(v(rst)*0+(1-v(rst))*(v(ph2)*0+(1-v(ph2))*0)))*v(vdd)'
SB0 bl0 drvb0 ctl0 0 swinit
SN0 blb0 drvn0 ctl0 0 swinit
VCTL0 ctl0 0 PWL(0n 0 0.1n 0 0.15n 1 2.3n 1 2.35n 0 3.1n 0 3.15n 1 4.5n 1 4.55n 0 6.75n 0 6.8n 1 8.15n 1 8.2n 0 10.45n 0 10.5n 1 11.85n 1 11.9n 0 14.2n 0 14.25n 1 15.6n 1 15.65n 0 18n 0 18.05n 1 19.4n 1 19.45n 0 21.85n 0 21.9n 1 23.25n 1 23.3n 0 25.75n 0 25.8n 1 27.15n 1 27.2n 0 29.7n 0 29.75n 1 31.1n 1 31.15n 0 33.7n 0 33.75n 1 35.1n 1 35.15n 0 37.75n 0 37.8n 1 39.15n 1 39.2n 0 41.85n 0 41.9n 1 43.25n 1 43.3n 0 46n 0 46.05n 1 47.4n 1 47.45n 0 50.2n 0 50.25n 1 51.6n 1 51.65n 0 54.45n 0 54.5n 1 55.85n 1 55.9n 0 58.75n 0 58.8n 1 60.15n 1 60.2n 0 63.1n 0 63.15n 1 64.5n 1 64.55n 0 67.5n 0 67.55n 1 68.9n 1 68.95n 0 72.1n 0 72.15n 1 73.5n 1 73.55n 0 76.95n 0 77n 1 78.35n 1 78.4n 0 82.05n 0 82.1n 1 83.45n 1 83.5n 0)
BDB1 drvb1 0 V='(v(ph2)*0+(1-v(ph2))*0)*v(vdd)'
BDN1 drvn1 0 V='(1-(v(ph2)*0+(1-v(ph2))*0))*v(vdd)'
SB1 bl1 drvb1 ctl1 0 swinit
SN1 blb1 drvn1 ctl1 0 swinit
VCTL1 ctl1 0 PWL(0n 0 0.1n 0 0.15n 1 2.3n 1 2.35n 0)
BDB2 drvb2 0 V='(v(ph2)*1+(1-v(ph2))*0)*v(vdd)'
BDN2 drvn2 0 V='(1-(v(ph2)*1+(1-v(ph2))*0))*v(vdd)'
SB2 bl2 drvb2 ctl2 0 swinit
SN2 blb2 drvn2 ctl2 0 swinit
VCTL2 ctl2 0 PWL(0n 0 0.1n 0 0.15n 1 2.3n 1 2.35n 0)
BDB3 drvb3 0 V='(v(ph2)*0+(1-v(ph2))*0)*v(vdd)'
BDN3 drvn3 0 V='(1-(v(ph2)*0+(1-v(ph2))*0))*v(vdd)'
SB3 bl3 drvb3 ctl3 0 swinit
SN3 blb3 drvn3 ctl3 0 swinit
VCTL3 ctl3 0 PWL(0n 0 0.1n 0 0.15n 1 2.3n 1 2.35n 0)
VPH2 ph2 0 PWL(0n 0 1.25n 0 1.3n 1 2.4n 1 2.45n 0)
VRST rst 0 PWL(0n 0 3.1n 0 3.15n 1 4.5n 1 4.55n 0 6.75n 0 6.8n 1 8.15n 1 8.2n 0 10.45n 0 10.5n 1 11.85n 1 11.9n 0 14.2n 0 14.25n 1 15.6n 1 15.65n 0 18n 0 18.05n 1 19.4n 1 19.45n 0 21.85n 0 21.9n 1 23.25n 1 23.3n 0 25.75n 0 25.8n 1 27.15n 1 27.2n 0 29.7n 0 29.75n 1 31.1n 1 31.15n 0 33.7n 0 33.75n 1 35.1n 1 35.15n 0 37.75n 0 37.8n 1 39.15n 1 39.2n 0 41.85n 0 41.9n 1 43.25n 1 43.3n 0 46n 0 46.05n 1 47.4n 1 47.45n 0 50.2n 0 50.25n 1 51.6n 1 51.65n 0 54.45n 0 54.5n 1 55.85n 1 55.9n 0 58.75n 0 58.8n 1 60.15n 1 60.2n 0 63.1n 0 63.15n 1 64.5n 1 64.55n 0 67.5n 0 67.55n 1 68.9n 1 68.95n 0 72.1n 0 72.15n 1 73.5n 1 73.55n 0 76.95n 0 77n 1 78.35n 1 78.4n 0 82.05n 0 82.1n 1 83.45n 1 83.5n 0)
VWL0F wl0f 0 PWL(0n 0 0.1n 0 0.15n 1 1.2n 1 1.25n 0 1.3n 0 1.35n 1 2.3n 1 2.35n 0 3.2n 0 3.25n 1 4.2n 1 4.25n 0 5.7n 0 5.75n 1 5.8n 0 6.85n 0 6.9n 1 7.85n 1 7.9n 0 9.35n 0 9.4n 1 9.45n 1 9.5n 0 10.55n 0 10.6n 1 11.55n 1 11.6n 0 13.05n 0 13.1n 1 13.2n 1 13.25n 0 14.3n 0 14.35n 1 15.3n 1 15.35n 0 16.8n 0 16.85n 1 17n 1 17.05n 0 18.1n 0 18.15n 1 19.1n 1 19.15n 0 20.6n 0 20.65n 1 20.85n 1 20.9n 0 21.95n 0 22n 1 22.95n 1 23n 0 24.45n 0 24.5n 1 24.75n 1 24.8n 0 25.85n 0 25.9n 1 26.85n 1 26.9n 0 28.35n 0 28.4n 1 28.7n 1 28.75n 0 29.8n 0 29.85n 1 30.8n 1 30.85n 0 32.3n 0 32.35n 1 32.7n 1 32.75n 0 33.8n 0 33.85n 1 34.8n 1 34.85n 0 36.3n 0 36.35n 1 36.75n 1 36.8n 0 37.85n 0 37.9n 1 38.85n 1 38.9n 0 40.35n 0 40.4n 1 40.85n 1 40.9n 0 41.95n 0 42n 1 42.95n 1 43n 0 44.45n 0 44.5n 1 45n 1 45.05n 0 46.1n 0 46.15n 1 47.1n 1 47.15n 0 48.6n 0 48.65n 1 49.2n 1 49.25n 0 50.3n 0 50.35n 1 51.3n 1 51.35n 0 52.8n 0 52.85n 1 53.45n 1 53.5n 0 54.55n 0 54.6n 1 55.55n 1 55.6n 0 57.05n 0 57.1n 1 57.75n 1 57.8n 0 58.85n 0 58.9n 1 59.85n 1 59.9n 0 61.35n 0 61.4n 1 62.1n 1 62.15n 0 63.2n 0 63.25n 1 64.2n 1 64.25n 0 65.7n 0 65.75n 1 66.5n 1 66.55n 0 67.6n 0 67.65n 1 68.6n 1 68.65n 0 70.1n 0 70.15n 1 71.1n 1 71.15n 0 72.2n 0 72.25n 1 73.2n 1 73.25n 0 74.7n 0 74.75n 1 75.95n 1 76n 0 77.05n 0 77.1n 1 78.05n 1 78.1n 0 79.55n 0 79.6n 1 81.05n 1 81.1n 0 82.15n 0 82.2n 1 83.15n 1 83.2n 0 84.65n 0 84.7n 1 86.65n 1 86.7n 0)
BWLIN0 wlin0 0 V='(1-v(wl0f))*v(vdd)'
VWLOF wlof 0 PWL(0n 0 0.1n 0 0.15n 1 1.2n 1 1.25n 0)
BWLO wlo 0 V='v(wlof)*v(vdd)'
VPCHBF pchbf 0 PWL(0n 1 2.4n 1 2.45n 0 2.9n 0 2.95n 1 4.6n 1 4.65n 0 5.6n 0 5.65n 1 8.25n 1 8.3n 0 9.25n 0 9.3n 1 11.95n 1 12n 0 12.95n 0 13n 1 15.7n 1 15.75n 0 16.7n 0 16.75n 1 19.5n 1 19.55n 0 20.5n 0 20.55n 1 23.35n 1 23.4n 0 24.35n 0 24.4n 1 27.25n 1 27.3n 0 28.25n 0 28.3n 1 31.2n 1 31.25n 0 32.2n 0 32.25n 1 35.2n 1 35.25n 0 36.2n 0 36.25n 1 39.25n 1 39.3n 0 40.25n 0 40.3n 1 43.35n 1 43.4n 0 44.35n 0 44.4n 1 47.5n 1 47.55n 0 48.5n 0 48.55n 1 51.7n 1 51.75n 0 52.7n 0 52.75n 1 55.95n 1 56n 0 56.95n 0 57n 1 60.25n 1 60.3n 0 61.25n 0 61.3n 1 64.6n 1 64.65n 0 65.6n 0 65.65n 1 69n 1 69.05n 0 70n 0 70.05n 1 73.6n 1 73.65n 0 74.6n 0 74.65n 1 78.45n 1 78.5n 0 79.45n 0 79.5n 1 83.55n 1 83.6n 0 84.55n 0 84.6n 1)
BPCHB pchb 0 V='v(pchbf)*v(vdd)'
VSAEF saef 0 PWL(0n 0)
BSAE sae 0 V='v(saef)*v(vdd)'
VWENF wenf 0 PWL(0n 0 5.7n 0 5.75n 1 5.8n 0 9.35n 0 9.4n 1 9.45n 1 9.5n 0 13.05n 0 13.1n 1 13.2n 1 13.25n 0 16.8n 0 16.85n 1 17n 1 17.05n 0 20.6n 0 20.65n 1 20.85n 1 20.9n 0 24.45n 0 24.5n 1 24.75n 1 24.8n 0 28.35n 0 28.4n 1 28.7n 1 28.75n 0 32.3n 0 32.35n 1 32.7n 1 32.75n 0 36.3n 0 36.35n 1 36.75n 1 36.8n 0 40.35n 0 40.4n 1 40.85n 1 40.9n 0 44.45n 0 44.5n 1 45n 1 45.05n 0 48.6n 0 48.65n 1 49.2n 1 49.25n 0 52.8n 0 52.85n 1 53.45n 1 53.5n 0 57.05n 0 57.1n 1 57.75n 1 57.8n 0 61.35n 0 61.4n 1 62.1n 1 62.15n 0 65.7n 0 65.75n 1 66.5n 1 66.55n 0 70.1n 0 70.15n 1 71.1n 1 71.15n 0 74.7n 0 74.75n 1 75.95n 1 76n 0 79.55n 0 79.6n 1 81.05n 1 81.1n 0 84.65n 0 84.7n 1 86.65n 1 86.7n 0)
BWEN wen 0 V='v(wenf)*v(vdd)'
BDIN din 0 V='1*v(vdd)'
VCSF0 csf0 0 PWL(0n 0 4.4n 0 4.45n 1 6.35n 1 6.4n 0 8.05n 0 8.1n 1 10.05n 1 10.1n 0 11.75n 0 11.8n 1 13.8n 1 13.85n 0 15.5n 0 15.55n 1 17.6n 1 17.65n 0 19.3n 0 19.35n 1 21.45n 1 21.5n 0 23.15n 0 23.2n 1 25.35n 1 25.4n 0 27.05n 0 27.1n 1 29.3n 1 29.35n 0 31n 0 31.05n 1 33.3n 1 33.35n 0 35n 0 35.05n 1 37.35n 1 37.4n 0 39.05n 0 39.1n 1 41.45n 1 41.5n 0 43.15n 0 43.2n 1 45.6n 1 45.65n 0 47.3n 0 47.35n 1 49.8n 1 49.85n 0 51.5n 0 51.55n 1 54.05n 1 54.1n 0 55.75n 0 55.8n 1 58.35n 1 58.4n 0 60.05n 0 60.1n 1 62.7n 1 62.75n 0 64.4n 0 64.45n 1 67.1n 1 67.15n 0 68.8n 0 68.85n 1 71.7n 1 71.75n 0 73.4n 0 73.45n 1 76.55n 1 76.6n 0 78.25n 0 78.3n 1 81.65n 1 81.7n 0 83.35n 0 83.4n 1 87.25n 1 87.3n 0)
BCS0 cs0 0 V='v(csf0)*v(vdd)'
VCSF1 csf1 0 PWL(0n 0)
BCS1 cs1 0 V='v(csf1)*v(vdd)'
VCSF2 csf2 0 PWL(0n 0)
BCS2 cs2 0 V='v(csf2)*v(vdd)'
VCSF3 csf3 0 PWL(0n 0)
BCS3 cs3 0 V='v(csf3)*v(vdd)'
