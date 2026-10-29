"""Why did stage D change nothing?

Round 4 added a stand-up stage and returned final_up identical to round 3 to
three decimal places at every tail length (90 -> 0.688, 110 -> 0.746,
130 -> 0.791). Two explanations fit, and they point in opposite directions:

  a  stage D never fired, so round 4 re-ran round 3 with four dead parameters
  b  the final angle is set by GEOMETRY - the tail length fixes the angle the
     body reclines at - and no controller can change it, so every search lands
     on the same number

(b) would mean the smooth length/angle curve across rounds 3 and 4 is not a
controller achievement at all, just the resting angle of a deckchair. That
matters for what gets claimed, so this traces one run and prints the facts:
when each stage fires, and the whole attitude history.
"""
import json
import math
import os

import numpy as np

import penguin_env
import behaviours as B
import getup_tail as G
from control import Balancer
from prop_study import make_variant

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")
ROWS = json.load(open(os.path.join(OUT, "prop_study_r4.json")))
lines = []


def log(s):
    print(s, flush=True)
    lines.append(s)


def traced(length, params):
    path = os.path.join(HERE, "penguin_diag.urdf")
    make_variant(-38.0, 55.0, length, -10.0, path)
    sim = penguin_env.PenguinSim(urdf=path)
    sim.reset(tilt=G.FALLS["back"])
    for _ in range(int(0.7 / sim.dt)):
        sim.command(B.REST)
        sim.step()
    rc = G.TailCatcher([params[k] for k in G.KEYS])
    bal = Balancer(kp=0.5, kd=0.05, sign=+1.0)
    every = max(1, int(1.0 / (50 * sim.dt)))
    t, hist = 0.0, []
    for i in range(int(9.0 / sim.dt)):
        s = sim.state()
        fN = G.foot_load(sim)
        if i % every == 0:
            pose = rc.sample(t, s, fN)
            if rc.caught_at is not None:
                pose = bal.correct(s, pose)
            sim.command(pose)
        sim.step()
        t += sim.dt
        if i % int(0.5 / sim.dt) == 0:
            hist.append((t, s["up"], fN, G.tail_load(sim)))
    log("  tail %.0f mm   C fired at %s   D fired at %s"
        % (length,
           "%.2f s" % rc.caught_at if rc.caught_at is not None else "NEVER",
           "%.2f s" % rc.stood_at if rc.stood_at is not None else "NEVER"))
    log("     t/s :  " + " ".join("%5.1f" % h[0] for h in hist))
    log("     up  :  " + " ".join("%5.2f" % h[1] for h in hist))
    log("     feet:  " + " ".join("%5.1f" % h[2] for h in hist))
    log("     tail:  " + " ".join("%5.1f" % h[3] for h in hist))
    log("     D params: flip %.0f  ank %.0f  hip %.0f  rate %.2f  C_hold %.2f"
        % (params["D_flip"], params["D_ank"], params["D_hip"], params["D_rate"],
           params["C_hold"]))
    sim.close()
    return rc.stood_at is not None


log("=== tracing the tail recovery, to see which stages actually fire ===")
log("")
for r in ROWS:
    if r["length_mm"] in (90.0, 130.0):
        traced(r["length_mm"], r["params"])
        log("")

# And the decisive test for (b): does the resting angle depend on the controller
# at all? Drop it on its back with NO controller - just rest - and see where it
# settles with a tail fitted.
log("=== control: dropped on its back, limp, no recovery attempt at all ===")
for length in (90.0, 130.0):
    path = os.path.join(HERE, "penguin_diag.urdf")
    make_variant(-38.0, 55.0, length, -10.0, path)
    sim = penguin_env.PenguinSim(urdf=path)
    sim.reset(tilt=G.FALLS["back"])
    for _ in range(int(4.0 / sim.dt)):
        sim.command(B.REST)
        sim.step()
    s = sim.state()
    log("  tail %3.0f mm   limp resting up = %.3f   feet %.2f N   tail %.2f N"
        % (length, s["up"], G.foot_load(sim), G.tail_load(sim)))
    sim.close()

open(os.path.join(OUT, "prop_diag_log.txt"), "w").write("\n".join(lines) + "\n")
