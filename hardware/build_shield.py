"""Writes shield.kicad_pcb (KiCad 5 format: opens in KiCad and EasyEDA Pro File > Import > KiCad).
LED shield that slides onto the long header pins under an ESP32-H2 SuperMini (2x9, 2.54 mm pitch, rows 15.24 mm apart,
measured from the SuperMini STEP model). Parts sit on the top layer, which faces AWAY from the SuperMini, so the pin rows
are mirrored compared with the SuperMini's own top-view pinout. Coordinates in mm, y down, SuperMini USB end at the top."""
import math
import re
import sys


def blocks(text, head):  # copied from build_pcb.py, which writes board.kicad_pcb on import
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


W, L = 18, 23.6  # SuperMini outline (H2-Zero: 18 x 23.5)
HOLE_X, TAB_X, TAB_H = 12, 14.5, 6  # M2 holes at (±HOLE_X, 0) in side tabs; screw heads clear the SuperMini (x ±9) hanging below
ZERO = sys.argv[1:] == ["zero"]  # `python3 build_shield.py zero` writes the Waveshare ESP32-H2-Zero variant
FP = dict(led="LED-SMD_4P-L5.0-W5.0-TL_WS2812B-B", d="SOD-123F_L2.7-W1.6-LS3.8-RD", c6="C0603", r6="R0603")
if not ZERO:
    NAME, OUT, DATA = "SuperMini", "shield.kicad_pcb", "IO8"
    POWER_ROW = ["5V", "GND", "3V3", "IO14", "IO13", "IO12", "IO11", "IO10", "IO9"]  # SuperMini right row (top view), from USB end
    OTHER_ROW = ["IO24", "IO23", "IO0", "IO1", "IO2", "IO3", "IO4", "IO5", "IO8"]  # SuperMini left row (top view)
    LABEL_Y = 10.2
    PSX = -1  # x side of the power row on the shield (mirrored top view)
    # ref: (footprint, value, x, y, rotation, {pad: net})
    PARTS = {
        "LED1": ("led", "SK6812-B", 0, 0, 0, {"1": "VLED", "3": "GND", "4": "LED_DIN"}),
        "D1": ("d", "1N4148W", -3.5, -9, 180, {"1": "VLED", "2": "5V"}),  # drops VDD to ~4.2 V so 3.3 V data meets VIH (0.7 VDD)
        "C1": ("c6", "100nF", -5, -1.65, 0, {"1": "GND", "2": "VLED"}),
        "R1": ("r6", "470R", 5, 4, 90, {"1": "LED_DIN_RAW", "2": "LED_DIN"}),
    }
    # (net, width, [points]) on F.Cu
    TRACKS = [
        ("5V", 0.4, [(-7.62, -10.16), (-5.23, -9)]),
        ("VLED", 0.4, [(-1.77, -9), (-2.45, -4), (-2.45, -1.65)]),
        ("VLED", 0.4, [(-4.25, -1.65), (-2.45, -1.65)]),
        ("GND", 0.4, [(-7.62, -7.62), (-5.75, -5.75), (-5.75, 3.5), (2.45, 3.5), (2.45, 1.65)]),
        ("LED_DIN_RAW", 0.25, [(7.62, 10.16), (5, 7.54), (5, 4.7)]),
        ("LED_DIN", 0.25, [(5, 3.3), (5, -1.65), (2.45, -1.65)]),
    ]
