"""Draws circuit_diagram.svg from the netlist in PCB.md. Sections are joined by net names: the same label means the same wire."""
out = []


def line(x1, y1, x2, y2):
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"/>')


def text(x, y, s, anchor="start", size=14, bold=False):
    out.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="{size}"{" font-weight=\'bold\'" if bold else ""} fill="#111" stroke="none">{s}</text>')


def dot(x, y):
    out.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="#111"/>')


def box(x, y, w, h, title):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="#f4f7fb"/>')
    text(x + w / 2, y - 8, title, "middle", 14, True)


def pin(x, y, name, side):
    """Pin stub with its name inside the box. side: left/right/bottom."""
    if side == "left":
        text(x + 8, y + 5, name)
    elif side == "right":
        text(x - 8, y + 5, name, "end")
    else:
        text(x, y - 8, name, "middle")


def res(x, y1, y2, ref, value, side="left"):
    """Vertical resistor between y1 and y2 at x."""
    mid, h = (y1 + y2) / 2, 30
    line(x, y1, x, mid - h / 2), line(x, mid + h / 2, x, y2)
    out.append(f'<rect x="{x - 7}" y="{mid - h / 2}" width="14" height="{h}" fill="white"/>')
    text(x - 14 if side == "left" else x + 14, mid - 2, ref, "end" if side == "left" else "start", 13, True)
    text(x - 14 if side == "left" else x + 14, mid + 13, value, "end" if side == "left" else "start", 12)


def res_h(x1, x2, y, ref, value):
    mid = (x1 + x2) / 2
    line(x1, y, mid - 15, y), line(mid + 15, y, x2, y)
    out.append(f'<rect x="{mid - 15}" y="{y - 7}" width="30" height="14" fill="white"/>')
    text(mid, y - 14, f"{ref} {value}", "middle", 13)


def cap(x, y1, y2, ref, value, side="left"):
    mid = (y1 + y2) / 2
    line(x, y1, x, mid - 4), line(x, mid + 4, x, y2)
    line(x - 11, mid - 4, x + 11, mid - 4), line(x - 11, mid + 4, x + 11, mid + 4)
    text(x - 16 if side == "left" else x + 16, mid - 1, ref, "end" if side == "left" else "start", 13, True)
    text(x - 16 if side == "left" else x + 16, mid + 14, value, "end" if side == "left" else "start", 12)


def gnd(x, y):
    line(x, y, x, y + 6), line(x - 12, y + 6, x + 12, y + 6), line(x - 8, y + 11, x + 8, y + 11), line(x - 4, y + 16, x + 4, y + 16)


def flag(x, y, name, up=True, anchor=None):
    """Net label. Up: stub going up with name above. Otherwise a horizontal stub with the name beside it."""
    if up:
        line(x, y, x, y - 14), text(x, y - 20, name, "middle", 13, True)
    else:
        text(x - 6, y + 5, name, "end", 13, True)


def diode_h(x1, x2, y, ref, value):
    mid = (x1 + x2) / 2
    line(x1, y, mid - 8, y), line(mid + 8, y, x2, y)
    out.append(f'<polygon points="{mid - 8},{y - 9} {mid - 8},{y + 9} {mid + 8},{y}" fill="white"/>')
    line(mid + 8, y - 9, mid + 8, y + 9)
    text(mid, y - 16, f"{ref} {value}", "middle", 13)


def button(x, y1, y2, ref, value):
    mid = (y1 + y2) / 2
    line(x, y1, x, mid - 12), line(x, mid + 12, x, y2)
    line(x - 10, mid - 12, x + 10, mid - 12), line(x - 10, mid + 12, x + 10, mid + 12)
    line(x - 10, mid - 12, x - 10, mid - 17)  # lever
    text(x - 16, mid - 2, ref, "end", 13, True)
    text(x - 16, mid + 13, value, "end", 12)


def title(x, y, s):
    text(x, y, s, "start", 17, True)


# ---- 1. USB-C ------------------------------------------------------------------------------
title(30, 50, "1. USB-C input")
box(60, 90, 150, 350, "J1 USB-C")
for y, n in ((130, "VBUS"), (200, "CC1"), (260, "CC2"), (350, "D+"), (400, "D-")):
    line(210, y, 235, y), pin(210, y, n, "right")
line(210, 130, 330, 130), dot(330, 130)
out.append('<text x="338" y="135" font-size="13" font-weight="bold" fill="#111" stroke="none">VBUS (5 V)</text>')
dot(290, 130), line(290, 130, 290, 142), line(290, 158, 290, 170), gnd(290, 170)  # D2 TVS, cathode to VBUS
out.append('<polygon points="281,158 299,158 290,142" fill="white"/>'), line(281, 142, 299, 142)
text(306, 152, "D2", "start", 13, True), text(306, 167, "SMF5.0A", "start", 12)
line(210, 200, 340, 200), dot(340, 200), res(340, 200, 290, "R1", "5.1k", "right"), gnd(340, 290)
line(210, 260, 270, 260), dot(270, 260), res(270, 260, 320, "R2", "5.1k", "left"), gnd(270, 320)
line(210, 350, 330, 350), text(338, 355, "USB_D+", "start", 13, True)
line(210, 400, 330, 400), text(338, 405, "USB_D-", "start", 13, True)
line(135, 440, 135, 450), pin(135, 440, "GND", "bottom"), gnd(135, 450)
text(60, 500, "CC1/CC2 resistors tell the charger", "start", 12), text(60, 517, "\"I am a device, give me 5 V\".", "start", 12)

