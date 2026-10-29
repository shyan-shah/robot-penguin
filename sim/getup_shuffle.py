"""Getting out of the deckchair: shuffle the feet back under the body.

prop_diag.py established the thing that reframes this whole problem. Dropped on
its back completely limp, with no recovery attempt at all, a penguin with a tail
prop rests at:

      90 mm tail   up = 0.688   3.2 N on the feet
     130 mm tail   up = 0.791   4.3 N on the feet

Those are exactly the numbers that rounds 2, 3 and 4 reported as search results
after several thousand trials. The searches were not recovering - they were
measuring the angle the tail happens to hold the body at. up never moved by 0.01
in nine seconds of driving.

So the tail does not right the penguin. What it does is make lying flat on its
back impossible: a backward fall now ends with it reclined against the tail, FEET
ON THE FLOOR, at about 40 degrees off vertical. That is a completely different
starting position, and it suggests the move that actually finishes the job - the
one a person uses to get out of a low deckchair. You do not haul your chest up.
You shuffle your feet back underneath you until your weight is over them.

The feet have to travel about 105*sin(40) = 67 mm backwards. That is what this
searches: the existing waddle CPG, run backwards, from the reclined rest pose,
with the balancer catching it as the tail comes off the floor.

No stages A-D here. The recline is free, so the controller only has to do the
last part.
"""
import json
import math
import os
import time

import numpy as np

import behaviours as B
from control import Balancer, Gaited
from gait_search import gait_motion
from getup_catch import FALLS

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")
os.makedirs(OUT, exist_ok=True)

# The shuffle is the waddle CPG with its own parameters, plus a hip bias (which
# steers how hard it digs backwards) and a flipper position (which moves the
# centre of mass fore and aft while it shuffles).
KEYS = ["roll", "yaw", "phase", "period", "dwell", "toe_out",
        "hip_bias", "flip", "kp", "kd", "lean_scale", "settle"]
LO = np.array([6.0, 0.0, -0.5, 0.5, 0.0, -16.0, -40.0, -45.0, 0.10, 0.000, 0.3, 0.5])
HI = np.array([26.0, 34.0, 0.5, 2.2, 1.0, 16.0, 40.0, 135.0, 1.00, 0.140, 1.2, 2.5])


def trial(sim, x, seconds=10.0, hz=50):
    g = dict(zip(KEYS, x))
    m = gait_motion(g["roll"], g["yaw"], g["phase"], g["period"], g["toe_out"],
                    g["dwell"], 0.0)
    bal = Balancer(kp=g["kp"], kd=g["kd"], sign=+1.0)
    closed = Gaited(m, bal, g["lean_scale"])

    sim.reset(tilt=FALLS["back"])
    # let it fall and settle against the tail, limp - this needs no control
    for _ in range(int(g["settle"] / sim.dt)):
        sim.command(B.REST)
        sim.step()
    rest_up = sim.state()["up"]

    every = max(1, int(1.0 / (hz * sim.dt)))
    t, peak = 0.0, rest_up
    for i in range(int(seconds / sim.dt)):
        s = sim.state()
        if i % every == 0:
            pose = closed.sample_closed(t, s)
            # bias the hips to dig backwards, and hold the flippers where the
            # search wants them for fore-aft trim
            pose["hip_R"] = max(-90.0, min(90.0, pose.get("hip_R", 0.0) + g["hip_bias"]))
            pose["hip_L"] = max(-90.0, min(90.0, pose.get("hip_L", 0.0) - g["hip_bias"]))
            pose["flipper_R"] = pose["flipper_L"] = max(-45.0, min(135.0, g["flip"]))
            sim.command(pose)
        sim.step()
        t += sim.dt
        peak = max(peak, sim.state()["up"])
    # let go: a real recovery has to stay up without the shuffle driving it
    for i in range(int(2.0 / sim.dt)):
        s = sim.state()
        if i % every == 0:
            sim.command(bal.correct(s, B.REST))
        sim.step()
    s = sim.state()
    return {"rest_up": float(rest_up), "final_up": float(s["up"]),
            "peak_up": float(peak), "gain": float(s["up"] - rest_up),
            "recovered": bool(s["up"] > 0.85)}


def score(r):
    # Credit only what the controller ADDS to the free resting angle. This is the
    # mistake rounds 2-4 made: scoring absolute uprightness rewarded a longer
    # tail for simply reclining less, which no amount of control was doing.
    return (r["gain"] * 300.0 + r["final_up"] * 60.0
            + (250.0 if r["recovered"] else 0.0))


def search(sim, iters=16, pop=20, elite=5, seed=11, log=print):
    rng = np.random.default_rng(seed)
    mu = (LO + HI) / 2.0
    sigma = (HI - LO) / 4.0
    best, best_s = None, -1e9
    for it in range(iters):
        xs = np.clip(rng.normal(mu, sigma, size=(pop, len(mu))), LO, HI)
        rs = [trial(sim, x) for x in xs]
        ss = np.array([score(r) for r in rs])
        order = np.argsort(-ss)
        top = xs[order[:elite]]
        mu = top.mean(axis=0)
        sigma = np.maximum(top.std(axis=0), (HI - LO) * 0.03)
        if ss[order[0]] > best_s:
            best_s = float(ss[order[0]])
            best = {"params": dict(zip(KEYS, [float(v) for v in xs[order[0]]])),
                    **rs[order[0]]}
        log("  iter %2d  best %6.1f | rest %.3f -> final %.3f  (gain %+.3f) %s"
            % (it, best_s, best["rest_up"], best["final_up"], best["gain"],
               "STANDS UP" if best["recovered"] else ""))
    return best