else:
    NAME, OUT, DATA = "H2-Zero", "shield_zero.kicad_pcb", "IO22"  # IO8 is a bottom pad; IO10 sits at the chip antenna end
    POWER_ROW = ["5V", "GND", "3V3", "IO0", "IO1", "IO2", "IO3", "IO4", "IO5"]  # Zero left row (top view), from USB end
    OTHER_ROW = ["IO24", "IO23", "IO25", "IO22", "IO14", "IO13", "IO12", "IO11", "IO10"]  # Zero right row (top view)
    PSX, LABEL_Y = 1, -3.8
    PARTS = {
        "LED1": ("led", "SK6812-B", 0, 0, 270, {"1": "VLED", "3": "GND", "4": "LED_DIN"}),  # VDD top right, DIN bottom right, GND bottom left
        "D1": ("d", "1N4148W", 3, -9, 0, {"1": "VLED", "2": "5V"}),
        "C1": ("c6", "100nF", 4, -2.45, 180, {"1": "GND", "2": "VLED"}),
        "R1": ("r6", "470R", -5, 1.5, 270, {"1": "LED_DIN_RAW", "2": "LED_DIN"}),
    }
    TRACKS = [
        ("5V", 0.4, [(7.62, -10.16), (4.73, -9)]),
        ("VLED", 0.4, [(1.27, -9), (1.65, -5), (1.65, -2.45)]),
        ("VLED", 0.4, [(3.3, -2.45), (1.65, -2.45)]),
        ("GND", 0.4, [(7.62, -7.62), (5.75, -5.75), (5.75, -2.45), (4.7, -2.45)]),
        ("GND", 0.4, [(4.7, -2.45), (4.7, 0), (-1.65, 0), (-1.65, 2.45)]),  # between the LED pad rows
        ("LED_DIN_RAW", 0.25, [(-7.62, -2.54), (-5, -2.54), (-5, 0.75)]),
        ("LED_DIN", 0.25, [(-5, 2.25), (-5, 4.2), (1.65, 4.2), (1.65, 2.45)]),  # stays above the antenna keepout (y > 6.7)
    ]
PINS = {name: (sx * 7.62, (i - 4) * 2.54) for row, sx in ((POWER_ROW, PSX), (OTHER_ROW, -PSX)) for i, name in enumerate(row)}
NET_OF_PIN = {"5V": "5V", "GND": "GND", DATA: "LED_DIN_RAW"}
nets = ["", "GND", "5V", "VLED", "LED_DIN", "LED_DIN_RAW"]
net_id = {n: i for i, n in enumerate(nets)}


def module(ref, spec):
    fp, value, x, y, rot, padnets = spec
    t = open(f"footprints/{FP[fp]}.kicad_mod").read()
    for head in ("model", "property"):
        for s, e in reversed(list(blocks(t, head))):
            t = t[:s] + t[e:]
    t = re.sub(r"\(tedit [0-9A-Fa-f]+\)", f"(tedit 0) (at {x} {y} {rot})", t, count=1)
    t = t.replace("fp_text reference REF**", f"fp_text reference {ref}").replace(f"fp_text value {FP[fp]}", f"fp_text value {value}")
    for s, e in reversed(list(blocks(t, "pad"))):
        pad = t[s:e]
        name = pad_name(pad)
        pad = re.sub(r"\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", lambda m: f"(at {m[1]} {m[2]} {float(m[3] or 0) + rot})", pad, count=1)
        if name in padnets:
            pad = pad[:-1] + f' (net {net_id[padnets[name]]} "{padnets[name]}"))'
        t = t[:s] + pad + t[e:]
    return t


def header():
    pads = ""
    for name, (x, y) in PINS.items():
        net = NET_OF_PIN.get(name)
        shape = "rect" if name == "5V" else "circle"
        pads += f'\t(pad "{name}" thru_hole {shape} (at {x} {y}) (size 1.7 1.7) (drill 1.0) (layers *.Cu *.Mask)' + (f' (net {net_id[net]} "{net}")' if net else "") + ")\n"
    return (f"(module {NAME.replace('-', '_')}_2x9 (layer F.Cu) (tedit 0) (at 0 0)\n"
            "\t(fp_text reference J1 (at 0 -10.6) (layer F.SilkS) (effects (font (size 0.8 0.8) (thickness 0.15))))\n"
            f"\t(fp_text value ESP32-{NAME} (at 0 6) (layer F.Fab) (effects (font (size 0.8 0.8) (thickness 0.15))))\n"
            "\t(fp_text user \"USB\" (at 0 -10.8 180) (layer B.SilkS) (effects (font (size 0.8 0.8) (thickness 0.15)) (justify mirror)))\n"
            f"\t(fp_text user 5V (at {PSX * 5.6} -10.9) (layer F.SilkS) (effects (font (size 0.7 0.7) (thickness 0.12))))\n"
            f"\t(fp_text user {DATA} (at {-PSX * 5.2} {LABEL_Y}) (layer F.SilkS) (effects (font (size 0.7 0.7) (thickness 0.12))))\n"
            + pads + ")\n")


