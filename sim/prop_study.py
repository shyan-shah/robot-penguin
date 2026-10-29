"""Does a tail prop let the penguin get up? Test before committing any CAD.

A prop is a fixed spur off the lower back shell. It does two things when the
penguin lands on its back:

  1  it stops the body lying flat, holding it at an angle so the centre of mass
     starts closer to the tipping point
  2  it gives the flipper push a fixed point to lever about, instead of needing
     the flipper to keep contact with the floor all the way round - which is
     exactly what the length sweep showed it cannot do

The prop is parameterised by where it leaves the body, how long it is, and how
far down it points. It must also stay clear of the floor when standing, or the
penguin is on a tripod and cannot walk.

Sweeps the geometry, searching a recovery controller for each, and reports which
props work. Writes tuned/prop_study.json.
"""
import json
import math
import os
import sys
import time

import numpy as np

import penguin_env

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")
URDF = os.path.join(HERE, "penguin.urdf")
VARIANT = os.path.join(HERE, "penguin_prop.urdf")   # single-process default
os.makedirs(OUT, exist_ok=True)

FLOOR_Z = -64.0          # mm, in CAD coordinates
PROP_SECTION = 12.0      # mm square section of the spur
PROP_DENSITY = 1.24e-3   # g/mm^3 (PLA)


def prop_tip(attach_y, attach_z, length, down_deg):
    """Where the tip of the spur ends up, in CAD mm."""
    a = math.radians(down_deg)
    return (attach_y - length * math.cos(a), attach_z - length * math.sin(a))


def make_variant(attach_y, attach_z, length, down_deg, path=None):
    """Write penguin_prop.urdf: the normal robot plus a spur on the torso."""
    src = open(URDF).read()
    a = math.radians(down_deg)
    # centre of the box, in metres, in the torso frame (which is the CAD origin)
    cy = (attach_y - 0.5 * length * math.cos(a)) / 1000.0
    cz = (attach_z - 0.5 * length * math.sin(a)) / 1000.0
    L = length / 1000.0
    s = PROP_SECTION / 1000.0
    # rotate about X so the box's long axis lies along the spur
    rpy = "%.5f 0 0" % (-a)
    block = (
        '    <collision>\n'
        '      <origin xyz="0 %.6f %.6f" rpy="%s"/>\n'
        '      <geometry><box size="%.5f %.5f %.5f"/></geometry>\n'
        '    </collision>\n'
        '    <visual>\n'
        '      <origin xyz="0 %.6f %.6f" rpy="%s"/>\n'
        '      <geometry><box size="%.5f %.5f %.5f"/></geometry>\n'
        '      <material name="mat_prop"><color rgba="0.85 0.35 0.1 1"/></material>\n'
        '    </visual>\n' % (cy, cz, rpy, s, L, s, cy, cz, rpy, s, L, s))
    # add it to the torso link, just before its closing tag
    i = src.index('<link name="torso"')
    j = src.index('</link>', i)
    out = src[:j] + block + src[j:]
    # and add its mass to the torso (small, but be honest about it)
    m = PROP_SECTION * PROP_SECTION * length * PROP_DENSITY / 1000.0   # kg
    k = out.index('<mass value=', i)
    e = out.index('/>', k)
    old = float(out[k:e].split('"')[1])
    out = out[:k] + '<mass value="%.6f"' % (old + m) + out[e:]
    open(path or VARIANT, "w").write(out)
    return m * 1000.0


def restore():
    if os.path.exists(VARIANT):
        os.remove(VARIANT)


def ground_clearance(attach_y, attach_z, length, down_deg):
    ty, tz = prop_tip(attach_y, attach_z, length, down_deg)
    return tz - FLOOR_Z


GRID = [(-40.0, 15.0, L, d) for L in (45.0, 60.0, 75.0) for d in (20.0, 35.0, 50.0)]


def _eval(job):
    """One geometry, in its own process with its own variant file."""
    idx, (ay, az, length, down) = job
    import importlib
    import getup_catch as G
    path = os.path.join(HERE, "penguin_prop_%d.urdf" % idx)
    g = make_variant(ay, az, length, down, path)
    importlib.reload(penguin_env)
    sim = penguin_env.PenguinSim(urdf=path)
    best = G.search(sim, "back", iters=8, pop=14)
    sim.close()
    try:
        os.remove(path)
    except OSError:
        pass
    ty, tz = prop_tip(ay, az, length, down)
    return {"length_mm": length, "down_deg": down, "tip_y": ty, "tip_z": tz,
            "clearance_mm": ground_clearance(ay, az, length, down), "prop_g": g,
            "peak_up": best["peak_up"], "final_up": best["final_up"],
            "recovered": best["recovered"], "params": best["params"]}


if __name__ == "__main__":
    import multiprocessing as mp

    lines = []

    def log(s):
        print(s, flush=True)
        lines.append(s)

    log("=== tail prop: does it let the penguin get up? ===")
    log("    spur %.0f mm square off the back shell at Y -40, Z 15" % PROP_SECTION)
    log("    fall: BACK shell on the ground (labels were verified, not assumed)")
    log("")
    t0 = time.time()
    jobs = [(i, g) for i, g in enumerate(GRID)
            if ground_clearance(g[0], g[1], g[2], g[3]) >= 8.0]
    with mp.Pool(5) as pool:
        rows = pool.map(_eval, jobs)
    log("%6s %6s %8s %9s %8s   %s" % ("len", "down", "tip Y", "tip Z", "clear", "result"))
    for r in sorted(rows, key=lambda r: (r["length_mm"], r["down_deg"])):
        log("%6.0f %6.0f %8.1f %9.1f %8.1f   peak %.3f  final %.3f  %s"
            % (r["length_mm"], r["down_deg"], r["tip_y"], r["tip_z"], r["clearance_mm"],
               r["peak_up"], r["final_up"], "STANDS UP" if r["recovered"] else ""))
    ok = [r for r in rows if r["recovered"]]
    log("")
    if ok:
        b = max(ok, key=lambda r: r["final_up"])
        log("WORKS: %.0f mm spur %.0f deg below horizontal (%.1f mm floor clearance, %.1f g)"
            % (b["length_mm"], b["down_deg"], b["clearance_mm"], b["prop_g"]))
    else:
        b = max(rows, key=lambda r: r["peak_up"])
        log("no prop in this grid gets it up; best peak %.3f (%.0f mm at %.0f deg)"
            % (b["peak_up"], b["length_mm"], b["down_deg"]))
    json.dump(rows, open(os.path.join(OUT, "prop_study.json"), "w"), indent=1)
    log("done in %.0f s" % (time.time() - t0))
    open(os.path.join(OUT, "prop_study_log.txt"), "w").write(chr(10).join(lines) + chr(10))
