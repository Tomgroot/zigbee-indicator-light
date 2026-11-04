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
| 3V3 | U2.2 + tab, C2, C3, C4, U1.3 (3V3), R3, R4, R5, R6 |
| GND | J1 A1/B1/A12/B12 + shell, U2.1, U1.1/2/11/14/36-53, all caps, TP1.2, R1, R2, R8, D2 anode, LED1 VSS |
| CC1 / CC2 | J1 A5 - R1 - GND / J1 B5 - R2 - GND |
| USB_D+ | J1 A6 + B6 - U1.18 (IO13) |
| USB_D- | J1 A7 + B7 - U1.17 (IO12) |
| EN | U1.8, R3 to 3V3, C5 to GND |
| BOOT | U1.23 (IO9), R4 to 3V3, TP1.1 (bare pad, short to TP1.2 = GND) |
| IO8 | U1.22, R5 to 3V3 (strapping pin) |
| IO15 | U1.20, R6 to 3V3 (strapping pin, no internal pull: datasheet says it must be driven) |
| LED_DIN | U1.19 (IO14) - R7 - LED1 DIN, R8 to GND (keeps the LED dark until firmware runs) |

Flashing and logs go over the C6's native USB Serial/JTAG, so no USB-UART chip is needed.
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

## Rev 2 notes (battery, not built)

- U2 is already an AP2114H (SOT-223, 1 A, stable with ceramic caps). For a cell, a lower-quiescent LDO such as AP2112K-3.3 (C51118) is better, but its SOT-23-5 package overheats at 5 V in / 0.4 A peaks; only use it from the battery.
- Add a charger (MCP73831 or TP4056) and cell protection. The WS2812B-B-V6 idles at under 1 uA (datasheet), so no LED switch is needed.
- Free GPIOs: IO3 (ADC1_CH3, battery sense) and IO2. Keep the cell away from the antenna edge.

## Power budget (USB 5 V)

- C6 peak supply current (datasheet): Wi-Fi TX up to 382 mA, 802.15.4 TX 305 mA, BLE 309 mA, RX about 75 mA. The module needs a supply that delivers 0.5 A; the AP2114H gives 1 A.
- Worst case 5 V to 3.3 V at 0.38 A is 0.65 W, about +83 C on the SOT-223 (128 C/W) while transmitting continuously. Average dissipation is much lower.
- With the LED at full white (about 60 mA) the board stays under the 500 mA USB limit, but only just. Cap the LED brightness in firmware.

## LED shield for ESP32-H2 SuperMini (cheap variant)

`shield.kicad_pcb` (from `python3 build_shield.py`, routed, self-checked) is an 18 x 23.6 mm board (29 mm wide over the screw tabs) that slides onto the long header pins under a SuperMini H2 (2x9, 2.54 mm pitch, rows 15.24 mm apart). Solder at least 5V, GND and IO8 (5V is the square pad). Parts face away from the SuperMini; its USB end is marked on the bottom silk.

- LED1 SK6812-B (C5380881, extended, Economic OK) on IO8, in parallel with the SuperMini's own WS2812: same protocol, no firmware change; colour may differ slightly. WS2812B-B-V6 (C52941391) is Standard PCBA only. JLCPCB holds orders with C5380881 for baking (MSL3, $7.82, Standard PCBA only); every in-stock 5050 alternative is Standard-only or also flagged (checked 2026-11-05), so for boards that are sold order Standard PCBA with baking; only for throwaway prototypes order Economic with the remark "proceed without baking, customer accepts risk". Pinout assumed equal to WS2812B (1 VDD, 2 DOUT, 3 GND, 4 DIN): confirm in the datasheet before ordering.
- D1 1N4148W drops 5V to ~4.2 V so 3.3 V data meets VIH. C1 100 nF at VDD, R1 470R in the data line.
- Order: JLCPCB **Economic** PCBA with `shield_bom.csv` / `shield_cpl.csv`. Check each part's PCBA type with `jlc.py --bom shield_bom.csv` (`pcba` column must be `econ`). Check LED1 pin 1 and D1 polarity in the placement preview.
- Two M2 holes (Ø2.2) at (±12, 0) in side tabs (board 29 x 23.6 mm). They take M2 self-tapping screws into the two Ø5 bosses of `base_indicator_light.stl` (from `base.py`), at STL (5.5, 13.1) and (29.5, 13.1). The SuperMini hangs upside down below the shield with its USB-C centre at z 4.0 (`USB_Z`, keeps the plug overmould off the table); the wall USB hole is at that height. The boss top z 9.1 is an estimate (USB-C 3.2 + SuperMini PCB 1.0 + header spacer 2.5): measure the stack and update `base.py`. The base no longer has the C6 board's corner bosses.

### H2-Zero variant

`shield_zero.kicad_pcb` (`python3 build_shield.py zero`) is for the Waveshare ESP32-H2-Zero. The Zero's power row is on the other side and its IO8 is a bottom pad only, so the LED data comes from **IO22** (firmware change) and the parts are re-placed (LED1 rotated 270). Same BOM (`shield_bom.csv`); placement in `shield_zero_cpl.csv`. Pinout, 15.24 mm row spacing and 18 x 23.5 mm outline checked against the Waveshare schematic and size drawing. The Zero's ceramic antenna sits centred at the end opposite USB-C, over a ground-free area from about y = +6.7 (shield coordinates) to the edge: keep all shield copper except the header pads out of it. IO10 (last pin at that end) is not used for that reason.
