"""Writes board.kicad_pcb (KiCad 5 format, for EasyEDA Pro File > Import > KiCad).
Footprints come from EasyEDA's library via easyeda2kicad (footprints/). Coordinates in mm, y points down:
antenna edge at the top, USB-C edge at the bottom, button on the right."""
import math
import re

H, R = 16.2, 10  # half board size, corner radius
HOLES = [(sx * 11.5, sy * 11.5) for sx in (-1, 1) for sy in (-1, 1)]  # M2 screw holes, dia 2.2
GND, VBUS, VLED, V33 = "GND", "VBUS", "VLED", "3V3"
FP = dict(
    esp="WIFIM-SMD_61P-L16.6-W13.2-P0.80-ESP32-C6-MINI-1-N4", usb="USB-C_SMD-TYPE-C-31-M-12_1",
    led="LED-SMD_4P-L5.0-W5.0-TL_WS2812B-B", tp="TESTPAD_BOOT",
    reg="SOT-223-3_L6.5-W3.4-P2.30-LS7.0-BR", d="SOD-123F_L2.7-W1.6-LS3.8-RD",
    c8="C0805", c6="C0603", r6="R0603",
)
# ref: (footprint, value, x, y, rotation, {pad name: net})
PARTS = {
    "U1": ("esp", "ESP32-C6-MINI-1", 0, -5.22, 0, {
        "3": V33, "8": "EN", "23": "BOOT", "22": "IO8", "20": "IO15", "19": "IO14",
        "17": "USB_DN", "18": "USB_DP", "1": GND, "2": GND, "11": GND, "14": GND,
        **{str(n): GND for n in range(36, 54)}}),
    "J1": ("usb", "USB-C", 0, 11.11, 0, {
        "A1B12": GND, "B1A12": GND, "1": GND, "2": GND, "3": GND, "4": GND, "A4B9": VBUS, "B4A9": VBUS,
        "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN"}),
    "LED1": ("led", "WS2812B", 0, 3.4, 0, {"1": VLED, "3": GND, "4": "LED_DIN"}),
    "TP1": ("tp", "BOOT-GND", 3.5, 3, 0, {"1": "BOOT", "2": GND}),  # bottom side, bare pads: short them while plugging in = download mode
    "U2": ("reg", "AP2114H-3.3", -11.3, 0, 0, {"1": GND, "2": V33, "3": VBUS, "4": V33}),
    "D1": ("d", "1N4148W", 11.5, 7, 0, {"1": VLED, "2": VBUS}),
    "D2": ("d", "SMF5.0A", -7.4, 9.5, 0, {"1": GND, "2": VBUS}),  # TVS: hot-plug spikes would reach the LED (VDD max 5.3 V) through D1
    "C1": ("c8", "10uF", -9, -6.2, 0, {"1": VBUS, "2": GND}),
    "C2": ("c8", "22uF", -9, 5.5, 0, {"1": V33, "2": GND}),
    "C3": ("c8", "10uF", -8.3, -8, 0, {"1": GND, "2": V33}),  # bulk at U1.3
    "C4": ("c6", "100nF", -7.7, -9.6, 0, {"1": GND, "2": V33}),
    "C5": ("c6", "1uF", -13.5, 7.5, 0, {"1": "EN", "2": GND}),
    "C6": ("c6", "100nF", -4.6, 1.75, 0, {"1": GND, "2": VLED}),  # at LED1 VDD (pad 1, left side)
    "R1": ("r6", "5.1k", 10, 4, 0, {"1": "CC1", "2": GND}),
    "R2": ("r6", "5.1k", 13.5, 4, 0, {"1": "CC2", "2": GND}),
    "R3": ("r6", "10k", -13.5, 5.5, 0, {"1": V33, "2": "EN"}),
    "R4": ("r6", "10k", 9.5, -6, 0, {"1": V33, "2": "BOOT"}),
    "R5": ("r6", "10k", 9.5, -4, 0, {"1": V33, "2": "IO8"}),
    "R6": ("r6", "10k", 9.5, -2, 0, {"1": V33, "2": "IO15"}),
    "R7": ("r6", "470R", 6.5, 2.5, 0, {"1": "IO14", "2": "LED_DIN"}),
    "R8": ("r6", "10k", 9.1, 2.5, 0, {"1": "LED_DIN", "2": GND}),  # keeps DIN low until firmware drives it
}
nets = ["", GND, VBUS, VLED, V33] + sorted({n for p in PARTS.values() for n in p[5].values()} - {GND, VBUS, VLED, V33})
net_id = {n: i for i, n in enumerate(nets)}


def blocks(text, head):
    """Yield (start, end) of every balanced `(head ...)` block."""
    for m in re.finditer(r"\(" + head + r"\b", text):
        depth, i = 0, m.start()
        while True:
            depth += text[i] == "("
            depth -= text[i] == ")"
            i += 1
            if depth == 0:
                break
        yield m.start(), i


def pad_name(pad):
    return re.match(r'\(pad ("[^"]*"|\S+)', pad).group(1).strip('"')


