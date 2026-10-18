* HOLD SNM half-cell fixture body (circuit body for `klt sim`: no .control/.end).
* hold: WL deasserted (0 V), BL precharged to VDD. One storage inverter + its access device, decoupled from the other
* inverter; the sweep source is normalised (0..1) and scaled by VDD so one sweep
* covers every supply corner. Sizes from design/bitcell/sizing.json (make_tb.py).
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