def holes():  # same as build_pcb.py
    return "".join(
        f'(module MountingHole_2.2mm (layer F.Cu) (tedit 0) (at {x} 0)\n\t(fp_text reference H{i} (at 0 0) (layer F.SilkS) hide (effects (font (size 1 1) (thickness 0.15))))\n\t(fp_text value M2 (at 0 0) (layer F.Fab) hide (effects (font (size 1 1) (thickness 0.15))))\n\t(pad "" np_thru_hole circle (at 0 0) (size 2.2 2.2) (drill 2.2) (layers *.Cu *.Mask))\n)\n'
        for i, x in enumerate((-HOLE_X, HOLE_X), 1))


def outline():
    x, y, t = W / 2, L / 2, TAB_H / 2
    pts = [(-x, -y), (x, -y), (x, -t), (TAB_X, -t), (TAB_X, t), (x, t), (x, y), (-x, y), (-x, t), (-TAB_X, t), (-TAB_X, -t), (-x, -t)]
    return "".join(f"(gr_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (layer Edge.Cuts) (width 0.15))\n" for a, b in zip(pts, pts[1:] + pts[:1]))


def tracks():
    return "".join(
        f'(segment (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (width {w}) (layer F.Cu) (net {net_id[n]}))\n'
        for n, w, pts in TRACKS for a, b in zip(pts, pts[1:]))


layers = "(0 F.Cu signal) (31 B.Cu signal) (34 B.Paste user) (35 F.Paste user) (36 B.SilkS user) (37 F.SilkS user) (38 B.Mask user) (39 F.Mask user) (44 Edge.Cuts user) (46 B.CrtYd user) (47 F.CrtYd user) (48 B.Fab user) (49 F.Fab user)"
out = f"(kicad_pcb (version 20171130) (host pcbnew 5.1.0)\n(general (thickness 1.6))\n(page A4)\n(layers {layers})\n(setup (pad_to_mask_clearance 0))\n"
out += "".join(f'(net {i} "{n}")\n' for i, n in enumerate(nets))
out += '(net_class Default "" (clearance 0.2) (trace_width 0.25) (via_dia 0.8) (via_drill 0.4) (uvia_dia 0.3) (uvia_drill 0.1)' + "".join(f' (add_net "{n}")' for n in nets[1:]) + ")\n"
out += header() + "".join(module(r, s) + "\n" for r, s in PARTS.items()) + tracks() + holes() + outline() + ")\n"
open(OUT, "w").write(out)

# self-check: every track end lands on a pad of its own net, copper of different nets keeps >= 0.2 mm apart
assert out.count("(") == out.count(")")
pads = [(x, y, 0.85, 0.85, NET_OF_PIN.get(n)) for n, (x, y) in PINS.items()]
for ref, (fp, _, mx, my, mr, padnets) in PARTS.items():
    for ps, pe in blocks(open(f"footprints/{FP[fp]}.kicad_mod").read(), "pad"):
        pad = open(f"footprints/{FP[fp]}.kicad_mod").read()[ps:pe]
        at = re.search(r"\(at ([-\d.]+) ([-\d.]+)", pad)
        sz = re.search(r"\(size ([-\d.]+) ([-\d.]+)\)", pad)
        a = math.radians(mr)
        px, py, w, h = float(at[1]), float(at[2]), float(sz[1]), float(sz[2])
        if mr % 180 == 90:
            w, h = h, w
        pads.append((mx + px * math.cos(a) + py * math.sin(a), my - px * math.sin(a) + py * math.cos(a), w / 2, h / 2, padnets.get(pad_name(pad))))


def dist_box(px, py, b):  # distance from point to pad rectangle
    return math.hypot(max(abs(px - b[0]) - b[2], 0), max(abs(py - b[1]) - b[3], 0))


for n, w, pts in TRACKS:
    for end in (pts[0], pts[-1]):
        assert any(b[4] == n and dist_box(*end, b) < 1e-6 for b in pads), (n, end)
    for a, b in zip(pts, pts[1:]):
        for k in range(101):
            px, py = a[0] + (b[0] - a[0]) * k / 100, a[1] + (b[1] - a[1]) * k / 100
            for p in pads:
                assert p[4] == n or dist_box(px, py, p) >= w / 2 + 0.2, (n, (round(px, 2), round(py, 2)), p)
            assert abs(px) <= W / 2 - 0.5 and abs(py) <= L / 2 - 0.5
print(OUT, "ok:", len(pads), "pads,", sum(len(t[2]) - 1 for t in TRACKS), "segments")