def module(ref, spec):
    fp, value, x, y, rot, padnets = spec
    t = open(f"footprints/{FP[fp]}.kicad_mod").read()
    for head in ("model", "property"):
        for s, e in reversed(list(blocks(t, head))):
            t = t[:s] + t[e:]
    t = re.sub(r"\(tedit [0-9A-Fa-f]+\)", f"(tedit 0) (at {x} {y} {rot})", t, count=1)
    t = t.replace("fp_text reference REF**", f"fp_text reference {ref}").replace(f"fp_text value {FP[fp]}", f"fp_text value {value}")
    names = set()
    for s, e in reversed(list(blocks(t, "pad"))):
        pad = t[s:e]
        name = pad_name(pad)
        names.add(name)
        if name == "" and "thru_hole" in pad:  # unnamed round holes are locating pegs, not plated
            pad = pad.replace("thru_hole", "np_thru_hole", 1)
        pad = re.sub(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", lambda m: f"(at {m[1]} {m[2]} {float(m[3] or 0) + rot})", pad, count=1)
        if name in padnets:
            pad = pad[:-1] + f' (net {net_id[padnets[name]]} "{padnets[name]}"))'
        t = t[:s] + pad + t[e:]
    assert set(padnets) <= names, (ref, set(padnets) - names)
    return t


def holes():
    return "".join(
        f'(module MountingHole_2.2mm (layer F.Cu) (tedit 0) (at {x} {y})\n\t(fp_text reference H{i} (at 0 0) (layer F.SilkS) hide (effects (font (size 1 1) (thickness 0.15))))\n\t(fp_text value M2 (at 0 0) (layer F.Fab) hide (effects (font (size 1 1) (thickness 0.15))))\n\t(pad "" np_thru_hole circle (at 0 0) (size 2.2 2.2) (drill 2.2) (layers *.Cu *.Mask))\n)\n'
        for i, (x, y) in enumerate(HOLES, 1))


def outline():
    pts = []
    for cx, cy, a0 in [(H - R, -H + R, -90), (H - R, H - R, 0), (-H + R, H - R, 90), (-H + R, -H + R, 180)]:
        pts += [(cx + R * math.cos(math.radians(a0 + 90 * k / 16)), cy + R * math.sin(math.radians(a0 + 90 * k / 16))) for k in range(17)]
    return "".join(
        f"(gr_line (start {a[0]:.3f} {a[1]:.3f}) (end {b[0]:.3f} {b[1]:.3f}) (layer Edge.Cuts) (width 0.15))\n"
        for a, b in zip(pts, pts[1:] + pts[:1]))


layers = "(0 F.Cu signal) (31 B.Cu signal) (32 B.Adhes user) (33 F.Adhes user) (34 B.Paste user) (35 F.Paste user) (36 B.SilkS user) (37 F.SilkS user) (38 B.Mask user) (39 F.Mask user) (40 Dwgs.User user) (41 Cmts.User user) (44 Edge.Cuts user) (46 B.CrtYd user) (47 F.CrtYd user) (48 B.Fab user) (49 F.Fab user)"
out = f"(kicad_pcb (version 20171130) (host pcbnew 5.1.0)\n(general (thickness 1.6))\n(page A4)\n(layers {layers})\n(setup (pad_to_mask_clearance 0))\n"
out += "".join(f'(net {i} "{n}")\n' for i, n in enumerate(nets))
out += '(net_class Default "" (clearance 0.15) (trace_width 0.25) (via_dia 0.8) (via_drill 0.4) (uvia_dia 0.3) (uvia_drill 0.1)' + "".join(f' (add_net "{n}")' for n in nets[1:]) + ")\n"
out += "".join(module(r, s) + "\n" for r, s in PARTS.items()) + holes() + outline() + ")\n"
open("board.kicad_pcb", "w").write(out)

# self-check: parens balance, every non-NC net has >=2 pads, pads of different parts don't overlap
assert out.count("(") == out.count(")")
rects = []
for ref in PARTS.keys() - {"TP1"}:  # TP1 is on the bottom layer
    m = re.search(rf"\(fp_text reference {re.escape(ref)} ", out)
    s = out.rfind("(module", 0, m.start())
    mod = out[s:next(e for st, e in blocks(out[s:], "module")) + s]
    for ps, pe in blocks(mod, "pad"):
        pad = mod[ps:pe]
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", pad)
        sz = re.search(r"\(size ([-\d.]+) ([-\d.]+)\)", pad)
        if "(drill" not in pad and float(sz[1]) > 0.1 and "custom" not in pad:
            _, _, mx, my, mr, _ = PARTS[ref]
            a = math.radians(mr)
            px, py, w, h = float(at[1]), float(at[2]), float(sz[1]), float(sz[2])
            if (float(at[3] or 0) - mr) % 180 == 90:
                w, h = h, w
            cx = mx + px * math.cos(a) + py * math.sin(a)
            cy = my - px * math.sin(a) + py * math.cos(a)
            net = re.search(r"\(net (\d+)", pad)
            rects.append((ref, pad_name(pad), cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, net[1] if net else None))
bad = [(a[:2], b[:2]) for i, a in enumerate(rects) for b in rects[i + 1:]
       if a[0] != b[0] and a[2] < b[4] + 0.1 and b[2] < a[4] + 0.1 and a[3] < b[5] + 0.1 and b[3] < a[5] + 0.1]
print("outside:", [r[:2] + tuple(round(v, 2) for v in r[2:6]) for r in rects if not (-H < r[2] and r[4] < H and -H < r[3] and r[5] < H)])
print("pads", len(rects), "overlap/<0.1mm pairs:", bad)
