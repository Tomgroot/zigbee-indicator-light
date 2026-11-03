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

1. Check the LCSC numbers in `bom.csv`. The ESP32 module (C18203071) may be out of stock, so pick any in-stock ESP32-H2-MINI-1 variant (same footprint).
2. Use **Order → PCB / Assembly** in EasyEDA.

## If something goes wrong

- **KiCad import is not in the menu:** you are inside a PCB or schematic editor. Close it and go to the project view.
- **Import fails or the board is empty:** tell me the error message. As a fallback import `board.kicad_pcb` (parts and nets only, no traces) and use **Route → Auto Router**.
- **Only the outline is needed:** open the PCB editor, then **File → Import → DXF**, choose `board_outline.dxf` (units are mm), layer **Board Outline**.

## Enclosure

- `base_indicator_light.stl` has a solid floor; there is no button. `base.py` regenerates it from commit 62c14d3 (old floor flexure filled). Do not edit the STL and rerun the script, or the edit is lost.
- Download mode: open the enclosure and short the two bare TP1 pads on the PCB bottom while plugging in USB.
- Zigbee factory reset: plug the light in 5 times in a row (firmware counts power-ups).

## Regenerating (not needed for import)

- `python3 build_pcb.py` rewrites `board.kicad_pcb` (parts, nets and placement).
- `python3 route.py <freerouting.jar> <java>` routes it into `board_routed.kicad_pcb`. It needs KiCad 9's python module (`pcbnew`), Freerouting 2.5 and Java 25.
- Do not run `generate.py`; it is outdated.
