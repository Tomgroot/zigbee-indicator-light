# Indicator light PCB

2-layer, 1.6 mm, 32.4 x 32.4 mm, corner radius 10 (`board_outline.dxf`), 0.3 mm clearance to the enclosure walls.
4 mounting holes Ø2.2 at (±11.5, ±11.5) for M2 x 5 self-tapping screws (PT/plastite) into the enclosure bosses.
Top-side assembly, except SW1 on the bottom. Coordinates below: board centre = (0,0), +Y = antenna edge, -Y = USB edge.
Enclosure: `base_indicator_light.stl` + `cap_indicator_light.stl`. PCB bottom sits on the bosses at z=4.0 above the table.

## Netlist

| Net | Connections |
|---|---|
| VBUS | J1 A4/B4/A9/B9, U2.3 (VIN), C1, D1 anode |
| VLED | D1 cathode, LED1 VDD, C6. The diode drops ~0.7 V so 3.3 V data meets WS2812 VIH |
| 3V3 | U2.2 + tab, C2, C3, C4, U1.3 (3V3), U1.15 (VBAT), R3, R4, R5, R6 |
| GND | J1 A1/B1/A12/B12 + shell, U2.1, U1.1/2/11/14/36-53, all caps, SW1, R1, R2, LED1 VSS |
| CC1 / CC2 | J1 A5 - R1 - GND / J1 B5 - R2 - GND |
| USB_D+ | J1 A6 + B6 - U1.27 (IO27) |
| USB_D- | J1 A7 + B7 - U1.26 (IO26) |
| EN | U1.8, R3 to 3V3, C5 to GND |
| BOOT | U1.23 (IO9), R4 to 3V3, SW1 to GND |
| IO8 | U1.22, R5 to 3V3 (strapping pin) |
| IO25 | U1.25, R6 to 3V3 (strapping pin, datasheet: must not float) |
| LED_DIN | U1.18 (IO4) - R7 - LED1 DIN |

Flashing and logs go over the H2's native USB Serial/JTAG, so no USB-UART chip is needed.
Download mode: hold SW1 while plugging in.

## Placement

| Ref | Position (mm) | Note |
|---|---|---|
| U1 | centre (0, 7.9), antenna to +Y | Module top edge flush with board edge. No copper on either layer under the antenna area |
| J1 | (0, -16.2) edge, opening facing -Y | Matches the enclosure hole (centre 1.63 mm above PCB top, z=7.23) |
| LED1 | (0, -4.6) | Between J1 and U1, under the cap |
| SW1 | (-5, -8.5) **bottom side**, actuator facing down | Pressed by the floor flexure plunger (top at z=2.2, 0.3 mm gap to a 1.5 mm switch) |
| U2, C1-C3 | left area x -16..-7, y -8.5..8.5 | |
| R1-R7, C4-C6, D1 | right area x 7..16, y -8.5..8.5 | C4 next to U1.3, C6 next to LED1 |

Keep Ø6 mm around each mounting hole free of copper and parts on both layers (screw head + boss).
Use nylon screws for the two +Y holes if the antenna detunes.
