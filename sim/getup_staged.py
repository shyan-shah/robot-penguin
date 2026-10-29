"""Two-stage fall recovery, built around which joints can actually help.

Measured alignment between each joint axis and the axis the body must rotate
about to stand up (1.00 = directly useful, 0.00 = useless):

              hip    ankle   flipper
    on back   0.00   0.02    1.00
    on front  0.00   0.07    1.00
    on side   0.00   0.67    0.74

So from the back or front the flippers are the *only* actuator pointing the right
way, and they are 55 mm long on a pivot 46.7 mm off the floor - about 8 mm of
usable lever against a 5.7 N robot. A single-stage search over flipper
oscillation found zero successes in 1,800 trials, and that is the honest answer
for that geometry.

From the side it is a different problem: the ankles align at 0.67 and have the
whole foot as a lever.

Hence two stages:

    stage A   roll from face-up/face-down onto the side.
              This is a rotation about a different axis, and the HIPS are aligned
              with it - swinging 90 g of leg generates the reaction torque, and
              the body's egg-shaped shell lets it roll rather than having to be
              lifted.

    stage B   right the body from the side, using ankles and flippers together.

Each stage is a short oscillation with its own parameters; the whole thing is
searched end to end on the final uprightness, so the optimiser is free to decide
how long to spend rolling before it starts pushing.
"""
import json
import math
import os
import sys
import time

import numpy as np

from penguin_env import PenguinSim
import behaviours as B

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")
os.makedirs(OUT, exist_ok=True)

FALLS = {"back": (math.radians(88), 0.0),      # back shell on the ground
         "front": (math.radians(-88), 0.0),    # face down
         "side": (0.0, math.radians(85))}

KEYS = [
    # stage A - roll onto the side
    "tA", "A_freq", "A_hip", "A_hip_bias", "A_flipR", "A_flipL", "A_centre",
    # stage B - right from the side
    "B_freq", "B_ank", "B_ank_bias", "B_flip_amp", "B_flip_centre", "B_phase",
    "B_hip",
]
LO = np.array([0.0, 0.4, 0.0, -90.0, -95.0, -95.0, -90.0,
               0.4, 0.0, -30.0, 0.0, -90.0, -math.pi, 0.0])
HI = np.array([3.5, 3.5, 90.0, 90.0, 185.0, 185.0, 185.0,
               3.5, 30.0, 30.0, 140.0, 185.0, math.pi, 90.0])


def clamp_hip(v):
    return max(-90.0, min(90.0, v))


class Staged:
    def __init__(self, p):
        self.q = dict(zip(KEYS, p))

    def sample(self, t):
        q = self.q
        if t < q["tA"]:
            w = 2 * math.pi * q["A_freq"] * t
            env = min(1.0, t / 0.35)
            hip = env * (q["A_hip_bias"] + q["A_hip"] * math.sin(w))
            pose = {"flipper_R": q["A_centre"] + env * (q["A_flipR"] - q["A_centre"]),
                    "flipper_L": q["A_centre"] + env * (q["A_flipL"] - q["A_centre"]),
                    "ankle_R": 0.0, "ankle_L": 0.0, "beak": 0.0}
            pose = B.clamp(pose)
            pose["hip_R"] = clamp_hip(hip)
            pose["hip_L"] = clamp_hip(-hip)
            return pose
        u = t - q["tA"]
        w = 2 * math.pi * q["B_freq"] * u
        env = min(1.0, u / 0.35)
        ank = env * (q["B_ank_bias"] + q["B_ank"] * math.sin(w))
        pose = {"flipper_R": q["B_flip_centre"] + env * q["B_flip_amp"] * math.sin(w),
                "flipper_L": q["B_flip_centre"] + env * q["B_flip_amp"] * math.sin(w + q["B_phase"]),
                "ankle_R": ank, "ankle_L": ank, "beak": 0.0}
        pose = B.clamp(pose)
        pose["hip_R"] = clamp_hip(env * q["B_hip"])
        pose["hip_L"] = clamp_hip(-env * q["B_hip"])
        return pose


