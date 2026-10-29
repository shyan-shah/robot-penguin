"""Fall recovery with a catch phase, and a flipper-length sweep.

The length sweep showed the roll gets *further* with every extra millimetre of
flipper - peak uprightness 0.35 at 55 mm, 0.81 at 121 mm - but never completes.
At 0.81 the penguin is within 36 degrees of standing and falls back, which is not
a leverage problem any more. It is that the controller keeps oscillating through
the top of the arc instead of stopping and putting its feet down.

So this adds a third stage, triggered by feedback rather than by a timer:

    A  roll onto the side          hips swing 90 g of leg; the egg shell rolls
    B  push                        flippers drive against the floor
    C  CATCH - the moment the body passes `trigger` uprightness, stop pushing,
       snap the legs and ankles to the standing pose, and hand over to the
       balance controller

That last stage is what a person does getting off the floor: you do not keep
heaving once you are nearly up, you get a foot under yourself and stand.
"""
import json
import math
import os
import sys
import time

import numpy as np

import penguin_env
from control import Balancer
import behaviours as B

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tuned")
os.makedirs(OUT, exist_ok=True)

FALLS = {"back": (math.radians(88), 0.0),      # back shell on the ground
         "front": (math.radians(-88), 0.0),    # face down
         "side": (0.0, math.radians(85))}

# The flipper window is normally clamped to an MG90S's 180 deg (-45..135). For
# recovery that matters a lot: the flipper stops pushing the moment it runs out
# of travel, and that can happen before the body reaches its balance point. Set
# PENGUIN_FULL_SWEEP=1 to test the linkage's full 280 deg instead, i.e. what a
# 270 deg servo would buy.
if os.environ.get("PENGUIN_FULL_SWEEP"):
    FLIP_LO, FLIP_HI = -95.0, 185.0
else:
    FLIP_LO, FLIP_HI = -45.0, 135.0


KEYS = ["tA", "A_freq", "A_hip", "A_hip_bias", "A_flip",
        "B_freq", "B_flip_amp", "B_flip_centre", "B_phase", "B_hip", "B_ank",
        "trigger", "C_ank"]
LO = np.array([0.0, 0.4, 0.0, -90.0, FLIP_LO,
               0.4, 0.0, FLIP_LO, -math.pi, 0.0, 0.0,
               0.45, -25.0])
HI = np.array([3.0, 3.5, 90.0, 90.0, FLIP_HI,
               3.5, 140.0, FLIP_HI, math.pi, 90.0, 28.0,
               0.90, 25.0])

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Catcher:
    """Three-stage recovery. Stage C is entered on feedback and never left."""

    def __init__(self, p):
        self.q = dict(zip(KEYS, p))
        self.caught_at = None

    def sample(self, t, up):
        q = self.q
        if self.caught_at is None and up >= q["trigger"] and t > 0.4:
            self.caught_at = t
        if self.caught_at is not None:
            # --- C: plant the feet and hold still, let the balancer finish it
            return {"hip_R": 0.0, "hip_L": 0.0,
                    "ankle_R": q["C_ank"], "ankle_L": q["C_ank"],
                    "flipper_R": 90.0, "flipper_L": 90.0, "beak": 0.0}
        if t < q["tA"]:
            # --- A: roll onto the side
            w = 2 * math.pi * q["A_freq"] * t
            env = min(1.0, t / 0.3)
            hip = env * (q["A_hip_bias"] + q["A_hip"] * math.sin(w))
            return {"hip_R": clamp(hip, -90, 90), "hip_L": clamp(-hip, -90, 90),
                    "ankle_R": 0.0, "ankle_L": 0.0,
                    "flipper_R": clamp(q["A_flip"], FLIP_LO, FLIP_HI),
                    "flipper_L": clamp(q["A_flip"], FLIP_LO, FLIP_HI), "beak": 0.0}
        # --- B: push
        u = t - q["tA"]
        w = 2 * math.pi * q["B_freq"] * u
        env = min(1.0, u / 0.3)
        return {"hip_R": clamp(env * q["B_hip"], -90, 90),
                "hip_L": clamp(-env * q["B_hip"], -90, 90),
                "ankle_R": clamp(env * q["B_ank"], -30, 30),
                "ankle_L": clamp(env * q["B_ank"], -30, 30),
                "flipper_R": clamp(q["B_flip_centre"] + env * q["B_flip_amp"] * math.sin(w),
                                   FLIP_LO, FLIP_HI),
                "flipper_L": clamp(q["B_flip_centre"] + env * q["B_flip_amp"] * math.sin(w + q["B_phase"]),
                                   FLIP_LO, FLIP_HI),
                "beak": 0.0}


