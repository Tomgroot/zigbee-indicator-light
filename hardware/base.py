"""Rebuilds base_indicator_light.stl from commit 62c14d3 with a solid floor (old floor flexure filled, raised plunger removed) and screw bosses for the LED shield.
STL coords: board centre is (17.5, 17.5), floor is z 0..1.0. All sizes in mm."""
import subprocess

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, Mesh

FLOOR, PLUNGER_TOP = 1.0, 2.2
f = lambda v: float(np.float32(v))  # the STL stores float32, so snap to it or the booleans leave hairline slivers
OLD_SLOT = [(f(x), f(y)) for x, y in [(15.68, 15.0), (16.1, 15.0), (16.1, 5.4), (8.9, 5.4), (8.9, 15.0), (9.5, 15.0), (9.5, 6.0), (15.5, 6.0), (15.5, 15.0)]]

orig = subprocess.run(["git", "show", "62c14d3:hardware/base_indicator_light.stl"], capture_output=True, check=True).stdout
open("/tmp/base_orig.stl", "wb").write(orig)
t = trimesh.load("/tmp/base_orig.stl")
base = Manifold(Mesh(vert_properties=np.asarray(t.vertices, dtype=np.float32), tri_verts=np.asarray(t.faces, dtype=np.uint32)))
slot = CrossSection([OLD_SLOT[::-1]]).extrude(FLOOR)                                   # reversed: needs counter-clockwise
plunger = Manifold.cube([f(14) - f(11), f(10.5) - f(7.5), PLUNGER_TOP + 0.1 - FLOOR]).translate([f(11), f(7.5), FLOOR])
base = base + slot - plunger

# Screw bosses for shield.kicad_pcb: the 4 corner bosses (top z 4.0) go, 2 new ones sit under the shield tabs.
# Shield USB edge 0.3 mm from the -Y wall (like board.kicad_pcb), so its centre is at y 17.5 - 16.2 + 11.8.
# The SuperMini hangs upside down under the shield, USB-C down. USB_Z 4.0 keeps a ~7 mm plug overmould off the table.
# shortcut: BOSS_TOP = USB_Z + USB-C half height 1.6 + SuperMini PCB 1.0 + header spacer 2.5, estimated; measure the stack and update
USB_Z = 4.0
BOSS_TOP, BOSS_D, PILOT_D = USB_Z + 1.6 + 1.0 + 2.5, 5.0, 1.6
cavity = CrossSection.square([35, 35]) - base.slice(4.5)
base -= cavity.extrude(4.2 - FLOOR).translate([0, 0, FLOOR])
for x in (17.5 - 12, 17.5 + 12):
    boss = Manifold.cylinder(BOSS_TOP - FLOOR, BOSS_D / 2, circular_segments=48) - Manifold.cylinder(BOSS_TOP - FLOOR + 0.1, PILOT_D / 2, circular_segments=24).translate([0, 0, 0.5])
    base += boss.translate([x, 17.5 - 16.2 + 11.8, FLOOR])

# USB-C hole in the -Y wall (y 0..0.95): fill the C6 board's hole (centre z 7.23), cut a 9.4 x 3.6 slot at USB_Z
base += Manifold.cube([12, f(0.95), 5]).translate([17.5 - 6, 0, 5])
slot = CrossSection.square([9.4 - 3.2, 3.6 - 3.2], center=True).offset(1.6, JoinType.Round, circular_segments=32)
base -= slot.extrude(3).rotate([90, 0, 0]).translate([17.5, 2, USB_Z])
assert base.status().name == "NoError"
mesh = base.to_mesh()
out = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)
assert out.is_watertight
out.export("base_indicator_light.stl")
print("floor solid, volume mm3:", round(out.volume))
