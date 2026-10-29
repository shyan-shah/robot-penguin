"""Learn a fall-recovery controller instead of hand-animating one.

The hand-written get-up routines in behaviours.py do not work, and the reason is
geometric: lying on its back the flipper pivot sits 46.7 mm above the floor and the
flipper is 55 mm long, so it reaches the ground with about 8 mm to spare and almost
no leverage. A single shove cannot lift 580 g that way.

What might work is resonance. The body is an egg, so it rocks; if the flippers beat
at the rocking frequency they pump energy in each cycle until it tips over its own
edge. That is a four-parameter idea with no obvious closed form, so we search it:
cross-entropy over an oscillating controller, scored on how upright the penguin
ends up six seconds later.
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

KEYS = ["freq", "amp_R", "amp_L", "centre", "phase", "hip", "hip_bias", "ank",
        "ank_phase", "ramp"]
# The hips are the key change from the first attempt. They were capped at +-35 deg
# because that is all that is useful when standing (beyond that the feet collide),
# but lying down the legs can splay to the servo's full +-90 and push against the
# floor. That is 4.2 N at each foot against a 5.7 N robot - enough to lever it up,
# where the flippers alone (55 mm long, pivot 46.7 mm off the floor) never were.
LO = np.array([0.4, 0.0, 0.0, -90.0, -math.pi, 0.0, -80.0, 0.0, -math.pi, 0.5])
HI = np.array([4.0, 140.0, 140.0, 140.0, math.pi, 90.0, 80.0, 30.0, math.pi, 4.0])


class Rocker:
    """Oscillating recovery controller."""

    def __init__(self, p):
        self.p = dict(zip(KEYS, p))

    def sample(self, t):
        q = self.p
        w = 2 * math.pi * q["freq"] * t
        env = min(1.0, t / max(0.2, q["ramp"]))          # ease the oscillation in
        hip = env * (q["hip_bias"] + q["hip"] * math.sin(w))
        out = {
            "flipper_R": q["centre"] + env * q["amp_R"] * math.sin(w),
            "flipper_L": q["centre"] + env * q["amp_L"] * math.sin(w + q["phase"]),
            "hip_R": hip,
            "hip_L": -hip,
            "ankle_R": env * q["ank"] * math.sin(w + q["ank_phase"]),
            "ankle_L": env * q["ank"] * math.sin(w + q["ank_phase"]),
            "beak": 0.0,
        }
        # the hips get the widened recovery range, everything else stays nominal
        out["hip_R"] = max(-90.0, min(90.0, out["hip_R"]))
        out["hip_L"] = max(-90.0, min(90.0, out["hip_L"]))
        rest = B.clamp({k: v for k, v in out.items() if not k.startswith("hip")})
        rest["hip_R"], rest["hip_L"] = out["hip_R"], out["hip_L"]
        return rest


def trial(sim, p, kind, drive=6.0, settle=2.0, hz=50):
    sim.reset(tilt=FALLS[kind])
    for _ in range(int(0.7 / sim.dt)):
        sim.command(B.REST)
        sim.step()
    rc = Rocker(p)
    peak, t = sim.state()["up"], 0.0
    every = max(1, int(1.0 / (hz * sim.dt)))
    for i in range(int(drive / sim.dt)):
        if i % every == 0:
            sim.command(rc.sample(t))
        sim.step()
        t += sim.dt
        peak = max(peak, sim.state()["up"])
    for i in range(int(settle / sim.dt)):      # let go and see if it stays up
        if i % every == 0:
            sim.command(B.REST)
        sim.step()
    s = sim.state()
    return {"final_up": float(s["up"]), "peak_up": float(peak),
            "recovered": bool(s["up"] > 0.85)}


def score(r):
    return r["final_up"] * 100.0 + r["peak_up"] * 25.0 + (120.0 if r["recovered"] else 0.0)


def search(kind, iters=16, pop=24, elite=6, seed=3, log=print):
    sim = PenguinSim()
    rng = np.random.default_rng(seed)
    mu = (LO + HI) / 2.0
    sigma = (HI - LO) / 4.0
    best, best_s = None, -1e9
    for it in range(iters):
        xs = np.clip(rng.normal(mu, sigma, size=(pop, len(mu))), LO, HI)
        rs = [trial(sim, x, kind) for x in xs]
        ss = np.array([score(r) for r in rs])
        order = np.argsort(-ss)
        top = xs[order[:elite]]
        mu = top.mean(axis=0)
        sigma = np.maximum(top.std(axis=0), (HI - LO) * 0.03)
        if ss[order[0]] > best_s:
            best_s = float(ss[order[0]])
            best = {"params": dict(zip(KEYS, [float(v) for v in xs[order[0]]])),
                    **rs[order[0]]}
        log("  %-5s iter %2d  best %6.1f  final_up %.3f  peak %.3f  recovered=%s"
            % (kind, it, best_s, best["final_up"], best["peak_up"], best["recovered"]))
    sim.close()
    return best


if __name__ == "__main__":
    lines = []

    def log(s):
        print(s, flush=True)
        lines.append(s)

    t0 = time.time()
    out = {}
    for kind in (sys.argv[1:] or list(FALLS)):
        log("=== learning recovery from: %s ===" % kind)
        out[kind] = search(kind, log=log)
        log("  -> %s  params %s" % ("RECOVERS" if out[kind]["recovered"] else "still stuck",
                                    json.dumps({k: round(v, 2) for k, v in out[kind]["params"].items()})))
    json.dump(out, open(os.path.join(OUT, "getup_learned_v2.json"), "w"), indent=1)
    log("done in %.0f s" % (time.time() - t0))
    open(os.path.join(OUT, "getup_v2_log.txt"), "w").write("\n".join(lines) + "\n")