def trial(sim, p, kind, drive=7.0, settle=2.5, hz=50):
    sim.reset(tilt=FALLS[kind])
    for _ in range(int(0.7 / sim.dt)):
        sim.command(B.REST)
        sim.step()
    rc = Catcher(p)
    bal = Balancer(kp=0.5, kd=0.05, sign=+1.0)
    peak = sim.state()["up"]
    every = max(1, int(1.0 / (hz * sim.dt)))
    t = 0.0
    for i in range(int(drive / sim.dt)):
        s = sim.state()
        if i % every == 0:
            pose = rc.sample(t, s["up"])
            if rc.caught_at is not None:         # balance once we are on our feet
                pose = bal.correct(s, pose)
            sim.command(pose)
        sim.step()
        t += sim.dt
        peak = max(peak, sim.state()["up"])
    for i in range(int(settle / sim.dt)):        # let go and see if it stays up
        s = sim.state()
        if i % every == 0:
            sim.command(bal.correct(s, B.REST))
        sim.step()
        peak = max(peak, sim.state()["up"])
    s = sim.state()
    return {"final_up": float(s["up"]), "peak_up": float(peak),
            "caught": rc.caught_at is not None,
            "recovered": bool(s["up"] > 0.85)}


def score(r):
    return (r["final_up"] * 150.0 + r["peak_up"] * 50.0 +
            (20.0 if r["caught"] else 0.0) + (200.0 if r["recovered"] else 0.0))


def search(sim, kind, iters=12, pop=20, elite=5, seed=5, log=print):
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
            best = {"params": dict(zip(KEYS, [float(v) for v in xs[order[0]]])), **rs[order[0]]}
    return best


if __name__ == "__main__":
    import flipper_study as FS
    lines = []

    def log(s):
        print(s, flush=True)
        lines.append(s)

    factors = [float(a) for a in sys.argv[1:]] or [1.0, 1.3, 1.6, 1.9]
    log("=== recovery with a catch phase, swept over flipper length ===")
    log("    fall: on its back.  catch = stop pushing and plant the feet once")
    log("    the body passes a learned uprightness threshold")
    t0 = time.time()
    rows = []
    try:
        for f in factors:
            FS.make_variant(f)
            import importlib
            importlib.reload(penguin_env)
            sim = penguin_env.PenguinSim(urdf=FS.VARIANT)
            best = search(sim, "back", log=log)
            sim.close()
            length = 55.0 * f
            rows.append({"factor": f, "length_mm": length, **best})
            log("  flipper %6.1f mm -> peak %.3f  final %.3f  caught=%s  %s"
                % (length, best["peak_up"], best["final_up"], best["caught"],
                   "STANDS UP" if best["recovered"] else ""))
    finally:
        FS.restore()
    ok = [r for r in rows if r["recovered"]]
    log("")
    if ok:
        log("self-rights from %.0f mm of flipper (%.0f mm longer than the current 55)"
            % (ok[0]["length_mm"], ok[0]["length_mm"] - 55.0))
    else:
        log("still no complete recovery; best peak %.3f at %.0f mm"
            % (max(r["peak_up"] for r in rows),
               max(rows, key=lambda r: r["peak_up"])["length_mm"]))
    json.dump(rows, open(os.path.join(OUT, "getup_catch.json"), "w"), indent=1)
    log("done in %.0f s" % (time.time() - t0))
    open(os.path.join(OUT, "getup_catch_log.txt"), "w").write("\n".join(lines) + "\n")
