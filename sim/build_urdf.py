"""Generate penguin.urdf straight from the CAD.

Masses, centres of mass and inertia tensors come from Inventor
(CAD/exports/mass_properties.json); the visual and collision meshes are the
as-designed STLs, so the simulated robot is the robot that gets printed.
Lengths in the JSON are metres, STL vertices are millimetres.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(os.path.dirname(HERE), "CAD")
MESH = os.path.join(CAD, "exports", "stl_assembled")

# which STLs make up each link, and which of those are worth colliding
VISUAL = {
    "torso": ["base_plate", "core_frame", "body_front", "body_back",
              "head_front", "head_back", "beak_upper"],
    "leg_R": ["leg_R"], "leg_L": ["leg_L"],
    "foot_R": ["foot_R"], "foot_L": ["foot_L"],
    "flipper_R": ["flipper_R"], "flipper_L": ["flipper_L"],
    "beak": ["beak_lower"],
}
# internal parts never touch the outside world, so leave them out of collision
COLLIDE = dict(VISUAL, torso=["base_plate", "body_front", "body_back",
                              "head_front", "head_back"])
# Colour per MESH, not per link: the torso link holds both shells, and painting
# the whole link one colour makes the renders a black blob.
MESH_COLOUR = {
    "body_front": "0.93 0.93 0.95 1", "head_front": "0.93 0.93 0.95 1",
    "body_back": "0.10 0.10 0.12 1", "head_back": "0.10 0.10 0.12 1",
    "beak_upper": "0.95 0.45 0.05 1", "beak_lower": "0.95 0.45 0.05 1",
    "foot_R": "0.95 0.45 0.05 1", "foot_L": "0.95 0.45 0.05 1",
    "flipper_R": "0.10 0.10 0.12 1", "flipper_L": "0.10 0.10 0.12 1",
    "leg_R": "0.45 0.45 0.48 1", "leg_L": "0.45 0.45 0.48 1",
    "base_plate": "0.40 0.40 0.43 1", "core_frame": "0.40 0.40 0.43 1",
}
DEFAULT_COLOUR = "0.5 0.5 0.52 1"


def geoms(kind, link, origin_m):
    """<visual>/<collision> blocks, each mesh shifted into the link frame."""
    ox, oy, oz = origin_m
    rows = []
    for m in (VISUAL if kind == "visual" else COLLIDE).get(link, []):
        path = os.path.join(MESH, m + ".stl").replace("\\", "/")
        body = ('      <origin xyz="%.6f %.6f %.6f" rpy="0 0 0"/>\n'
                '      <geometry><mesh filename="%s" scale="0.001 0.001 0.001"/></geometry>\n'
                % (-ox, -oy, -oz, path))
        if kind == "visual":
            body += ('      <material name="mat_%s"><color rgba="%s"/></material>\n'
                     % (m, MESH_COLOUR.get(m, DEFAULT_COLOUR)))
        rows.append("    <%s>\n%s    </%s>" % (kind, body, kind))
    return "\n".join(rows)


def link_xml(name, props, origin_m):
    cx, cy, cz = props["com"]
    ox, oy, oz = origin_m
    ixx, iyy, izz, ixy, iyz, ixz = props["inertia"]
    return """  <link name="%s">
    <inertial>
      <origin xyz="%.6f %.6f %.6f" rpy="0 0 0"/>
      <mass value="%.6f"/>
      <inertia ixx="%.9f" iyy="%.9f" izz="%.9f" ixy="%.9f" iyz="%.9f" ixz="%.9f"/>
    </inertial>
%s
%s
  </link>""" % (name, cx - ox, cy - oy, cz - oz, props["mass"],
               ixx, iyy, izz, ixy, iyz, ixz,
               geoms("visual", name, origin_m), geoms("collision", name, origin_m))


def build(src=None, dst=None):
    src = src or os.path.join(CAD, "exports", "mass_properties.json")
    dst = dst or os.path.join(HERE, "penguin.urdf")
    d = json.load(open(src))
    links, joints = d["links"], d["joints"]

    origin = {"torso": [0.0, 0.0, 0.0]}
    for name, j in joints.items():
        origin[name] = [v / 1000.0 for v in j["origin_mm"]]

    out = ['<?xml version="1.0"?>', '<robot name="penguin">',
           link_xml("torso", links["torso"], origin["torso"])]
    for name, j in joints.items():
        parent = j["parent"]
        rel = [origin[name][k] - origin[parent][k] for k in range(3)]
        lo, hi = [v * 3.141592653589793 / 180.0 for v in j["limit_deg"]]
        out.append(link_xml(name, links[name], origin[name]))
        out.append("""  <joint name="%s" type="revolute">
    <parent link="%s"/>
    <child link="%s"/>
    <origin xyz="%.6f %.6f %.6f" rpy="0 0 0"/>
    <axis xyz="%d %d %d"/>
    <limit lower="%.4f" upper="%.4f" effort="%.4f" velocity="%.4f"/>
    <dynamics damping="0.002" friction="0.0015"/>
  </joint>""" % (name, parent, name, rel[0], rel[1], rel[2],
                 j["axis"][0], j["axis"][1], j["axis"][2], lo, hi,
                 d["servo"]["stall_torque_Nm"],
                 d["servo"]["no_load_speed_dps"] * 3.141592653589793 / 180.0))
    out.append("</robot>")
    open(dst, "w").write("\n".join(out) + "\n")
    return dst, d


if __name__ == "__main__":
    path, d = build()
    print("wrote", path)
    print("total mass %.1f g, floor at z = %.1f mm" % (d["total_mass_kg"] * 1000, d["floor_z_mm"]))
    for name, j in d["joints"].items():
        print("  %-10s parent=%-6s axis=%s  limits %s deg" %
              (name, j["parent"], j["axis"], j["limit_deg"]))
