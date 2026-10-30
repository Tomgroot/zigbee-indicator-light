# Indicator light PCB

2-layer, 1.6 mm, 30.4 x 30.4 mm, corner radius 2.5 (`board_outline.dxf`).
Single-sided assembly (top). Coordinates below: board centre = (0,0), +Y = antenna edge, -Y = USB edge.
`generate.py` regenerates `body.stl`, `cap.stl` and the outline. It needs a venv with manifold3d, trimesh and ezdxf.

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
| U1 | centre (0, 6.9), antenna to +Y | Module top edge flush with board edge. No copper on either layer under the antenna area |
| J1 | (0, -15.2) edge, opening facing -Y | Matches the enclosure hole (centre 1.63 mm above PCB top) |
| LED1 | (0, -4.6) | Between J1 and U1, under the cap |
| SW1 | (15.2, -7) edge, actuator facing +X | Actuator flush with board edge. The enclosure block reaches 0.1 mm short of it |
| U2, C1-C3 | left area x -15..-7, y -15..-2 | |
| R1-R7, C4-C6, D1 | right area x 7..15, y -15..-2 | C4 next to U1.3, C6 next to LED1 |

Board rests on 4 corner posts (4 x 4 mm) — keep corners 4 x 4 mm free of bottom-side protrusions.
