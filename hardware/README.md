# Import the PCB into EasyEDA Pro

Import this file: `hardware/board_routed.kicad_pcb`. It has all parts placed, all traces routed and GND pours on both layers. It is in KiCad 5.1 format, which is the newest EasyEDA Pro imports.

## 1. Import

1. Open EasyEDA Pro and create a new project (or open an existing one).
2. Stay on the **project view** (the start page or the project tree). Do not open a PCB or schematic first.
3. Click **File → Import → KiCad...**
4. Select `hardware/board_routed.kicad_pcb` and confirm.
5. A board appears in the project tree. Double-click its PCB to open it.
6. Use **View → Fit All**.

## 2. After import

1. Rebuild the copper pours: **Tools → Copper Manager... → Rebuild All → Confirm**. The file contains the pour outlines but EasyEDA computes the fill itself.
2. Check that the red/blue traces are all there and that the top edge of the board (ESP32 antenna end) has no copper on either layer.
3. Run **Design → Check DRC**.

Known DRC findings that are fine:

- J1 (USB-C) GND and VBUS pads are 0.10 mm apart. That is the library footprint (LCSC C165948), widely used on JLCPCB.
- Silkscreen overlaps: reference texts overlap each other or pads. JLCPCB trims silk on pads. Move the texts if you like.

## 3. Order

1. Check the LCSC numbers in `bom.csv`. Stock was checked against JLCPCB on 2026-11-03; all parts were in stock (ESP32-C6-MINI-1-N4 C5736265: 3400, WS2812B-B-V6 C52941391: 7725, AP2114H-3.3 C150716: 2858). Re-match in the BOM tool before ordering.
2. In EasyEDA use **Export → PCB Fabrication File(Gerber)** and click **Export Gerber**. On jlcpcb.com upload the zip, turn on PCB Assembly, then upload `bom.csv` and `cpl.csv` instead of the generated files: the KiCad import carries no LCSC numbers, so JLCPCB guesses (it picked the out-of-stock C5453904 for U1 and found nothing for six parts). `cpl.csv` leaves out the screw holes (H1-H4) and TP1. Regenerate it if parts move.

## If something goes wrong

- **KiCad import is not in the menu:** you are inside a PCB or schematic editor. Close it and go to the project view.
- **Import fails or the board is empty:** tell me the error message. As a fallback import `board.kicad_pcb` (parts and nets only, no traces) and use **Route → Auto Router**.
- **Only the outline is needed:** open the PCB editor, then **File → Import → DXF**, choose `board_outline.dxf` (units are mm), layer **Board Outline**.

## Enclosure

- `base_indicator_light.stl` has a solid floor; there is no button. `base.py` regenerates it from commit 62c14d3 (old floor flexure filled). Do not edit the STL and rerun the script, or the edit is lost.
- Download mode: open the enclosure and short the two bare TP1 pads on the PCB bottom while plugging in USB.
- Zigbee factory reset: plug the light in 5 times in a row (firmware counts power-ups).

## JLCPCB order settings

Board: 32.4 x 32.4 mm. If the order form shows another size (70.4 mm was seen), the EasyEDA import added stray geometry: show only the Board Outline layer, delete everything else on it, and re-check before ordering.

| Setting | Value | Note |
|---|---|---|
| Base material / layers | FR-4, 2 | |
| Dimensions | 32.4 x 32.4 mm | must not read 70.4 |
| PCB qty | 5 | |
| Product type | industrial electronics | |
| Different design / delivery format | 1 / single PCB | |
| Thickness | 1.6 mm | |
| Solder mask / silkscreen | green / white | Economic PCBA: white mask only with leaded HASL |
| Material | FR-4 standard Tg (130-135) | |
| Surface finish | Lead-free HASL | TP1 are bare copper pads on the bottom: OSP oxidises there. ENIG is flatter but ~15x the price. NOTE: not the default, change it |
| Outer copper | 1 oz | |
| Via covering | tented | Required: vias must not be exposed near the grounded USB-C shell |
| Min via hole | 0.3 mm | Board vias are 0.4 mm |
| Outline tolerance | +-0.2 mm (regular) | Enclosure gap is 0.3 mm |
| Confirm production file | yes (first order) | NOTE: not the default, change it |
| Mark on PCB | remove mark | May cost extra |
| Electrical test | flying probe, full | |
| Gold fingers, castellated, edge plating, blind slots, UL mark, HIC | no | |

Assembly:

| Setting | Value | Note |
|---|---|---|
| PCBA type | Economic | All parts are on the top side, so Economic is enough and cheaper. Max 50 boards |
| Assembly side / qty | top / 5 | |
| Edge rails / fiducials | added by JLCPCB | |
| Confirm parts placement | yes | Check polarity of D1, D2 (SOD-123), pin 1 of LED1 and orientation of U1 and J1 |
| Parts selection | by customer (self-service) | Extended parts (U1, J1, LED1, D2) carry a fee each |
| Depanel boards and rails before delivery | yes | Leftover tab stubs would eat the 0.3 mm enclosure gap. NOTE: not the default, change it |
| Solder paste | high temp (lead-free) | |
| Stencil/fixture storage, bake, cleaning, tests, photo, coating, special stencil, nitrogen | no | |
| Packaging | antistatic bubble film | |

## Regenerating (not needed for import)

- `python3 build_pcb.py` rewrites `board.kicad_pcb` (parts, nets and placement).
- `python3 route.py <freerouting.jar> <java>` routes it into `board_routed.kicad_pcb`. It needs KiCad 9's python module (`pcbnew`), Freerouting 2.5 and Java 25.
- Do not run `generate.py`; it is outdated.
