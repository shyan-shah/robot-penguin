"""What does the tail prop actually achieve, and what does it cost?

Round 3 reached final_up 0.826 with a 150 mm spur, against 0.098 bare. But
final_up and peak_up were equal in every row, which is the signature of the robot
SETTLING at an angle rather than rising and falling back. up = 0.826 is cos(34
deg) - so the question this script answers is whether it finishes on its FEET or
simply resting on the tail like a kickstand.

It also measures the cost, which the recovery search never sees: a 150 mm tail
carrying 27 g a long way behind the body moves the centre of mass backwards, and
that eats into backwards tip-over margin and may show up in walking.
"""
import json
import math
import os

import numpy as np
import pybullet as pb

import penguin_env
import behaviours as B
import getup_catch as G
from prop_study import make_variant

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")
BEST = json.load(open(os.path.join(OUT, "prop_study_r3.json")))
lines = []


def log(s):
    print(s, flush=True)
    lines.append(s)


def contacts(sim):
    """Which links are touching the ground, and with what normal force."""
    out = {}
    names = {v: k for k, v in sim.jid.items()}
    for c in pb.getContactPoints(bodyA=sim.rid, bodyB=sim.plane,
                                 physicsClientId=sim.cid):
        li = c[3]
        name = "torso+prop" if li < 0 else names.get(li, "link%d" % li)
        out[name] = out.get(name, 0.0) + c[9]
    return out


def end_state(path, params, label):
    sim = penguin_env.PenguinSim(urdf=path)
    G.trial(sim, [params[k] for k in G.KEYS], "back")
    s = sim.state()
    cj = contacts(sim)
    pos, orn = pb.getBasePositionAndOrientation(sim.rid, physicsClientId=sim.cid)
    eul = pb.getEulerFromQuaternion(orn)
    log("  %-22s up %.3f   pitch %+6.1f deg   body CoM z %5.1f mm" %
        (label, s["up"], math.degrees(eul[0]), pos[2] * 1000))
    log("     touching: %s" % ", ".join("%s %.2f N" % (k, v)
                                        for k, v in sorted(cj.items())) or "nothing")
    feet = sum(v for k, v in cj.items() if "foot" in k)
    log("     -> weight on the FEET: %.2f N of %.2f N total%s"
        % (feet, sum(cj.values()),
           "   ON ITS FEET" if feet > 2.0 else "   NOT on its feet"))
    sim.close()
    return s["up"], feet


log("=== what the tail prop actually does ===")
log("")
log("1. end of the recovery attempt - is it standing, or propped?")
rows = [r for r in BEST if r["length_mm"] > 0]
for r in sorted(rows, key=lambda r: -r["peak_up"])[:3]:
    path = os.path.join(HERE, "penguin_verify.urdf")
    make_variant(-38.0, r["attach_z"], r["length_mm"], -r["up_deg"], path)
    end_state(path, r["params"], "%.0f mm at %.0f deg" % (r["length_mm"], r["up_deg"]))

log("")
log("2. the cost - does the tail hurt normal standing and walking?")
best = max(rows, key=lambda r: r["peak_up"])
path = os.path.join(HERE, "penguin_verify.urdf")
make_variant(-38.0, best["attach_z"], best["length_mm"], -best["up_deg"], path)
for label, urdf in (("bare", os.path.join(HERE, "penguin.urdf")),
                    ("with %.0f mm tail" % best["length_mm"], path)):
    sim = penguin_env.PenguinSim(urdf=urdf)
    sim.reset()
    for _ in range(int(2.0 / sim.dt)):
        sim.command(B.REST)
        sim.step()
    s = sim.state()
    cj = contacts(sim)
    tail = sum(v for k, v in cj.items() if "torso" in k)
    log("  %-18s standing: up %.3f   tail/shell touching floor %.2f N   %s"
        % (label, s["up"], tail, "TAIL IS DRAGGING" if tail > 0.1 else "tail clear"))
    sim.close()

json.dump({"log": lines}, open(os.path.join(OUT, "prop_verify.json"), "w"), indent=1)
open(os.path.join(OUT, "prop_verify_log.txt"), "w").write("\n".join(lines) + "\n")
