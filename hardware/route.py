"""board.kicad_pcb -> board_routed.kicad_pcb (KiCad 5.1 format, the newest EasyEDA Pro imports): design rules, antenna keepout, Freerouting, GND pours.
Needs KiCad's pcbnew python module and java (see README). Usage: python3 route.py <freerouting.jar> <java>"""
import re
import subprocess
import sys

import pcbnew

jar, java = sys.argv[1:3]
mm = pcbnew.FromMM
b = pcbnew.LoadBoard("board.kicad_pcb")
ds = b.GetDesignSettings()
ds.m_MinClearance, ds.m_CopperEdgeClearance, ds.m_TrackMinWidth = mm(0.1), mm(0.3), mm(0.25)  # EasyEDA's default rules (stricter than JLCPCB's 0.127 / 0.3) so its DRC passes
ds.m_ViasMinSize, ds.m_ViasMinAnnulus, ds.m_MinThroughDrill = mm(0.8), mm(0.13), mm(0.3)
ns = ds.m_NetSettings
default = ns.GetDefaultNetclass()
default.SetClearance(mm(0.15)), default.SetTrackWidth(mm(0.25)), default.SetViaDiameter(mm(0.8)), default.SetViaDrill(mm(0.4))


def zone(layers, points, name, net=None, keepout=False, tracks=False, vias=False):
    z = pcbnew.ZONE(b)
    ls = pcbnew.LSET()
    for layer in layers:
        ls.AddLayer(layer)
    z.SetLayerSet(ls)
    z.SetZoneName(name)
    if keepout:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowCopperPour(not (tracks or vias)), z.SetDoNotAllowTracks(not tracks), z.SetDoNotAllowVias(not vias)
        z.SetDoNotAllowPads(False), z.SetDoNotAllowFootprints(False)
    else:
        z.SetNetCode(b.GetNetcodeFromNetname(net))
        z.SetMinThickness(mm(0.25)), z.SetLocalClearance(mm(0.2)), z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in points:
        ol.Append(mm(x), mm(y))
    b.Add(z)
    return z


H = 16.2
both = [pcbnew.F_Cu, pcbnew.B_Cu]
rect = lambda x0, y0, x1, y1: [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
# antenna end of the module: no copper on any layer across the full board width (ESP32 module is flush with the top edge)
KEEPOUT = rect(-H - 1, -H - 1, H + 1, -10.6)
# (name, layers, points, tracks allowed, vias allowed)
RULES = [
    ("usb_shell", ["F.Cu", "B.Cu"], rect(-4.5, 8.85, 4.5, H + 1), True, False),  # grounded metal shell sits on these
]
zone(both, KEEPOUT, "antenna_keepout", keepout=True)
for name, ls, pts, tracks, vias in RULES:
    zone([b.GetLayerID(l) for l in ls], pts, name, keepout=True, tracks=tracks, vias=vias)
pcbnew.SaveBoard("/tmp/route_in.kicad_pcb", b)
pcbnew.ExportSpecctraDSN(b, "/tmp/route.dsn")

subprocess.run([java, "-jar", jar, "--gui.enabled=false", "-de", "/tmp/route.dsn", "-do", "/tmp/route.ses", "-mp", "40"], check=True)
assert pcbnew.ImportSpecctraSES(b, "/tmp/route.ses"), "SES import failed"

for t in b.GetTracks():  # the router narrows stubs near fine-pitch pads below the minimum width
    if t.GetClass() == "PCB_TRACK" and t.GetWidth() < mm(0.25):
        t.SetWidth(mm(0.25))

# GND stitching vias on a 2 mm grid wherever they clear other nets, the keepouts and the screw heads
gnd = b.GetNetcodeFromNetname("GND")
holes = [(sx * 11.5, sy * 11.5) for sx in (-1, 1) for sy in (-1, 1)]
inside = lambda x, y, pts: pts[0][0] <= x <= pts[2][0] and pts[0][1] <= y <= pts[2][1]
no_via = [KEEPOUT] + [pts for _, _, pts, _, vias in RULES if not vias]
vias_at = [t.GetPosition() for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
copper = [t for t in b.GetTracks() if t.GetNetCode() != gnd] + [p for f in b.GetFootprints() for p in f.Pads() if p.GetNetCode() != gnd]
stitched = 0
for i in range(-8, 9):
    for j in range(-8, 9):
        x, y = i * 2.0, j * 2.0
        cx, cy = max(abs(x) - 6.2, 0), max(abs(y) - 6.2, 0)  # distance outside the rounded corner centres
        if (cx * cx + cy * cy) ** 0.5 > 10 - 1.0 or any(inside(x, y, pts) for pts in no_via) or any((x - hx) ** 2 + (y - hy) ** 2 < 3.5 ** 2 for hx, hy in holes) \
                or any(abs(mm(x) - p.x) < mm(1.2) and abs(mm(y) - p.y) < mm(1.2) for p in vias_at):
            continue
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))), v.SetWidth(mm(0.8)), v.SetDrill(mm(0.4)), v.SetNetCode(gnd)
        if any(c.GetEffectiveShape(layer).Collide(v.GetEffectiveShape(layer), mm(0.25)) for c in copper for layer in both if c.IsOnLayer(layer)):
            continue
        b.Add(v)
        stitched += 1
