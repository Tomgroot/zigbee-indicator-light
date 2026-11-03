# Indicator light PCB

`board_routed.kicad_pcb` (from `build_pcb.py` + `route.py`) has the real EasyEDA footprints placed, routed and poured. Import: project view, File > Import > KiCad (see README.md). Coordinates in that file have +Y pointing down (antenna at the top). The placement table below uses +Y up.

2-layer, 1.6 mm, 32.4 x 32.4 mm, corner radius 10 (`board_outline.dxf`), 0.3 mm clearance to the enclosure walls.
4 mounting holes Ø2.2 at (±11.5, ±11.5) for M2 x 5 self-tapping screws (PT/plastite) into the enclosure bosses.
All parts on the top side (JLCPCB Economic PCBA); TP1 is two bare pads on the bottom. Coordinates below: board centre = (0,0), +Y = antenna edge, -Y = USB edge.
Enclosure: `base_indicator_light.stl` + `cap_indicator_light.stl`. PCB bottom sits on the bosses at z=4.0 above the table.

## Netlist

| Net | Connections |
|---|---|
| VBUS | J1 A4/B4/A9/B9, U2.3 (VIN), C1, D1 anode, D2 cathode (TVS to GND, clamps hot-plug spikes) |
| VLED | D1 cathode, LED1 VDD, C6. The diode drops ~0.7 V so 3.3 V data meets WS2812 VIH |
| 3V3 | U2.2 + tab, C2, C3, C4, U1.3 (3V3), U1.15 (VBAT), R3, R4, R5, R6 |
| GND | J1 A1/B1/A12/B12 + shell, U2.1, U1.1/2/11/14/36-53, all caps, TP1.2, R1, R2, R8, D2 anode, LED1 VSS |
| CC1 / CC2 | J1 A5 - R1 - GND / J1 B5 - R2 - GND |
| USB_D+ | J1 A6 + B6 - U1.27 (IO27) |
| USB_D- | J1 A7 + B7 - U1.26 (IO26) |
| EN | U1.8, R3 to 3V3, C5 to GND |
| BOOT | U1.23 (IO9), R4 to 3V3, TP1.1 (bare pad, short to TP1.2 = GND) |
| IO8 | U1.22, R5 to 3V3 (strapping pin) |
| IO25 | U1.25, R6 to 3V3 (strapping pin, datasheet: must not float) |
| LED_DIN | U1.18 (IO4) - R7 - LED1 DIN, R8 to GND (keeps the LED dark until firmware runs) |

Flashing and logs go over the H2's native USB Serial/JTAG, so no USB-UART chip is needed.
Download mode: short the TP1 pads (BOOT, GND) with tweezers while plugging in. Zigbee factory reset: firmware counts power-ups, 5 in a row.

## Placement

| Ref | Position (mm) | Note |
|---|---|---|
| U1 | centre (0, 7.9), antenna to +Y | Module top edge flush with board edge. No copper on either layer above y=+10.6 (antenna strip), across the full board width |
| J1 | (0, -16.2) edge, opening facing -Y | Matches the enclosure hole (centre 1.63 mm above PCB top, z=7.23) |
| LED1 | (0, -3.4) | As central as it gets: 0.5 mm below the ESP32 module body (module ends at y=-0.4), under the cap |
| TP1 | (3.5, -3) **bottom side**, bare pads | BOOT and GND, 2.54 mm pitch, no part. Open the enclosure to reach them |
| U2, C1, C2 | left area x -16..-7, y -8.5..8.5 | |
| C3, C4 | (-8.3, -8), (-7.7, -9.6) | Bulk 10 uF and 100 nF right at U1.3 (2.5 mm rule) |
| R1, R2, R4-R8, D1 | right area x 7..16, y -8.5..8.5 | R8 next to R7 |
| R3, C5 | left, x -13.5, y 5.5 / 7.5 | EN pull-up and delay cap |
| C6 | (-4.6, 1.75) | At LED1 VDD (pad on the LED left side) |
| D2 | (-7.4, 9.5) | Next to J1 VBUS pads so the TVS sees spikes first |

Keep Ø6 mm around each mounting hole free of copper and parts on both layers (screw head + boss).
Use nylon screws for the two +Y (antenna side) holes; metal screws there sit ~4 mm from the antenna.

Routing rules (`route.py`): no vias under the USB-C shell (it is grounded metal), GND stitching vias on a 2 mm grid joining both pours.
