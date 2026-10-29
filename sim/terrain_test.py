"""Will it trip on a rug?

Direct test of the question, on four surfaces, with the scuffing gait and the
clearance-tuned one side by side. Each is run several times from different
starting yaws so one lucky run cannot carry the result.
"""
import json
import math
import os
import sys

import numpy as np

from penguin_env import PenguinSim
from control import Balancer, Gaited
import behaviours as B
import gait_search as G

HERE = os.path.dirname(os.path.abspath(__file__))
TUNED = os.path.join(HERE, "tuned")

SURFACES = [
    ("hard floor",        None),
    ("low pile 4 mm",     {"pile_mm": 4.0, "cell_mm": 8.0, "friction": 1.1, "seed": 1}),
    ("medium pile 8 mm",  {"pile_mm": 8.0, "cell_mm": 9.0, "friction": 1.3, "seed": 2}),
    ("deep pile 14 mm",   {"pile_mm": 14.0, "cell_mm": 11.0, "friction": 1.4, "seed": 3}),
    ("rug hem 6 mm step", {"pile_mm": 3.0, "cell_mm": 8.0, "friction": 1.2, "seed": 4,
                           "rug_edge_mm": 6.0}),
]


def load_gait(which):
    if which == "v1":                      # the scuffing one
        d = json.load(open(os.path.join(TUNED, "gait.json")))["params"]
        m = B.waddle(**{k: d[k] for k in ("roll", "yaw", "phase", "period", "toe_out")})
        return m, Balancer(kp=d["kp"], kd=d["kd"], sign=1.0), d.get("lean_scale", 1.0)
    d = json.load(open(os.path.join(TUNED, "gait_v2.json")))["params"]
    m = G.gait_motion(*[d[k] for k in ("roll", "yaw", "phase", "period", "toe_out",
                                       "dwell", "flip_amp")])
    return m, Balancer(kp=d["kp"], kd=d["kd"], sign=1.0), d["lean_scale"]


def trial(terrain, which, seconds=10.0, yaw0=0.0, seed=0):
    sim = PenguinSim(terrain=terrain, seed=seed)
    m, bal, ls = load_gait(which)
    closed = Gaited(m, bal, ls)
    sim.reset(yaw=yaw0, height=sim.z0 + 0.004)
    for _ in range(int(0.7 / sim.dt)):
        sim.command(B.REST)
        sim.step()
    p0 = sim.com().copy()
    stumble = 0
    prev_lean = 0.0
    fell = False
    t = 0.0
    for i in range(int(seconds / sim.dt)):
        if i % 5 == 0:
            sim.command(closed.sample_closed(t, sim.state()))
        sim.step()
        t += sim.dt
        if i % 8 == 0:
            s = sim.state()
            lean = s["lean_lat"]
            # a stumble: the body pitches forward hard, which is what catching a
            # toe looks like
            if abs(s["lean_fwd"]) > 22.0:
                stumble += 1
            prev_lean = lean
            if s["up"] < 0.5:
                fell = True
                break
    d = sim.com() - p0
    sim.close()
    return {"forward_mm": float(d[1] * 1000), "fell": fell,
            "stumbles": stumble, "t": t}


def main():
    print("%-20s %-10s %9s %9s %8s %s" % ("surface", "gait", "fwd mm", "mm/s", "stumble", "falls"))
    rows = []
    for name, terr in SURFACES:
        for which in ("v1", "v2"):
            fwd, falls, stum = [], 0, 0
            for k, yaw0 in enumerate((0.0, 0.6, -0.6)):
                r = trial(terr, which, yaw0=yaw0, seed=k)
                fwd.append(r["forward_mm"])
                falls += 1 if r["fell"] else 0
                stum += r["stumbles"]
            mean = float(np.mean(fwd))
            rows.append({"surface": name, "gait": which, "forward_mm": mean,
                         "speed_mms": mean / 10.0, "falls": falls, "stumbles": stum})
            print("%-20s %-10s %9.1f %9.1f %8d %d/3"
                  % (name, "scuff(v1)" if which == "v1" else "clearance(v2)",
                     mean, mean / 10.0, stum, falls))
    json.dump(rows, open(os.path.join(TUNED, "terrain.json"), "w"), indent=1)
    print("\nwritten tuned/terrain.json")


if __name__ == "__main__":
    main()