print("stitching vias", stitched)

pour = [(-H + 0.3, -H + 0.3), (H - 0.3, -H + 0.3), (H - 0.3, H - 0.3), (-H + 0.3, H - 0.3)]
zone([pcbnew.F_Cu], pour, "gnd_top", "GND")
zone([pcbnew.B_Cu], pour, "gnd_bottom", "GND")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard("/tmp/route_check.kicad_pcb", b)  # KiCad 9 copy, only for DRC

# KiCad 9 can't write the 5.1 format, so append the routing to the 5.1 file we generated
src = open("board.kicad_pcb").read().rstrip()
codes = {name: int(code) for code, name in re.findall(r'^\(net (\d+) "([^"]*)"\)$', src, re.M)}
net = lambda n: f"(net {codes[n]})"
mm_ = pcbnew.ToMM
lines = []
for t in b.GetTracks():
    layer = b.GetLayerName(t.GetLayer())
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        lines.append(f"(via (at {mm_(p.x):.4f} {mm_(p.y):.4f}) (size {mm_(t.GetWidth(t.GetLayer())):.3f}) (drill {mm_(t.GetDrillValue()):.3f}) (layers F.Cu B.Cu) {net(t.GetNetname())})")
    else:
        p, q = t.GetStart(), t.GetEnd()
        lines.append(f"(segment (start {mm_(p.x):.4f} {mm_(p.y):.4f}) (end {mm_(q.x):.4f} {mm_(q.y):.4f}) (width {mm_(t.GetWidth()):.3f}) (layer {layer}) {net(t.GetNetname())})")


def poly(points):
    return "(polygon (pts " + " ".join(f"(xy {x} {y})" for x, y in points) + "))"


for layer in ("F.Cu", "B.Cu"):
    lines.append(f'(zone {net("GND")} (net_name "GND") (layer {layer}) (tstamp 0) (hatch edge 0.508) (connect_pads yes (clearance 0.2)) (min_thickness 0.25) (fill yes (arc_segments 16) (thermal_gap 0.2) (thermal_bridge_width 0.3)) {poly(pour)})')
allowed = lambda ok: "allowed" if ok else "not_allowed"
for name, ls, pts, tracks, vias in [("antenna_keepout", ["F.Cu", "B.Cu"], KEEPOUT, False, False)] + RULES:
    lines.append(f'(zone (net 0) (net_name "") (layers {" ".join(ls)}) (tstamp 0) (hatch edge 0.508) (connect_pads (clearance 0.2)) (min_thickness 0.25) (keepout (tracks {allowed(tracks)}) (vias {allowed(vias)}) (copperpour {allowed(tracks or vias)})) (fill (arc_segments 16) (thermal_gap 0.2) (thermal_bridge_width 0.3)) {poly(pts)})')
assert src.endswith(")")
open("board_routed.kicad_pcb", "w").write(src[:-1] + "\n" + "\n".join(lines) + "\n)\n")
print("tracks", len(b.GetTracks()), "zones", len(b.Zones()))