# ---- 2. 3.3 V regulator --------------------------------------------------------------------
title(480, 50, "2. 3.3 V regulator")
box(600, 90, 160, 110, "U2 AP2114H-3.3")
line(540, 130, 600, 130), pin(600, 130, "VIN", "left"), flag(520, 130, "VBUS", up=False), line(520, 130, 540, 130)
dot(560, 130), cap(560, 130, 190, "C1", "10uF", "left"), gnd(560, 190)
line(760, 130, 900, 130), pin(760, 130, "VOUT", "right")
dot(800, 130), cap(800, 130, 190, "C2", "22uF", "right"), gnd(800, 190)
dot(880, 130), cap(880, 130, 190, "C3", "10uF", "right"), gnd(880, 190)
line(880, 130, 930, 130), text(938, 135, "3V3", "start", 13, True)
line(680, 200, 680, 215), pin(680, 200, "GND", "bottom"), gnd(680, 215)

# ---- 3. RGB LED ----------------------------------------------------------------------------
title(480, 330, "3. RGB LED")
text(480, 352, "D1 drops VBUS to ~4.3 V so the 3.3 V data signal counts as a valid high.", "start", 12)
line(480, 420, 500, 420), flag(480, 420, "VBUS", up=False)
diode_h(500, 580, 420, "D1", "1N4148W"), dot(600, 420), line(580, 420, 600, 420), text(612, 410, "VLED", "start", 13, True)
cap(600, 420, 460, "C6", "100nF", "left"), gnd(600, 460)
box(740, 380, 160, 150, "LED1 WS2812B")
line(600, 420, 740, 420), pin(740, 420, "VDD", "left")
line(690, 500, 740, 500), pin(740, 500, "DIN", "left"), res_h(640, 690, 500, "R7", "470R")
line(640, 500, 625, 500)
dot(715, 500), res(715, 500, 570, "R8", "10k", "left"), gnd(715, 570)
text(619, 505, "IO14", "end", 13, True)
line(820, 530, 820, 545), pin(820, 530, "VSS", "bottom"), gnd(820, 545)

# ---- 4. ESP32 ------------------------------------------------------------------------------
title(980, 50, "4. ESP32-C6 module (Zigbee/Thread/Wi-Fi radio + antenna)")
box(1230, 90, 220, 650, "U1 ESP32-C6-MINI-1")
rows = {"3V3": 140, "EN": 270, "IO9": 400, "IO8": 520, "IO15": 590, "IO13": 650, "IO12": 700}
for n, y in rows.items():
    line(1210, y, 1230, y), pin(1230, y, n, "left")
line(1210, 140, 1170, 140), dot(1170, 140), line(1170, 140, 1170, 120), flag(1170, 120, "3V3")
dot(1130, 140), line(1170, 140, 1130, 140), cap(1130, 140, 200, "C4", "100nF", "left"), gnd(1130, 200)
# EN: pull-up and delay capacitor
line(1210, 270, 1070, 270), dot(1070, 270)
res(1070, 190, 270, "R3", "10k", "left"), flag(1070, 190, "3V3")
cap(1070, 270, 330, "C5", "1uF", "left"), gnd(1070, 330)
# IO9 / BOOT: pull-up and button
line(1210, 400, 990, 400), dot(990, 400)
res(990, 320, 400, "R4", "10k", "left"), flag(990, 320, "3V3")
line(990, 400, 990, 424), line(990, 462, 990, 470), gnd(990, 470)
out.append('<circle cx="990" cy="430" r="6" fill="white"/><circle cx="990" cy="456" r="6" fill="white"/>')
text(974, 436, "TP1", "end", 13, True), text(974, 451, "bare pads", "end", 12)
# IO8 and IO15: pull-ups only (strapping pins)
line(1210, 520, 1130, 520), dot(1130, 520), res(1130, 450, 520, "R5", "10k", "left"), flag(1130, 450, "3V3")
line(1210, 590, 1070, 590), dot(1070, 590), res(1070, 520, 590, "R6", "10k", "left"), flag(1070, 520, "3V3")
# USB data
for y, n in ((650, "USB_D+"), (700, "USB_D-")):
    line(1210, y, 1100, y), text(1094, y + 5, n, "end", 13, True)
# LED data out, ground
line(1450, 140, 1490, 140), text(1496, 145, "IO14", "start", 13, True), pin(1450, 140, "IO14", "right")
line(1340, 740, 1340, 755), pin(1340, 740, "GND", "bottom"), gnd(1340, 755)
text(480, 640, "IO8 / IO15 pull-ups keep these strapping pins from floating.", "start", 12)
text(480, 660, "Short the TP1 pads while plugging in USB = flash mode.", "start", 12)
text(480, 677, "Plug in 5 times in a row = Zigbee factory reset (firmware).", "start", 12)
text(30, 830, "Same net name = same wire (VBUS, 3V3, VLED, USB_D+, USB_D-, IO14). All ground symbols are connected.", "start", 13)

svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1560" height="860" viewBox="0 0 1560 860" font-family="sans-serif">\n<rect width="1560" height="860" fill="white"/>\n<g stroke="#111" stroke-width="2" fill="none" stroke-linecap="round">\n' + "\n".join(out) + "\n</g>\n</svg>\n"
open("circuit_diagram.svg", "w").write(svg)
