"""Rebuilds base_indicator_light.stl from commit 62c14d3 with a solid floor: the old floor flexure is filled and its raised plunger removed.
STL coords: board centre is (17.5, 17.5), floor is z 0..1.0. All sizes in mm."""
import subprocess

import numpy as np
import trimesh
from manifold3d import CrossSection, Manifold, Mesh

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
assert base.status().name == "NoError"
mesh = base.to_mesh()
out = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)
assert out.is_watertight
out.export("base_indicator_light.stl")
print("floor solid, volume mm3:", round(out.volume))
