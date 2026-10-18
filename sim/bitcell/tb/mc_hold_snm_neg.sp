* HOLD SNM half-cell fixture body (circuit body for `klt sim`: no .control/.end).
* hold: WL deasserted (0 V), BL precharged to VDD. One storage inverter + its access device, decoupled from the other
* inverter; the sweep source is normalised (0..1) and scaled by VDD so one sweep
* covers every supply corner. Sizes from design/bitcell/sizing.json (make_tb.py).
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
VVDD vdd 0 dc 1.8
VNRM nrm 0 dc 0
BIN in 0 V='v(nrm)*v(vdd)'
EBL bl 0 vdd 0 1
XMPA outa in vdd vdd sky130_fd_pr__pfet_01v8 w=0.42 l=0.15
XMNA outa in 0 0 sky130_fd_pr__nfet_01v8 w=0.84 l=0.15
XMAA bl 0 outa 0 sky130_fd_pr__nfet_01v8 w=0.42 l=0.15
XMPB outb in vdd vdd sky130_fd_pr__pfet_01v8 w=0.42 l=0.15
XMNB outb in 0 0 sky130_fd_pr__nfet_01v8 w=0.84 l=0.15
XMAB bl 0 outb 0 sky130_fd_pr__nfet_01v8 w=0.42 l=0.15
