"""Generates body.stl, cap.stl and board_outline.dxf. All dimensions in mm, origin = box centre."""
import ezdxf
import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold

BOX, BOX_R, WALL, FLOOR = 35.0, 4.0, 2.0, 2.0
BODY_H, CAP_T, LIP_H = 28.0, 2.0, 3.0
PCB, PCB_R, PCB_T = 30.4, 2.5, 1.6
POST_H = 2.0                      # PCB bottom sits FLOOR + POST_H above the table
PCB_TOP = FLOOR + POST_H + PCB_T
USB_Z = PCB_TOP + 1.63            # receptacle centreline of TYPE-C-31-M-12 above PCB
BTN_Y, BTN_Z = -7.0, PCB_TOP + 0.9


def rrect(w, h, r):
    return CrossSection.square([w - 2 * r, h - 2 * r], center=True).offset(r, JoinType.Round, circular_segments=64)


def wall_cut(w, h, r, depth, axis):
    """Rounded slot extruded `depth` mm along +axis ('x' or 'y'), centred on the origin plane."""
    m = rrect(w, h, r).extrude(depth)
    return m.rotate([0, 90, 0]) if axis == "x" else m.rotate([-90, 0, 0])


inner = BOX - 2 * WALL
body = rrect(BOX, BOX, BOX_R).extrude(BODY_H) - rrect(inner, inner, BOX_R - WALL).extrude(BODY_H).translate([0, 0, FLOOR])

c = inner / 2 - 2
for sx in (-1, 1):
    for sy in (-1, 1):
        body += Manifold.cube([4, 4, POST_H], center=False).translate([sx * c - 2, sy * c - 2, FLOOR])

# USB-C: through hole for the shell + outside recess for the plug overmould
body -= wall_cut(9.4, 3.6, 1.6, WALL + 1, "y").translate([0, -BOX / 2 - 0.5, USB_Z])
body -= wall_cut(12.5, 7.0, 2.0, 1.2 + 0.5, "y").translate([0, -BOX / 2 - 0.5, USB_Z])

# Button: wall thinned to 0.8 mm from outside, block on the inside pushes the side switch
body -= wall_cut(9.0, 11.0, 2.0, 1.2 + 0.5, "x").translate([BOX / 2 - 1.2, BTN_Y, BTN_Z])
body += Manifold.cube([0.6, 3.0, 2.0], center=True).translate([inner / 2 - 0.3 + 0.05, BTN_Y, BTN_Z])

lip_o = inner - 0.4
cap = rrect(BOX, BOX, BOX_R).extrude(CAP_T) + (
    rrect(lip_o, lip_o, BOX_R - WALL - 0.2) - rrect(lip_o - 2.4, lip_o - 2.4, 0.8)
).extrude(LIP_H).translate([0, 0, CAP_T])  # printed upside down: plate on the bed


def save(m, path):
    mesh = m.to_mesh()
    assert m.status().name == "NoError" and m.genus() >= 0
    trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts)).export(path)


save(body, "body.stl")
save(cap, "cap.stl")

doc = ezdxf.new()
pts = rrect(PCB, PCB, PCB_R).to_polygons()[0]
doc.modelspace().add_lwpolyline(pts, close=True, dxfattribs={"layer": "BoardOutline"})
doc.saveas("board_outline.dxf")
print(f"PCB top z={PCB_TOP:.2f}, USB centre z={USB_Z:.2f}, button centre y={BTN_Y} z={BTN_Z:.2f}")