def trial(sim, p, kind, drive=7.0, settle=2.0, hz=50):
    sim.reset(tilt=FALLS[kind])
    for _ in range(int(0.7 / sim.dt)):
        sim.command(B.REST)
        sim.step()
    rc = Staged(p)
    peak = sim.state()["up"]
    best_side = 0.0
    t = 0.0
    every = max(1, int(1.0 / (hz * sim.dt)))
    for i in range(int(drive / sim.dt)):
        if i % every == 0:
            sim.command(rc.sample(t))
        sim.step()
        t += sim.dt
        s = sim.state()
        peak = max(peak, s["up"])
        # progress credit for reaching the side even if it does not finish
        best_side = max(best_side, abs(math.sin(math.radians(s["lean_lat"]))))
    for i in range(int(settle / sim.dt)):
        if i % every == 0:
            sim.command(B.REST)
        sim.step()
    s = sim.state()
    return {"final_up": float(s["up"]), "peak_up": float(peak),
            "side_progress": float(best_side),
            "recovered": bool(s["up"] > 0.85)}


def score(r):
    return (r["final_up"] * 120.0 + r["peak_up"] * 40.0 + r["side_progress"] * 25.0
            + (150.0 if r["recovered"] else 0.0))


_SIM = None


def _init():
    global _SIM
    _SIM = PenguinSim()


def _eval(args):
    x, kind = args
    r = trial(_SIM, np.asarray(x), kind)
    return score(r), r


def search(kind, iters=18, pop=24, elite=6, seed=5, log=print, workers=3):
    import multiprocessing as mp
    pool = mp.Pool(workers, initializer=_init) if workers > 1 else None
    sim = None if pool else PenguinSim()
    rng = np.random.default_rng(seed)
    mu = (LO + HI) / 2.0
    sigma = (HI - LO) / 4.0
    best, best_s = None, -1e9
    for it in range(iters):
        xs = np.clip(rng.normal(mu, sigma, size=(pop, len(mu))), LO, HI)
        if pool:
            out = pool.map(_eval, [(x.tolist(), kind) for x in xs])
            ss = np.array([o[0] for o in out])
            rs = [o[1] for o in out]
        else:
            rs = [trial(sim, x, kind) for x in xs]
            ss = np.array([score(r) for r in rs])
        order = np.argsort(-ss)
        top = xs[order[:elite]]
        mu = top.mean(axis=0)
        sigma = np.maximum(top.std(axis=0), (HI - LO) * 0.03)
        if ss[order[0]] > best_s:
            best_s = float(ss[order[0]])
            best = {"params": dict(zip(KEYS, [float(v) for v in xs[order[0]]])), **rs[order[0]]}
        log("  %-5s iter %2d  best %6.1f | final_up %.3f peak %.3f side %.2f | %s"
            % (kind, it, best_s, best["final_up"], best["peak_up"],
               best["side_progress"], "RECOVERS" if best["recovered"] else ""))
    if pool:
        pool.close(); pool.join()
    else:
        sim.close()
    return best


if __name__ == "__main__":
    lines = []

    def log(s):
        print(s, flush=True)
        lines.append(s)

    t0 = time.time()
    out = {}
    for kind in (sys.argv[1:] or ["side", "back", "front"]):
        log("=== two-stage recovery: %s ===" % kind)
        out[kind] = search(kind, log=log)
        log("  -> %s" % ("RECOVERS" if out[kind]["recovered"] else
                         "does not recover (final_up %.2f)" % out[kind]["final_up"]))
        json.dump(out, open(os.path.join(OUT, "getup_staged.json"), "w"), indent=1)
    log("done in %.0f s" % (time.time() - t0))
    open(os.path.join(OUT, "getup_staged_log.txt"), "w").write("\n".join(lines) + "\n")
